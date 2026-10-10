"""KPSS Atama Takip - İlan.gov.tr (BİK) Kazıyıcı Adaptörü."""

import asyncio
from pathlib import Path
from typing import List, Optional
from bs4 import BeautifulSoup

from app.core.constants.strings import PortalKeys, PortalStrings
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
        """Sistemdeki Chrome veya Edge yürütülebilir dosyasını arar."""
        candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("İlan.gov.tr personel alımları taranıyor...")
        browser_exe = self._find_browser_executable()
        announcements: List[AnnouncementCreate] = []

        if not browser_exe:
            self.logger.warning("Headless tarayıcı (Chrome/Edge) bulunamadı. İlan.gov.tr atlanıyor.")
            return announcements

        try:
            # SPA sayfasını asenkron headless tarayıcı ile DOM dump al
            cmd = [
                str(browser_exe),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--virtual-time-budget=6000",
                "--dump-dom",
                self.CATEGORY_URL,
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=15.0)
            html = stdout.decode("utf-8", errors="ignore")

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

        except Exception as e:
            self.logger.warning(f"İlan.gov.tr taramasında hata: {e}")
            return announcements

        self.logger.info(f"İlan.gov.tr üzerinden {len(announcements)} ilan tespit edildi.")
        return announcements
