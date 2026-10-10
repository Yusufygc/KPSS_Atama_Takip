"""KPSS Atama Takip - T.C. Resmî Gazete Kazıyıcı Adaptörü."""

from datetime import datetime, timedelta, timezone
from typing import List
from bs4 import BeautifulSoup

from app.core.constants.strings import PortalKeys, PortalStrings
from app.domain.schemas import AnnouncementCreate
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry


@ScraperRegistry.register
class ResmiGazeteScraper(BaseScraper):
    """Resmî Gazete Çeşitli İlânlar (Bölüm 4) Günlük Personel Alım Adaptörü."""

    portal_key = PortalKeys.RESMI_GAZETE
    portal_name = PortalStrings.RESMI_GAZETE
    BASE_URL = "https://www.resmigazete.gov.tr"

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("Resmî Gazete güncel ve geçmiş son 3 günün ilanları taranıyor...")
        announcements: List[AnnouncementCreate] = []
        today = datetime.now(timezone.utc)

        # Son 3 günü tara (Hafta sonu veya dün yayınlananları kaçırmamak için)
        for days_back in range(3):
            target_date = today - timedelta(days=days_back)
            year = target_date.strftime("%Y")
            month = target_date.strftime("%m")
            day = target_date.strftime("%d")
            date_str = f"{year}{month}{day}"

            url = f"{self.BASE_URL}/ilanlar/eskiilanlar/{year}/{month}/{date_str}-4.htm"
            try:
                response = await self._request("GET", url, retries=1)
                if response.status_code != 200:
                    continue

                html = response.content.decode("windows-1254", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    text = " ".join(a.get_text(strip=True).split())

                    # İlan başlığı ve PDF linki kontrolü
                    if not text or len(text) < 5:
                        continue

                    # PDF linkini mutlak adrese çevir
                    if href.startswith("http"):
                        pdf_url = href
                    else:
                        pdf_url = f"{self.BASE_URL}/ilanlar/eskiilanlar/{year}/{month}/{href.lstrip('/')}"

                    # Başlıktan kurum ve unvan ayrıştırma
                    institution = text.split("Rektörlüğünden")[0] if "Rektörlüğünden" in text else text.split(":")[0]
                    institution = institution.strip().rstrip(":")

                    announcements.append(
                        AnnouncementCreate(
                            source_key=self.portal_key,
                            source_name=self.portal_name,
                            title=text,
                            institution=institution or self.portal_name,
                            url=pdf_url,
                            pdf_url=pdf_url,
                            publish_date=f"{year}-{month}-{day}",
                            raw_content=f"Resmî Gazete İlanı ({year}-{month}-{day}): {text}",
                        )
                    )

            except Exception as e:
                self.logger.debug(f"{date_str} Resmî Gazete sayfası kontrol edilirken: {e}")
                continue

        self.logger.info(f"Resmî Gazete üzerinden {len(announcements)} ilan tespit edildi.")
        return announcements
