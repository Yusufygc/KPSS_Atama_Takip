"""KPSS Atama Takip - Yerel Yönetimler GM Kazıyıcı Adaptörü."""

import re
from typing import List
from bs4 import BeautifulSoup

from app.core.constants.strings import PortalKeys, PortalStrings
from app.domain.schemas import AnnouncementCreate
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry


@ScraperRegistry.register
class YerelYonetimlerScraper(BaseScraper):
    """Yerel Yönetimler Genel Müdürlüğü Belediye Personel Duyuruları Adaptörü."""

    portal_key = PortalKeys.YEREL_YONETIMLER
    portal_name = PortalStrings.YEREL_YONETIMLER
    BASE_URL = "https://yerelyonetimler.csb.gov.tr"
    DUYURU_URL = "https://yerelyonetimler.csb.gov.tr/duyurular"

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("Yerel Yönetimler GM duyuruları taranıyor...")
        response = await self._request("GET", self.DUYURU_URL)
        html = response.content.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        announcements: List[AnnouncementCreate] = []

        # Duyuru bağlantılarını topla
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "-duyuru-" not in href:
                continue

            raw_text = " ".join(a.get_text(strip=True).split())
            if not raw_text or len(raw_text) < 10:
                continue

            full_url = href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"

            # Tarih başlığını ayrıştırma (Örn: "09 Ekim 2026 ISPARTA İLİ SARIİDRİS BELEDİYE...")
            date_match = re.match(r"^(\d{1,2}\s+[a-zA-ZçÇğĞıİöÖşŞüÜ]+\s+\d{4})", raw_text)
            publish_date = date_match.group(1) if date_match else None
            title = raw_text[len(publish_date):].strip() if publish_date else raw_text

            # Kurum adı tahmini (Örn: "... BELEDİYESİ", "... BELEDİYE BAŞKANLIĞI")
            institution_match = re.search(r"([A-ZÇĞİÖŞÜ\s]+BELEDİYE[A-ZÇĞİÖŞÜ\s]*)", title)
            institution = institution_match.group(1).strip() if institution_match else "Belediye Başkanlığı"

            announcements.append(
                AnnouncementCreate(
                    source_key=self.portal_key,
                    source_name=self.portal_name,
                    title=title,
                    institution=institution,
                    url=full_url,
                    publish_date=publish_date,
                    raw_content=f"{publish_date or ''} - {title}",
                )
            )

        self.logger.info(f"Yerel Yönetimler GM üzerinden {len(announcements)} ilan tespit edildi.")
        return announcements
