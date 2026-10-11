"""KPSS Atama Takip - İŞKUR E-Şube Kamu İlanları Kazıyıcı Adaptörü."""

import re
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.constants.settings import ScraperLimits
from app.core.constants.strings import PortalKeys, PortalStrings
from app.core.exceptions.scraper import ParsingScraperException
from app.domain.schemas import AnnouncementCreate
from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry


@ScraperRegistry.register
class IskurScraper(BaseScraper):
    """İŞKUR E-Şube Kamu İşyeri ve Personel Alımları Adaptörü (ASP.NET WebForms).

    Sonuç tablosundaki her satır sabit kimlik son ekleri taşıyan span'lerden oluşur
    (ctlIsverenDL, ctlCalismaYeriDL, ctlSonBasvuruTarihi ...). Metin birleştirme yerine
    bu alanlar doğrudan okunur; sayfalama `btnNext` postback'iyle ilerletilir.
    """

    portal_key = PortalKeys.ISKUR
    portal_name = PortalStrings.ISKUR
    PAGE_URL = "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx"
    DETAIL_URL_TEMPLATE = "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanDetay.aspx?uiID={ilan_no}&isyeriTuru=Kamu"

    GRID_ID = "ctl04_ctlGridAcikIslerListeDetail"
    SEARCH_TARGET = "ctl04$ctlAcikIsPageCommand$CommandItem_Search"
    NEXT_PAGE_TARGET = "ctl04$ctlDataPagerDetay$btnNext"
    NEXT_PAGE_LINK_ID = "ctl04_ctlDataPagerDetay_btnNext"
    PUBLIC_SECTOR_RADIO = ("ctl04$IsyeriTuruRadios", "kamuRadio")

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://esube.iskur.gov.tr",
        "Referer": PAGE_URL,
    }

    _ILAN_NO_RE = re.compile(r"flag_(\d+)$")
    _DEADLINE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
    _WORK_PLACE_RE = re.compile(r"Çalışma Yeri:\s*(.+?)\s*\)?\s*$")

    @staticmethod
    def _collect_form_state(soup: BeautifulSoup) -> Dict[str, str]:
        """ASP.NET formundaki (ViewState dahil) gönderilecek alanları toplar."""
        form = soup.find("form")
        if not form:
            raise ParsingScraperException("İŞKUR formu bulunamadı", PortalKeys.ISKUR.value)

        data: Dict[str, str] = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            input_type = (inp.get("type") or "text").lower()
            if not name or "AramaKaydet" in name:
                continue
            if input_type in ("radio", "checkbox"):
                if inp.has_attr("checked"):
                    data[name] = inp.get("value", "")
            elif input_type not in ("submit", "button", "image"):
                data[name] = inp.get("value", "")

        for sel in form.find_all("select"):
            name = sel.get("name")
            if not name:
                continue
            option = sel.find("option", selected=True) or sel.find("option")
            data[name] = option.get("value", "") if option else ""
        return data

    def _parse_row(self, link: Tag) -> Optional[AnnouncementCreate]:
        """Bir ilan satırını (başlık bağlantısından başlayarak) AnnouncementCreate'e çevirir."""
        match = self._ILAN_NO_RE.search(link.get("id", ""))
        row = link.find_parent("tr")
        if not match or row is None:
            return None
        ilan_no = match.group(1)

        def text_of(suffix: str) -> str:
            node = row.find("span", id=re.compile(suffix + r"$"))
            return node.get_text(" ", strip=True) if node else ""

        position = link.get_text(" ", strip=True)
        institution = text_of("ctlIsverenDL") or "Kamu Kurumu"
        work_place_text = text_of("ctlCalismaYeriDL")
        place_match = self._WORK_PLACE_RE.search(work_place_text)
        city = place_match.group(1) if place_match else None

        deadline_match = self._DEADLINE_RE.search(text_of("ctlSonBasvuruTarihi"))
        conditions = " / ".join(
            part
            for part in (text_of("ctlIsverenTurDL"), text_of("ctlCalismaPeriyotDL"), text_of("ctlCalismaSekliDL"))
            if part
        )
        vacancy = text_of("Label9")

        raw_parts = [position, institution, conditions, f"{vacancy} açık pozisyon" if vacancy else "", work_place_text]
        return AnnouncementCreate(
            source_key=self.portal_key,
            source_name=self.portal_name,
            title=f"{position} - {institution}" if position else institution,
            institution=institution,
            position=position or None,
            city=city,
            url=self.DETAIL_URL_TEMPLATE.format(ilan_no=ilan_no),
            deadline_date=deadline_match.group(0) if deadline_match else None,
            raw_content=" | ".join(part for part in raw_parts if part),
        )

    def _parse_page(self, soup: BeautifulSoup) -> List[AnnouncementCreate]:
        grid = soup.find("table", id=self.GRID_ID)
        if grid is None:
            raise ParsingScraperException("İŞKUR sonuç tablosu bulunamadı", self.portal_key)
        items = (self._parse_row(a) for a in grid.find_all("a", id=self._ILAN_NO_RE))
        return [item for item in items if item is not None]

    def _next_request_state(self, soup: BeautifulSoup, event_target: str) -> Dict[str, str]:
        """Bir sonraki postback için form durumunu (ViewState dahil) hazırlar."""
        state = self._collect_form_state(soup)
        state[self.PUBLIC_SECTOR_RADIO[0]] = self.PUBLIC_SECTOR_RADIO[1]
        state["__EVENTTARGET"] = event_target
        state["__EVENTARGUMENT"] = ""
        return state

    async def scrape(self) -> List[AnnouncementCreate]:
        self.logger.info("İŞKUR E-Şube kamu ilanları taranıyor...")
        announcements: Dict[str, AnnouncementCreate] = {}

        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=25.0, headers=self.HEADERS) as client:
            # 1. Formu GET ile al, kamu aramasını POST ile tetikle
            get_resp = await client.get(self.PAGE_URL)
            get_resp.raise_for_status()
            form_state = self._next_request_state(BeautifulSoup(get_resp.text, "html.parser"), self.SEARCH_TARGET)

            for page_number in range(1, ScraperLimits.ISKUR_MAX_PAGES + 1):
                resp = await client.post(self.PAGE_URL, data=form_state)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content.decode("utf-8", errors="ignore"), "html.parser")

                page_items = self._parse_page(soup)
                for item in page_items:
                    announcements[item.url] = item
                self.logger.debug(f"İŞKUR sayfa {page_number}: {len(page_items)} ilan")

                # Sonraki sayfa bağlantısı yoksa (devre dışı) son sayfadayız
                has_next = soup.find("a", id=self.NEXT_PAGE_LINK_ID, href=True) is not None
                if not page_items or not has_next:
                    break
                form_state = self._next_request_state(soup, self.NEXT_PAGE_TARGET)

        self.logger.info(f"İŞKUR üzerinden {len(announcements)} kamu ilanı tespit edildi.")
        return list(announcements.values())
