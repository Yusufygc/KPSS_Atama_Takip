"""KPSS Atama Takip - İlan.gov.tr (BİK) Kazıyıcı Adaptörü."""

import asyncio
import shutil
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup

from app.config import settings
from app.core.constants.settings import ScraperLimits
from app.core.constants.strings import ErrorStrings, PortalKeys, PortalStrings
from app.core.exceptions.scraper import NetworkScraperException, ScraperException
from app.domain.schemas import AnnouncementCreate
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry


@ScraperRegistry.register
class IlanGovTrScraper(BaseScraper):
    """Basın İlan Kurumu (İlan.gov.tr) Personel Alımı Adaptörü."""

    portal_key = PortalKeys.ILAN_GOV_TR
    portal_name = PortalStrings.ILAN_GOV_TR
    BASE_URL = "https://www.ilan.gov.tr"
    CATEGORY_URL = "https://www.ilan.gov.tr/ilan/tum-ilanlar/personel-alimi?ats=5"

    def _find_browser_executable(self) -> Optional[Path]:
        """Yapılandırılmış veya sistemdeki Chrome / Edge / Chromium yürütülebilir dosyasını arar."""
        if settings.BROWSER_EXECUTABLE_PATH:
            configured = Path(settings.BROWSER_EXECUTABLE_PATH)
            return configured if configured.exists() else None

        for command in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
            found = shutil.which(command)
            if found:
                return Path(found)

        candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ]
        return next((c for c in candidates if c.exists()), None)

    async def _dump_dom(self, browser_exe: Path) -> str:
        """Headless tarayıcıyla sayfanın DOM çıktısını alır; zaman aşımında süreci öldürür."""
        cmd = [
            str(browser_exe),
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=6000",
        ]
        if settings.BROWSER_NO_SANDBOX:
            cmd.append("--no-sandbox")
        cmd += ["--dump-dom", self.CATEGORY_URL]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=ScraperLimits.BROWSER_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError as exc:
            # Artık Chrome süreçlerinin birikmesini önlemek için süreci sonlandır
            process.kill()
            await process.wait()
            raise NetworkScraperException(
                message=ErrorStrings.BROWSER_TIMEOUT,
                portal_key=self.portal_key,
                url=self.CATEGORY_URL,
            ) from exc
        return stdout.decode("utf-8", errors="ignore")

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("İlan.gov.tr personel alımları taranıyor...")
        browser_exe = self._find_browser_executable()
        announcements: List[AnnouncementCreate] = []

        if not browser_exe:
            raise ScraperException(
                message=ErrorStrings.BROWSER_NOT_FOUND,
                portal_key=self.portal_key,
                error_code="SCRAPER_BROWSER_NOT_FOUND",
            )

        # SPA sayfasını asenkron headless tarayıcı ile DOM dump al
        html = await self._dump_dom(browser_exe)

        soup = BeautifulSoup(html, "html.parser")
        seen_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/ilan/" not in href or "/tum-ilanlar" in href or "/kategori/" in href:
                continue

            title = " ".join(a.get_text(strip=True).split())
            if len(title) < 10 or href in seen_urls:
                continue
            seen_urls.add(href)

            full_url = f"{self.BASE_URL}{href}" if not href.startswith("http") else href

            # Kurum adı tahmini (Örn: "... BAŞKANLIĞI", "... ÜNİVERSİTESİ")
            institution = "Kamu Kurumu"
            for kw in ["BAŞKANLIĞI", "REKTÖRLÜĞÜ", "MÜDÜRLÜĞÜ", "BELEDİYESİ", "BİRLİĞİ"]:
                if kw in title:
                    parts = title.split(kw)
                    institution = (parts[0] + kw).strip()
                    break

            announcements.append(
                AnnouncementCreate(
                    source_key=self.portal_key,
                    source_name=self.portal_name,
                    title=title,
                    institution=institution,
                    url=full_url,
                    raw_content=f"{institution} - {title}",
                )
            )

        self.logger.info(f"İlan.gov.tr üzerinden {len(announcements)} ilan tespit edildi.")
        return announcements
