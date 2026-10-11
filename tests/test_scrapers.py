"""Kazıyıcı motoru: kayıt defteri, orkestratör hata izolasyonu ve adaptör davranışları."""

import asyncio

import pytest

from app.config import settings
from app.core.constants.strings import PortalKeys
from app.core.exceptions.scraper import ScraperException
from app.domain.schemas import AnnouncementCreate
from app.scrapers.adapters.ilan_gov_tr import IlanGovTrScraper
from app.scrapers.adapters.resmi_gazete import ResmiGazeteScraper
from app.scrapers.base import BaseScraper
from app.scrapers.orchestrator import ScraperOrchestrator
from app.scrapers.registry import ScraperRegistry


class MockSuccessScraper(BaseScraper):
    portal_key = "mock_success"
    portal_name = "Mock Portal"

    async def scrape(self):
        return [
            AnnouncementCreate(
                source_key=self.portal_key,
                source_name=self.portal_name,
                title="Mock 10 Mühendis Alımı",
                institution="Mock Bakanlığı",
                url="https://mock.gov.tr/ilan/1",
            )
        ]


class MockFailingScraper(BaseScraper):
    portal_key = "mock_failing"
    portal_name = "Failing Portal"

    async def scrape(self):
        raise ConnectionResetError("Simüle edilmiş sunucu çökmesi")


class MockHangingScraper(BaseScraper):
    portal_key = "mock_hanging"
    portal_name = "Hanging Portal"

    async def scrape(self):
        await asyncio.sleep(3600)


@pytest.fixture
def mock_scrapers():
    for cls in (MockSuccessScraper, MockFailingScraper, MockHangingScraper):
        ScraperRegistry.register(cls)
    yield
    for key in ("mock_success", "mock_failing", "mock_hanging"):
        ScraperRegistry._registry.pop(key, None)


def test_all_portals_registered():
    keys = ScraperRegistry.get_registered_keys()
    for portal in PortalKeys:
        assert portal.value in keys
        assert isinstance(ScraperRegistry.get(portal.value), BaseScraper)


def test_tls_verification_is_on_by_default():
    assert all(s.verify_ssl is True for s in ScraperRegistry.get_all())


async def test_orchestrator_isolates_failures(mock_scrapers):
    orchestrator = ScraperOrchestrator()

    _, items, status = await orchestrator.run_single("mock_success")
    assert status.status == "success" and len(items) == 1

    _, items, status = await orchestrator.run_single("mock_failing")
    assert status.status == "error" and items == []
    assert "Simüle edilmiş sunucu çökmesi" in status.error_message


async def test_orchestrator_times_out_hanging_scraper(mock_scrapers, monkeypatch):
    from app.core.constants import settings as constants

    monkeypatch.setattr(constants.ScraperLimits, "SCRAPER_JOB_TIMEOUT_SECONDS", 0.05)
    _, items, status = await ScraperOrchestrator().run_single("mock_hanging")
    assert status.status == "error" and items == []
    assert status.error_message  # boş zaman aşımı mesajı yerine sınıf adı döner


def test_resmi_gazete_link_filter_excludes_navigation_links():
    rx = ResmiGazeteScraper.ANNOUNCEMENT_LINK_RE
    assert rx.search("20261010-4-12.pdf")
    assert rx.search("/ilanlar/eskiilanlar/2026/10/20261010-4-1.PDF")
    assert not rx.search("../index.htm")
    assert not rx.search("20261010-4.htm")


async def test_ilan_gov_raises_when_browser_missing(monkeypatch):
    monkeypatch.setattr(settings, "BROWSER_EXECUTABLE_PATH", "/yok/boyle/bir/tarayici")
    with pytest.raises(ScraperException) as exc:
        await IlanGovTrScraper().scrape()
    assert exc.value.error_code == "SCRAPER_BROWSER_NOT_FOUND"


@pytest.mark.live
async def test_live_kariyer_kapisi():
    items = await ScraperRegistry.get(PortalKeys.KARIYER_KAPISI).scrape()
    assert items and items[0].url.startswith("http")
