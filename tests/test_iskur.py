"""İŞKUR kazıyıcı: gerçek sayfa yapısından alınmış fixture ile ayrıştırma testleri."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.core.exceptions.scraper import ParsingScraperException
from app.scrapers.adapters.iskur import IskurScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "iskur_page.html").read_text(encoding="utf-8")


def parse(html: str):
    return IskurScraper()._parse_page(BeautifulSoup(html, "html.parser"))


def test_parses_structured_fields():
    first, second = parse(FIXTURE)

    assert first.position == "Özel Güvenlik Görevlisi (Silahsız)"
    assert first.institution == "T.C.MARMARA ÜNİVERSİTESİ REK.İDARİ MALİ İŞLER DAİRE BAŞK."
    assert first.city == "İSTANBUL / KADIKÖY"
    assert first.deadline_date == "16.10.2026"
    assert first.url == "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanDetay.aspx?uiID=00009847600&isyeriTuru=Kamu"
    assert "7 açık pozisyon" in first.raw_content
    assert second.city == "ŞANLIURFA / ŞANLIURFA MERKEZ"
    assert first.url != second.url, "Her ilanın benzersiz detay URL'si olmalı"


def test_institution_has_no_stray_characters():
    for item in parse(FIXTURE):
        assert not item.institution.endswith("K")  # eski regex komşu hücrenin harfini sızdırıyordu


@pytest.mark.parametrize("position", ["Araç Sürücüsü", "Araştırmacı", "Aranan Eleman"])
def test_positions_starting_with_ara_are_not_dropped(position):
    html = FIXTURE.replace("Özel Güvenlik Görevlisi (Silahsız)", position)
    assert position in [i.position for i in parse(html)]


def test_missing_table_raises_parsing_error():
    with pytest.raises(ParsingScraperException):
        parse("<html><body><p>bakım</p></body></html>")


def test_form_state_keeps_viewstate_and_selected_radio():
    state = IskurScraper()._next_request_state(BeautifulSoup(FIXTURE, "html.parser"), IskurScraper.NEXT_PAGE_TARGET)
    assert state["__VIEWSTATE"] == "abc"
    assert state["ctl04$IsyeriTuruRadios"] == "kamuRadio"
    assert state["__EVENTTARGET"] == IskurScraper.NEXT_PAGE_TARGET
