"""KPSS Atama Takip - Arka Plan Zamanlayıcı Servisi (APScheduler)."""

from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.core.exceptions.scraper import ScrapeInProgressException
from app.core.logging import get_logger
from app.services.announcement_service import AnnouncementService

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

    def start(self) -> None:
        """Zamanlayıcıyı başlatır."""
        if self._is_running:
            return

        interval_minutes = settings.SCRAPER_INTERVAL_MINUTES
        self.scheduler.add_job(
            self._scheduled_task,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="periodic_scraper_job",
            max_instances=1,
            coalesce=True,
            name="Periyodik KPSS İlan Taraması",
            replace_existing=True,
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
