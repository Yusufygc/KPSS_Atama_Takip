"""KPSS Atama Takip - İŞKUR E-Şube Kamu İlanları Kazıyıcı Adaptörü."""

import re
from typing import List
from bs4 import BeautifulSoup
import httpx

from app.core.constants.strings import PortalKeys, PortalStrings
from app.core.exceptions.scraper import ParsingScraperException
from app.domain.schemas import AnnouncementCreate
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry


@ScraperRegistry.register
class IskurScraper(BaseScraper):
    """İŞKUR E-Şube Kamu İşyeri ve Personel Alımları Adaptörü."""

    portal_key = PortalKeys.ISKUR
    portal_name = PortalStrings.ISKUR
    PAGE_URL = "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx"

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("İŞKUR E-Şube kamu ilanları taranıyor...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://esube.iskur.gov.tr",
            "Referer": self.PAGE_URL,
        }

        announcements: List[AnnouncementCreate] = []

        try:
            async with httpx.AsyncClient(verify=False, timeout=25.0) as client:
                # 1. Sayfayı GET ile açıp ViewState ve form verilerini al
                get_resp = await client.get(self.PAGE_URL, headers=headers)
                soup = BeautifulSoup(get_resp.text, "html.parser")

                form_data = {}
                form = soup.find("form")
                if not form:
                    raise ParsingScraperException("İŞKUR formu bulunamadı", self.portal_key)

                for inp in form.find_all("input"):
                    name = inp.get("name")
                    val = inp.get("value", "")
                    t = inp.get("type", "text").lower()
                    if not name or "AramaKaydet" in name:
                        continue
                    if t in ["radio", "checkbox"]:
                        if inp.has_attr("checked"):
                            form_data[name] = val
                    else:
                        form_data[name] = val

                for sel in form.find_all("select"):
                    name = sel.get("name")
                    if not name:
                        continue
                    opt = sel.find("option", selected=True) or sel.find("option")
                    form_data[name] = opt.get("value", "") if opt else ""

                # 2. Kamu aramasını tetikle
                form_data["ctl04$IsyeriTuruRadios"] = "kamuRadio"
                form_data["__EVENTTARGET"] = "ctl04$ctlAcikIsPageCommand$CommandItem_Search"
                form_data["__EVENTARGUMENT"] = ""

                # 3. POST isteği gönder
                post_resp = await client.post(self.PAGE_URL, headers=headers, data=form_data)
                post_soup = BeautifulSoup(post_resp.content.decode("utf-8", errors="ignore"), "html.parser")

                rows = post_soup.find_all("tr")
                for r in rows:
                    cells = [c.get_text(strip=True) for c in r.find_all(["td", "th"]) if c.get_text(strip=True)]
                    if len(cells) < 3 or "Ara" in cells[0]:
                        continue

                    raw_info = cells[0]
                    location_info = cells[1] if len(cells) > 1 else ""
                    date_info = cells[2] if len(cells) > 2 else ""

                    # Tarih tespiti (Örn: "13.10.2026")
                    date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", date_info)
                    deadline = date_match.group(1) if date_match else None

                    # Şehir tespiti
                    city = None
                    if "Çalışma Yeri:" in location_info:
                        city = location_info.split("Çalışma Yeri:")[-1].strip().rstrip(")")

                    # Başlık ve kurum ayırma (Örn: "... BELEDİYE BAŞK.")
                    inst_match = re.search(r"([A-ZÇĞİÖŞÜ\s]+(?:BELEDİYE|MÜDÜRLÜĞÜ|İŞLETMESİ|BAŞKANLIĞI)[A-ZÇĞİÖŞÜ\s\.]*)", raw_info)
                    institution = inst_match.group(1).strip() if inst_match else "Kamu Kurumu"
                    position = raw_info.split(institution)[0].strip() if institution in raw_info else raw_info

                    title = f"{position} ({institution})" if position else institution

                    announcements.append(
                        AnnouncementCreate(
                            source_key=self.portal_key,
                            source_name=self.portal_name,
                            title=title,
                            institution=institution,
                            position=position,
                            city=city,
                            url=self.PAGE_URL,
                            deadline_date=deadline,
                            raw_content=f"{raw_info} | {location_info} | {date_info}",
                        )
                    )

        except Exception as e:
            self.logger.warning(f"İŞKUR taramasında hata oluştu: {e}")
            # İzolasyon: İŞKUR geçici çökse bile boş liste döner
            return announcements

        self.logger.info(f"İŞKUR üzerinden {len(announcements)} kamu ilanı tespit edildi.")
        return announcements
