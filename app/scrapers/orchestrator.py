"""KPSS Atama Takip - Kazıyıcı Orkestrasyon ve Eşzamanlı Çalıştırma Motoru."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from app.core.constants.icons import PortalIcons
from app.core.constants.strings import MessageStrings
from app.core.logging import get_logger
from app.domain.schemas import AnnouncementCreate, ScraperRunStatus
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry

# Adaptörlerin kayıt defterine yüklenmesini garanti et
import app.scrapers.adapters  # noqa: F401

logger = get_logger("scrapers.orchestrator")


class ScraperOrchestrator:
    """Tüm portal kazıyıcılarını eşzamanlı (asenkron paralel) yöneten orkestratör."""

    def __init__(self) -> None:
        self._last_statuses: Dict[str, ScraperRunStatus] = {}

    async def _execute_single_safe(
        self,
        scraper: BaseScraper,
    ) -> Tuple[str, List[AnnouncementCreate], ScraperRunStatus]:
        """Tek bir kazıyıcıyı hata izolasyonu ve süre ölçümüyle çalıştırır."""
        portal_key = scraper.portal_key
        portal_name = scraper.portal_name
        portal_icon = PortalIcons.get_for_portal(portal_key)

        logger.info(MessageStrings.SCRAPER_STARTING.format(portal=portal_name))
        start_time = time.perf_counter()

        status = ScraperRunStatus(
            portal_key=portal_key,
            portal_name=portal_name,
            portal_icon=portal_icon,
            status="running",
            last_run_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            items = await scraper.scrape()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            status.status = "success"
            status.found_count = len(items)
            status.duration_ms = duration_ms

            logger.info(
                MessageStrings.SCRAPER_FINISHED.format(
                    portal=portal_name,
                    found=len(items),
                    new="-",
                )
                + f" ({duration_ms} ms)"
            )
            self._last_statuses[portal_key] = status
            return portal_key, items, status

        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                MessageStrings.SCRAPER_FAILED.format(portal=portal_name, error=str(e))
            )
            status.status = "error"
            status.error_message = str(e)
            status.duration_ms = duration_ms
            self._last_statuses[portal_key] = status
            return portal_key, [], status

    async def run_all(self) -> List[Tuple[str, List[AnnouncementCreate], ScraperRunStatus]]:
        """Kayıtlı tüm portalları eşzamanlı (paralel) olarak tarar."""
        scrapers = ScraperRegistry.get_all()
        logger.info(f"Eşzamanlı tarama başlatılıyor. Kayıtlı portal sayısı: {len(scrapers)}")

        tasks = [self._execute_single_safe(s) for s in scrapers]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def run_single(
        self,
        portal_key: str,
    ) -> Tuple[str, List[AnnouncementCreate], ScraperRunStatus]:
        """Belirtilen tek bir portalı çalıştırır."""
        scraper = ScraperRegistry.get(portal_key)
        return await self._execute_single_safe(scraper)

    def get_statuses(self) -> List[ScraperRunStatus]:
        """Tüm portalların en son çalışma durumlarını döner."""
        all_keys = ScraperRegistry.get_registered_keys()
        statuses = []
        for key in all_keys:
            if key in self._last_statuses:
                statuses.append(self._last_statuses[key])
            else:
                scraper = ScraperRegistry.get(key)
                statuses.append(
                    ScraperRunStatus(
                        portal_key=key,
                        portal_name=scraper.portal_name,
                        portal_icon=PortalIcons.get_for_portal(key),
                        status="idle",
                    )
                )
        return statuses
