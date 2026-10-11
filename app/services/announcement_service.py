"""KPSS Atama Takip - İlan İş Mantığı ve Orkestrasyon Servisi."""

import asyncio
from typing import List, Optional, Tuple

from app.config import settings
from app.core.constants.settings import TelegramConstants
from app.core.constants.strings import ErrorStrings, MessageStrings, NotificationStrings
from app.core.dates import today_in_turkey
from app.core.exceptions.scraper import ScrapeInProgressException
from app.core.logging import get_logger
from app.core.scoring.city_matcher import CityMatcher
from app.core.scoring.it_field_matcher import ITFieldMatcher
from app.core.scoring.strategy import KPSSScoreMatcher
from app.core.security import is_http_url
from app.domain.models import Announcement
from app.domain.schemas import (
    AnnouncementCreate,
    AnnouncementFilterParams,
    AnnouncementResponse,
    ScraperRunStatus,
    SystemStatsResponse,
)
from app.infrastructure.database.repository import AnnouncementRepository
from app.infrastructure.notification.telegram import TelegramNotifier
from app.scrapers.orchestrator import ScraperOrchestrator

logger = get_logger("services.announcement")

# Bir döngüde değerlendirilecek en fazla bildirilmemiş ilan sayısı (üst sınır koruması)
_PENDING_FETCH_LIMIT = 500


class AnnouncementService:
    """İlan kazıma, KPSS puan eşleştirme, veritabanı kaydı ve bildirim sürecini yöneten ana servis."""

    def __init__(
        self,
        repository: Optional[AnnouncementRepository] = None,
        orchestrator: Optional[ScraperOrchestrator] = None,
        notifier: Optional[TelegramNotifier] = None,
    ) -> None:
        self.repository = repository or AnnouncementRepository()
        self.orchestrator = orchestrator or ScraperOrchestrator()
        self.notifier = notifier or TelegramNotifier()
        self._cycle_lock = asyncio.Lock()

    @property
    def is_scraping(self) -> bool:
        """Bir tarama döngüsünün çalışıp çalışmadığını döner."""
        return self._cycle_lock.locked()

    async def run_full_cycle(self) -> Tuple[int, List[ScraperRunStatus]]:
        """Tüm portalları tarar, puan eşleştirmesi yapar, yeni olanları kaydeder ve bildirir.

        Aynı anda yalnızca bir döngü çalışabilir; çakışma durumunda ScrapeInProgressException fırlatır.
        """
        if self._cycle_lock.locked():
            raise ScrapeInProgressException(ErrorStrings.SCRAPE_ALREADY_RUNNING)
        async with self._cycle_lock:
            return await self._run_full_cycle_locked()

    def _build_entity(self, dto: AnnouncementCreate) -> Announcement:
        """Ham DTO'yu puan, bilişim etiketi ve şehir tespitiyle zenginleştirilmiş varlığa çevirir."""
        # 1. KPSS Puanı ve Öncelik Tespiti
        scores, priority = KPSSScoreMatcher.match(
            title=dto.title,
            institution=dto.institution,
            raw_content=dto.raw_content or "",
        )

        # 2. Bilgisayar Mühendisliği ve Bilişim Alan Tespiti
        it_tags = ITFieldMatcher.match_tags(
            title=dto.title,
            institution=dto.institution,
            position=dto.position or "",
            raw_content=dto.raw_content or "",
        )

        # 3. Şehir / İl Tespiti ve Normalizasyonu
        detected_city = CityMatcher.detect_city(
            title=dto.title,
            institution=dto.institution,
            position=dto.position or "",
            raw_city=dto.city,
        )

        return Announcement(
            source_key=dto.source_key,
            source_name=dto.source_name,
            title=dto.title,
            institution=dto.institution,
            position=dto.position,
            city=detected_city,
            url=dto.url,
            pdf_url=dto.pdf_url,
            publish_date=dto.publish_date,
            deadline_date=dto.deadline_date,
            raw_content=dto.raw_content,
            matched_score_types=scores,
            priority_level=priority,
            field_tags=it_tags,
            stable_url=dto.stable_url,
        )

    async def _run_full_cycle_locked(self) -> Tuple[int, List[ScraperRunStatus]]:
        logger.info("Tam tarama ve bildirim döngüsü başlatılıyor...")
        # Boş veritabanında bulunan ilk ilanlar "yeni" sayılıp bildirim yağmuruna yol açmasın diye
        # döngü başlamadan önce kayıt sayısı alınır.
        is_first_run = await self.repository.count_all() == 0
        results = await self.orchestrator.run_all()

        total_new_saved = 0
        statuses: List[ScraperRunStatus] = []

        for portal_key, created_dtos, status in results:
            new_for_portal = 0

            for dto in created_dtos:
                # Güvenlik: yalnızca http/https adresli ilanlar kabul edilir (javascript: vb. reddedilir)
                if not is_http_url(dto.url):
                    logger.warning(f"Geçersiz URL nedeniyle ilan atlandı [{portal_key}]: {dto.url!r}")
                    continue
                if dto.pdf_url and not is_http_url(dto.pdf_url):
                    dto.pdf_url = None

                entity = self._build_entity(dto)

                # Mükerrer Kontrolü ve Kayıt
                new_id = await self.repository.save(entity)
                if new_id:
                    new_for_portal += 1
                    total_new_saved += 1
                    logger.info(
                        MessageStrings.ANNOUNCEMENT_SAVED.format(
                            portal=entity.source_name,
                            title=entity.title,
                        )
                    )

            status.new_count = new_for_portal
            statuses.append(status)

        # Bildirimler kayıt aşamasından ayrıdır: başarısız gönderimler sonraki taramada yeniden denenir
        await self._notify_pending(is_first_run)

        logger.info(
            MessageStrings.ALL_SCRAPERS_COMPLETED.format(total_new=total_new_saved)
        )
        return total_new_saved, statuses

    async def _notify_pending(self, is_first_run: bool) -> None:
        """Bildirilmemiş yeni ilanları öncelik sırasıyla, hız sınırına uyarak Telegram'a iletir.

        * İlk çalıştırmada (boş veritabanı) mevcut ilanlar sessizce "bildirildi" işaretlenir.
        * Döngü başına en fazla TELEGRAM_MAX_PER_CYCLE ilan tek tek gönderilir; fazlası tek özet mesajıdır.
        * Gönderilemeyenler bildirilmemiş kalır ve TELEGRAM_RETRY_WINDOW_HOURS içinde yeniden denenir.
        """
        if not self.notifier.is_ready:
            return

        pending = await self.repository.get_unnotified_announcements(
            limit=_PENDING_FETCH_LIMIT, since_hours=settings.TELEGRAM_RETRY_WINDOW_HOURS
        )
        if not pending:
            return

        # Son başvuru günü geçmiş ilanlar için bildirim anlamsızdır: sessizce "bildirildi" işaretlenir
        today_iso = today_in_turkey().isoformat()
        expired = [i for i in pending if i.deadline_on and i.deadline_on < today_iso]
        if expired:
            await self.repository.mark_as_notified([i.id for i in expired])
            pending = [i for i in pending if i not in expired]
            if not pending:
                return

        if is_first_run and not settings.NOTIFY_ON_FIRST_RUN:
            await self.repository.mark_as_notified([i.id for i in pending])
            logger.info(MessageStrings.NOTIFY_BASELINE.format(count=len(pending)))
            return

        batch, overflow = pending[: settings.TELEGRAM_MAX_PER_CYCLE], pending[settings.TELEGRAM_MAX_PER_CYCLE :]
        sent_ids: List[int] = []
        consecutive_failures = 0
        aborted = False

        for item in batch:
            if await self.notifier.send_announcement(item):
                sent_ids.append(item.id)
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= TelegramConstants.MAX_CONSECUTIVE_FAILURES:
                    aborted = True
                    logger.warning(MessageStrings.NOTIFY_ABORTED)
                    break
            await asyncio.sleep(settings.TELEGRAM_SEND_INTERVAL_SECONDS)

        summarized_ids: List[int] = []
        if overflow and not aborted:
            summary = NotificationStrings.SUMMARY.format(count=len(overflow))
            if await self.notifier.send_text(summary):
                summarized_ids = [i.id for i in overflow]

        if sent_ids or summarized_ids:
            await self.repository.mark_as_notified(sent_ids + summarized_ids)
            logger.info(MessageStrings.NOTIFY_SUMMARY.format(sent=len(sent_ids), summarized=len(summarized_ids)))

    async def get_announcements(
        self,
        params: AnnouncementFilterParams,
    ) -> Tuple[List[AnnouncementResponse], int]:
        """Filtrelenmiş ve formatlanmış ilan listesini döner."""
        items, total_count = await self.repository.list_announcements(params)
        dtos = [AnnouncementResponse.from_entity(i) for i in items]
        return dtos, total_count

    async def get_stats(self, only_active: bool = False) -> SystemStatsResponse:
        """Sistem istatistiklerini döner."""
        return await self.repository.get_system_stats(only_active=only_active)

    def get_scraper_statuses(self) -> List[ScraperRunStatus]:
        """Tüm kazayıcıların en son çalışma metriklerini döner."""
        return self.orchestrator.get_statuses()
