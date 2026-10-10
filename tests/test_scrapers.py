"""Aşama 3: Kazıyıcı Motoru (Scrapers, Registry, Orchestrator) Testi."""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.constants.strings import PortalKeys
from app.domain.schemas import AnnouncementCreate
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
                deadline_date="2026-11-01",
            )
        ]


class MockFailingScraper(BaseScraper):
    portal_key = "mock_failing"
    portal_name = "Failing Portal"

    async def scrape(self):
        raise ConnectionResetError("Simüle edilmiş sunucu çökmesi")


async def run_scraper_tests():
    print("=" * 50)
    print("RUNNING PHASE 3 SCRAPERS TEST SUITE")
    print("=" * 50)

    # 1. Test Registry Registration
    print("1. Testing ScraperRegistry Registration...")
    registered_keys = ScraperRegistry.get_registered_keys()
    print(f"   Registered keys: {registered_keys}")
    
    expected_portals = [
        PortalKeys.KARIYER_KAPISI,
        PortalKeys.RESMI_GAZETE,
        PortalKeys.KAMU_ILAN_SBB,
        PortalKeys.YEREL_YONETIMLER,
        PortalKeys.ISKUR,
        PortalKeys.ILAN_GOV_TR,
    ]
    for p in expected_portals:
        assert p in registered_keys, f"Portal {p} not registered in ScraperRegistry!"
        scraper = ScraperRegistry.get(p)
        assert isinstance(scraper, BaseScraper)
    print("   [OK] All 6 portal adapters successfully registered.")

    # 2. Test Live Kariyer Kapısı Adapter
    print("2. Testing Live Kariyer Kapısı Scraper Adapter...")
    kk_scraper = ScraperRegistry.get(PortalKeys.KARIYER_KAPISI)
    kk_items = await kk_scraper.scrape()
    assert len(kk_items) > 0, "Kariyer Kapısı should return active announcements!"
    first_item = kk_items[0]
    assert first_item.title != ""
    assert first_item.institution != ""
    assert first_item.url.startswith("http")
    print(f"   [OK] Kariyer Kapısı fetched {len(kk_items)} items successfully.")
    print(f"        Sample: [{first_item.institution}] {first_item.title[:60]}...")

    # 3. Test Orchestrator Fault Tolerance & Isolation
    print("3. Testing Orchestrator Fault Isolation with Mock Scrapers...")
    ScraperRegistry.register(MockSuccessScraper)
    ScraperRegistry.register(MockFailingScraper)

    orchestrator = ScraperOrchestrator()
    
    # Run success scraper
    key, items, status = await orchestrator.run_single("mock_success")
    assert status.status == "success"
    assert len(items) == 1
    assert status.duration_ms > 0
    print(f"   [OK] Mock success handled: {items[0].title} ({status.duration_ms} ms)")

    # Run failing scraper
    f_key, f_items, f_status = await orchestrator.run_single("mock_failing")
    assert f_status.status == "error"
    assert len(f_items) == 0
    assert "Simüle edilmiş sunucu çökmesi" in (f_status.error_message or "")
    print(f"   [OK] Mock error successfully isolated without crashing: {f_status.error_message}")

    # Clean up mock registrations
    ScraperRegistry._registry.pop("mock_success", None)
    ScraperRegistry._registry.pop("mock_failing", None)

    print("=" * 50)
    print("ALL PHASE 3 SCRAPER TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_scraper_tests())
