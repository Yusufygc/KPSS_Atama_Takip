"""KPSS Atama Takip - Arka Plan Zamanlayıcı Servisi (APScheduler)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.core.dates import TURKEY_TZ
from app.core.exceptions.scraper import ScrapeInProgressException
from app.core.logging import get_logger
from app.services.announcement_service import AnnouncementService
from app.services.backup import backup_database

logger = get_logger("services.scheduler")


class SchedulerService:
    """Periyodik arka plan taramasını yöneten zamanlayıcı."""

    def __init__(self, service: Optional[AnnouncementService] = None) -> None:
        self.service = service or AnnouncementService()
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

    async def _scheduled_task(self) -> None:
        """Belirlenen aralıklarla otomatik çalışan tarama görevi."""
        logger.info("Zamanlanmış otomatik tarama görevi tetiklendi.")
        try:
            new_count, statuses = await self.service.run_full_cycle()
            logger.info(f"Zamanlanmış tarama tamamlandı. Yeni ilan: {new_count}")
        except ScrapeInProgressException:
            logger.info("Önceki tarama hâlâ sürüyor, bu tetikleme atlandı.")
        except Exception as e:
            logger.error(f"Zamanlanmış tarama sırasında hata: {e}")

    async def _backup_task(self) -> None:
        """Günlük veritabanı yedeği (hata uygulamayı etkilemez)."""
        try:
            await backup_database()
        except Exception as e:  # noqa: BLE001 - yedekleme hatası zamanlayıcıyı durdurmamalı
            logger.error(f"Veritabanı yedeklenemedi: {e}")

    def start(self) -> None:
        """Zamanlayıcıyı başlatır."""
        if self._is_running:
            return

        interval_minutes = settings.SCRAPER_INTERVAL_MINUTES
        job_options = {}
        if settings.SCRAPER_RUN_ON_STARTUP:
            # Açılışta ilk taramayı kısa gecikmeyle başlat; aksi halde veri bir aralık boyunca bayat kalır.
            # (APScheduler'da next_run_time=None işi duraklatır, bu yüzden yalnızca gerektiğinde verilir.)
            job_options["next_run_time"] = datetime.now(timezone.utc) + timedelta(
                seconds=settings.SCRAPER_STARTUP_DELAY_SECONDS
            )
        self.scheduler.add_job(
            self._scheduled_task,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="periodic_scraper_job",
            name="Periyodik KPSS İlan Taraması",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            **job_options,
        )
        if settings.DB_BACKUP_ENABLED:
            self.scheduler.add_job(
                self._backup_task,
                trigger=CronTrigger(hour=settings.DB_BACKUP_HOUR, minute=0, timezone=TURKEY_TZ),
                id="daily_db_backup_job",
                name="Günlük Veritabanı Yedeği",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
        self.scheduler.start()
        self._is_running = True
        logger.info(
            f"Arka plan zamanlayıcısı başlatıldı (Periyot: {interval_minutes} dakika)."
        )

    def stop(self) -> None:
        """Zamanlayıcıyı durdurur."""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Arka plan zamanlayıcısı durduruldu.")
