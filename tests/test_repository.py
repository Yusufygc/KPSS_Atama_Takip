"""Aşama 2: Domain Modelleri ve Asenkron SQLite Repository Testi."""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.domain.models import Announcement, PriorityLevel, ScoreType
from app.domain.schemas import AnnouncementFilterParams, AnnouncementResponse
from app.infrastructure.database.connection import init_database
from app.infrastructure.database.repository import AnnouncementRepository


async def run_repository_tests():
    print("=" * 50)
    print("RUNNING PHASE 2 REPOSITORY TEST SUITE")
    print("=" * 50)

    test_db_path = BASE_DIR / "data" / "test_kpss.db"
    if test_db_path.exists():
        test_db_path.unlink()

    # 1. Init Database
    print("1. Initializing Test Database...")
    await init_database(test_db_path)
    repo = AnnouncementRepository(test_db_path)
    print("   [OK] Database schema initialized.")

    # 2. Testing Entity Creation and Hash Calculation
    print("2. Testing Entity Hash Generation...")
    ann1 = Announcement(
        source_key="kariyer_kapisi",
        source_name="Kariyer Kapısı (CBİKO)",
        title="Bilişim Personeli Alımı",
        institution="Çalışma ve Sosyal Güvenlik Bakanlığı",
        url="https://kariyerkapisi.gov.tr/ilan/1",
        deadline_date="2026-10-25",
        matched_score_types=[ScoreType.P3],
        priority_level=PriorityLevel.PRIORITY_P3,
    )
    assert len(ann1.hash_id) == 64, "SHA-256 hash length must be 64 characters"
    assert ann1.has_p3_score is True
    assert ann1.has_career_score is False
    print(f"   [OK] Hash generated: {ann1.hash_id[:16]}...")

    # 3. Testing Save and Deduplication
    print("3. Testing Save and Deduplication (Idempotency)...")
    id1 = await repo.save(ann1)
    assert id1 is not None and id1 > 0
    print(f"   [OK] First announcement inserted with ID: {id1}")

    # Duplicate save attempt must return None
    dup_id = await repo.save(ann1)
    assert dup_id is None, "Duplicate announcement must return None and NOT be inserted"
    print("   [OK] Duplicate insertion successfully prevented.")

    # 4. Testing Batch Save (save_many)
    print("4. Testing Batch Save (save_many)...")
    ann2 = Announcement(
        source_key="kamu_ilan_sbb",
        source_name="Kamu İlan (SBB)",
        title="860 Gelir Uzman Yardımcısı Alımı",
        institution="Gelir İdaresi Başkanlığı",
        url="https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=123",
        deadline_date="2026-10-22",
        matched_score_types=[ScoreType.P1, ScoreType.P2],
        priority_level=PriorityLevel.CAREER_P1_P2,
    )
    ann3 = Announcement(
        source_key="yerel_yonetimler",
        source_name="Yerel Yönetimler GM",
        title="Zabıta Memuru Alım İlanı",
        institution="Isparta Sarıidris Belediyesi",
        url="https://yerelyonetimler.csb.gov.tr/duyuru/1",
        deadline_date="2026-10-30",
        matched_score_types=[ScoreType.P3],
        priority_level=PriorityLevel.PRIORITY_P3,
    )
    # ann1 is already in DB, so only ann2 and ann3 should be inserted
    inserted_count = await repo.save_many([ann1, ann2, ann3])
    assert inserted_count == 2, f"Expected 2 newly inserted, got {inserted_count}"
    print(f"   [OK] Batch saved. Newly added: {inserted_count}")

    # 5. Testing Filtering and Querying
    print("5. Testing Filtering and Pagination...")
    # Filter by P3 only
    p3_params = AnnouncementFilterParams(only_p3=True)
    p3_items, p3_total = await repo.list_announcements(p3_params)
    assert p3_total == 2, f"Expected 2 P3 items, got {p3_total}"
    assert all(i.has_p3_score for i in p3_items)
    print(f"   [OK] P3 filter returned {p3_total} items.")

    # Filter by search text
    search_params = AnnouncementFilterParams(search_text="Zabıta")
    search_items, search_total = await repo.list_announcements(search_params)
    assert search_total == 1
    assert "Zabıta" in search_items[0].title
    print(f"   [OK] Search filter returned: {search_items[0].title}")

    # 6. Testing Unnotified and Mark as Notified
    print("6. Testing Notification State Management...")
    unnotified = await repo.get_unnotified_announcements(limit=10)
    assert len(unnotified) == 3, f"Expected 3 unnotified, got {len(unnotified)}"
    
    # Mark first 2 as notified
    marked_count = await repo.mark_as_notified([unnotified[0].id, unnotified[1].id])
    assert marked_count == 2
    
    # Remaining unnotified should be 1
    remaining = await repo.get_unnotified_announcements(limit=10)
    assert len(remaining) == 1
    print("   [OK] Notification status updated correctly.")

    # 7. Testing System Stats
    print("7. Testing System Stats Calculation...")
    stats = await repo.get_system_stats()
    assert stats.total_announcements == 3
    assert stats.total_unnotified == 1
    assert stats.p3_count == 2
    assert stats.p1_p2_count == 1
    print(f"   [OK] Stats: Total={stats.total_announcements}, P3={stats.p3_count}, P1/P2={stats.p1_p2_count}")

    # 8. Testing DTO Conversion
    print("8. Testing AnnouncementResponse DTO...")
    dto = AnnouncementResponse.from_entity(p3_items[0])
    assert dto.source_icon != ""
    assert dto.priority_icon == "🎓"
    print(f"   [OK] DTO generated with icon: {dto.priority_icon} {dto.source_icon}")

    # Cleanup test db
    if test_db_path.exists():
        test_db_path.unlink()

    print("=" * 50)
    print("ALL PHASE 2 REPOSITORY TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_repository_tests())
