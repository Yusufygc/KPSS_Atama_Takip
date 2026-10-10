"""Uçtan Uca (E2E) Sistem ve API Entegrasyon Test Paketi."""

import asyncio
import sys
from pathlib import Path
import httpx

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.scoring.strategy import KPSSScoreMatcher
from app.domain.models import PriorityLevel, ScoreType
from app.infrastructure.database.connection import init_database
from app.main import app


async def run_full_system_tests():
    print("=" * 60)
    print("RUNNING END-TO-END SYSTEM & API TEST SUITE")
    print("=" * 60)

    # 1. Test KPSS Score Matcher Strategy
    print("1. Testing KPSSScoreMatcher Strategy...")
    # Test P3 match
    p3_scores, p3_prio = KPSSScoreMatcher.match(
        title="Isparta Belediyesi 5 Zabıta Memuru ve 2 Mühendis Alımı",
        institution="Isparta Belediyesi",
    )
    assert ScoreType.P3 in p3_scores
    assert p3_prio == PriorityLevel.PRIORITY_P3
    print(f"   [OK] P3 Match: {p3_scores} | Priority: {p3_prio.name}")

    # Test Career P1/P2 match
    career_scores, career_prio = KPSSScoreMatcher.match(
        title="Cumhurbaşkanlığı İletişim Başkanlığı 15 Uzman Yardımcısı Alacak",
        institution="İletişim Başkanlığı",
    )
    assert ScoreType.P1 in career_scores or ScoreType.P2 in career_scores
    assert career_prio == PriorityLevel.CAREER_P1_P2
    print(f"   [OK] Career Match: {career_scores} | Priority: {career_prio.name}")

    # Test Explicit KPSSP3 regex
    exp_scores, exp_prio = KPSSScoreMatcher.match(
        title="Sözleşmeli Personel Alım İlanı",
        raw_content="Adayların 2026 KPSSP3 puan türünden en az 70 almış olması gerekmektedir.",
    )
    assert ScoreType.P3 in exp_scores
    assert exp_prio == PriorityLevel.PRIORITY_P3
    print(f"   [OK] Explicit Regex Match: {exp_scores} | Priority: {exp_prio.name}")

    # 2. Test FastAPI Endpoints via Async Client
    print("2. Testing FastAPI REST Endpoints...")
    await init_database()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test /health
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"
        print("   [OK] GET /health returned 200 OK.")

        # Test /api/settings
        settings_resp = await client.get("/api/settings")
        assert settings_resp.status_code == 200
        s_data = settings_resp.json()
        assert "scraper_interval_minutes" in s_data
        print(f"   [OK] GET /api/settings: Interval={s_data['scraper_interval_minutes']}m")

        # Test /api/scrapers/status
        scrapers_resp = await client.get("/api/scrapers/status")
        assert scrapers_resp.status_code == 200
        scrapers_list = scrapers_resp.json()
        assert len(scrapers_list) == 6
        print(f"   [OK] GET /api/scrapers/status: {len(scrapers_list)} portals tracked.")

        # Test /api/announcements/stats
        stats_resp = await client.get("/api/announcements/stats")
        assert stats_resp.status_code == 200
        stats_data = stats_resp.json()
        print(f"   [OK] GET /api/announcements/stats: Total={stats_data['total_announcements']}")

        # Test /api/announcements listing
        ann_resp = await client.get("/api/announcements?limit=10")
        assert ann_resp.status_code == 200
        ann_data = ann_resp.json()
        assert "items" in ann_data
        assert "total" in ann_data
        print(f"   [OK] GET /api/announcements: {len(ann_data['items'])} items returned.")

    print("=" * 60)
    print("ALL END-TO-END TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_full_system_tests())
