"""KPSS Atama Takip - Kamu İlan (SBB) Kazıyıcı Adaptörü."""

import re
from typing import List
from bs4 import BeautifulSoup

from app.core.constants.strings import PortalKeys, PortalStrings
from app.domain.schemas import AnnouncementCreate
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry


@ScraperRegistry.register
class KamuIlanSbbScraper(BaseScraper):
    """T.C. Cumhurbaşkanlığı Strateji ve Bütçe Başkanlığı Kamu İlan Adaptörü."""

    portal_key = PortalKeys.KAMU_ILAN_SBB
    portal_name = PortalStrings.KAMU_ILAN_SBB
    BASE_URL = "https://kamuilan.sbb.gov.tr"
    MENU_URL = "https://kamuilan.sbb.gov.tr/ilan_menu.aspx"

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("Kamu İlan (SBB) taranıyor...")
        response = await self._request("GET", self.MENU_URL)
        html = response.content.decode("windows-1254", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        announcements: List[AnnouncementCreate] = []

        # ilanDetay.aspx bağlantılarını topla
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "ilandetay.aspx" not in href.lower():
                continue

            raw_title = " ".join(a.get_text(strip=True).split())
            if not raw_title or len(raw_title) < 5:
                continue

            full_url = f"{self.BASE_URL}/{href.lstrip('/')}" if not href.startswith("http") else href

            # Tarih parantezini ayrıştırma (Örn: "ANKARA ÜNİVERSİTESİ 19 MEMUR ALACAK ( 28 Eylül - 13 Ekim)")
            deadline_match = re.search(r"\(\s*([^)]+)\s*\)$", raw_title)
            deadline_str = deadline_match.group(1) if deadline_match else None

            # Kurum adı tahmini
            institution = raw_title
            for kw in ["ALACAK", "ALIMI", "TEMİN", "MEMUR", "PERSONEL"]:
                if kw in raw_title:
                    institution = raw_title.split(kw)[0].strip()
                    break

            announcements.append(
                AnnouncementCreate(
                    source_key=self.portal_key,
                    source_name=self.portal_name,
                    title=raw_title,
                    institution=institution or self.portal_name,
                    url=full_url,
                    deadline_date=deadline_str,
                    raw_content=f"{raw_title} (Detay: {full_url})",
                )
            )

        self.logger.info(f"Kamu İlan (SBB) üzerinden {len(announcements)} ilan tespit edildi.")
        return announcements
