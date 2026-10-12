"""İlan.gov.tr kazıyıcısı: tarayıcı alt süreci olay döngüsünden bağımsız çalışmalı."""

import asyncio
import sys
import time
from pathlib import Path

import pytest

from app.core.constants.settings import ScraperLimits
from app.core.exceptions.scraper import NetworkScraperException, ScraperException
from app.scrapers.adapters.ilan_gov_tr import IlanGovTrScraper


def fake_browser(monkeypatch, scraper, code):
    """Gerçek Chrome yerine verilen Python kodunu çalıştıran sahte 'tarayıcı' komutu kurar."""
    monkeypatch.setattr(scraper, "_build_command", lambda exe: [sys.executable, "-c", code])


def test_dump_dom_works_on_selector_event_loop(monkeypatch):
    """Windows'ta uvicorn --reload SelectorEventLoop kullanır; asyncio alt süreci orada NotImplementedError verir."""
    scraper = IlanGovTrScraper()
    fake_browser(monkeypatch, scraper, "print('<html>tamam</html>')")

    loop = asyncio.SelectorEventLoop()
    try:
        html = loop.run_until_complete(scraper._dump_dom(Path(sys.executable)))
    finally:
        loop.close()

    assert "tamam" in html


async def test_dump_dom_times_out_and_kills_the_browser(monkeypatch):
    scraper = IlanGovTrScraper()
    monkeypatch.setattr(ScraperLimits, "BROWSER_TIMEOUT_SECONDS", 0.5)
    fake_browser(monkeypatch, scraper, "import time; time.sleep(60)")

    started = time.monotonic()
    with pytest.raises(NetworkScraperException):
        await scraper._dump_dom(Path(sys.executable))
    assert time.monotonic() - started < 15, "Zaman aşımında süreç öldürülmeli, 60 sn beklenmemeli"


async def test_dump_dom_reports_start_failure_as_scraper_error(monkeypatch):
    scraper = IlanGovTrScraper()
    monkeypatch.setattr(scraper, "_build_command", lambda exe: ["/yok/boyle/bir/tarayici"])

    with pytest.raises(ScraperException) as exc:
        await scraper._dump_dom(Path("/yok"))
    assert exc.value.error_code == "SCRAPER_BROWSER_START_FAILED"


async def test_scrape_parses_announcement_links_from_dom(monkeypatch):
    html = """
    <a href="/ilan/12345/ornek-universitesi-rektorlugu-sozlesmeli-personel">ÖRNEK ÜNİVERSİTESİ REKTÖRLÜĞÜ Sözleşmeli Personel Alım İlanı</a>
    <a href="/ilan/tum-ilanlar">Tüm ilanlar menüsü bağlantısı</a>
    <a href="/ilan/9/x">kısa</a>
    """

    async def fake_dump(browser_exe):
        return html

    scraper = IlanGovTrScraper()
    monkeypatch.setattr(scraper, "_find_browser_executable", lambda: Path(sys.executable))
    monkeypatch.setattr(scraper, "_dump_dom", fake_dump)

    items = await scraper.scrape()

    assert len(items) == 1
    assert items[0].url == "https://www.ilan.gov.tr/ilan/12345/ornek-universitesi-rektorlugu-sozlesmeli-personel"
    assert items[0].institution.endswith("REKTÖRLÜĞÜ")
