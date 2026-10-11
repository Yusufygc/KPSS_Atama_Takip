"""KPSS Atama Takip - Kariyer Kapısı (CBİKO) Kazıyıcı Adaptörü."""

from typing import List

from app.core.constants.strings import PortalKeys, PortalStrings
from app.core.exceptions.scraper import ParsingScraperException
from app.domain.schemas import AnnouncementCreate
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry


@ScraperRegistry.register
class KariyerKapisiScraper(BaseScraper):
    """Cumhurbaşkanlığı İnsan Kaynakları Ofisi (Kariyer Kapısı) Doğrudan API Adaptörü."""

    portal_key = PortalKeys.KARIYER_KAPISI
    portal_name = PortalStrings.KARIYER_KAPISI
    API_URL = "https://api.kariyerkapisi.gov.tr/api/ilan/GetIseAlimPage"
    BASE_PAGE_URL = "https://kariyerkapisi.gov.tr/isealim"
    # Sitenin kendi JS'i (Main.js) "IlanDetay?i=" bağlantısını /isealim sayfasına göre göreli üretir;
    # bu da kök dizindeki /IlanDetay yoludur. /isealim/IlanDetay WAF tarafından 406 ile engellenir.
    DETAIL_URL_TEMPLATE = "https://kariyerkapisi.gov.tr/IlanDetay?i={guid}"

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("Kariyer Kapısı API sorgulanıyor...")
        payload = {"krM_ID": 0, "searchText": "", "il": "0", "ilanTuru": "0"}

        response = await self._request(
            method="POST",
            url=self.API_URL,
            json_data=payload,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
                "Origin": "https://kariyerkapisi.gov.tr",
                "Referer": "https://kariyerkapisi.gov.tr/",
            },
        )

        try:
            data = response.json()
        except Exception as e:
            raise ParsingScraperException(
                message=f"JSON yanıtı ayrıştırılamadı: {e}",
                portal_key=self.portal_key,
                raw_snippet=response.text[:200],
            ) from e

        raw_items = data.get("searchIlan", [])
        self.logger.info(f"API üzerinden {len(raw_items)} aktif ilan alındı.")

        announcements: List[AnnouncementCreate] = []
        for item in raw_items:
            institution = (item.get("kurumAdi") or "").strip()
            title = (item.get("ilanBaslik") or "").strip()
            deadline = item.get("bitTarih")
            guid = item.get("guid")
            direct_link = (item.get("basvuruLinki") or "").strip()

            # İlan detay URL'si belirleme
            if direct_link.startswith("http"):
                url = direct_link
            elif guid:
                url = self.DETAIL_URL_TEMPLATE.format(guid=guid)
            else:
                url = self.BASE_PAGE_URL

            if title and institution:
                announcements.append(
                    AnnouncementCreate(
                        source_key=self.portal_key,
                        source_name=self.portal_name,
                        title=title,
                        institution=institution,
                        url=url,
                        deadline_date=deadline,
                        raw_content=f"{institution} - {title}",
                    )
                )

        return announcements
