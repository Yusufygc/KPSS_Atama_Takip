"""KPSS Atama Takip - İlan İş Mantığı ve Orkestrasyon Servisi."""

import asyncio
from typing import List, Optional, Tuple

from app.core.constants.strings import ErrorStrings, MessageStrings
from app.core.exceptions.scraper import ScrapeInProgressException
from app.core.logging import get_logger
from app.core.scoring.city_matcher import CityMatcher
from app.core.scoring.it_field_matcher import ITFieldMatcher
from app.core.scoring.strategy import KPSSScoreMatcher
from app.core.security import is_http_url
from app.domain.models import Announcement
from app.domain.schemas import (
    AnnouncementFilterParams,
    AnnouncementResponse,
    ScraperRunStatus,
    SystemStatsResponse,
)
from app.infrastructure.database.repository import AnnouncementRepository
from app.infrastructure.notification.telegram import TelegramNotifier
from app.scrapers.orchestrator import ScraperOrchestrator

logger = get_logger("services.announcement")


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

    async def _run_full_cycle_locked(self) -> Tuple[int, List[ScraperRunStatus]]:
        logger.info("Tam tarama ve bildirim döngüsü başlatılıyor...")
        results = await self.orchestrator.run_all()

        total_new_saved = 0
        statuses: List[ScraperRunStatus] = []

        for portal_key, created_dtos, status in results:
            new_for_portal = 0

            for dto in created_dtos:
                # 0. Güvenlik: yalnızca http/https adresli ilanlar kabul edilir (javascript: vb. reddedilir)
                if not is_http_url(dto.url):
                    logger.warning(f"Geçersiz URL nedeniyle ilan atlandı [{portal_key}]: {dto.url!r}")
                    continue
                if dto.pdf_url and not is_http_url(dto.pdf_url):
                    dto.pdf_url = None

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

                entity = Announcement(
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
                )

                # 2. Mükerrer Kontrolü ve Kayıt
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

                    # 3. Anlık Bildirim Gönderimi (Telegram)
                    if self.notifier.is_enabled and self.notifier.is_configured:
                        sent = await self.notifier.send_announcement(entity)
                        if sent:
                            await self.repository.mark_as_notified([new_id])

            status.new_count = new_for_portal
            statuses.append(status)

        logger.info(
            MessageStrings.ALL_SCRAPERS_COMPLETED.format(total_new=total_new_saved)
        )
        return total_new_saved, statuses

    async def get_announcements(
        self,
        params: AnnouncementFilterParams,
    ) -> Tuple[List[AnnouncementResponse], int]:
        """Filtrelenmiş ve formatlanmış ilan listesini döner."""
        items, total_count = await self.repository.list_announcements(params)
        dtos = [AnnouncementResponse.from_entity(i) for i in items]
        return dtos, total_count

    async def get_stats(self) -> SystemStatsResponse:
        """Sistem istatistiklerini döner."""
        return await self.repository.get_system_stats()

    def get_scraper_statuses(self) -> List[ScraperRunStatus]:
        """Tüm kazayıcıların en son çalışma metriklerini döner."""
        return self.orchestrator.get_statuses()
