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
        html = response.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        announcements: List[AnnouncementCreate] = []

        # ilanDetay.aspx bağlantılarını topla
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "ilandetay.aspx" not in href.lower():
                continue

            black_span = a.find("span", class_="black")
            patrol_span = a.find("span", class_="patrol")
            date_span = a.find("span", class_="h5date")

            institution = black_span.get_text(strip=True) if black_span else ""
            position = patrol_span.get_text(strip=True) if patrol_span else ""
            deadline_str = date_span.get_text(strip=True) if date_span else ""

            if not institution and not position:
                raw_text = " ".join(a.get_text(separator=" ", strip=True).split())
                if not raw_text or len(raw_text) < 5:
                    continue
                institution = self.portal_name
                position = raw_text

            title = f"{institution} - {position}" if institution and position else (position or institution)
            full_url = f"{self.BASE_URL}/{href.lstrip('/')}" if not href.startswith("http") else href

            announcements.append(
                AnnouncementCreate(
                    source_key=self.portal_key,
                    source_name=self.portal_name,
                    title=title,
                    institution=institution or self.portal_name,
                    position=position or None,
                    url=full_url,
                    deadline_date=deadline_str or None,
                    raw_content=f"{title} (Son Başvuru: {deadline_str})",
                )
            )

        self.logger.info(f"Kamu İlan (SBB) üzerinden {len(announcements)} ilan tespit edildi.")
        return announcements
