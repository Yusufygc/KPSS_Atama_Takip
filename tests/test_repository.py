"""Domain modelleri ve asenkron SQLite repository testleri (geçici veritabanı)."""

import pytest

from app.domain.models import Announcement, PriorityLevel, ScoreType
from app.domain.schemas import AnnouncementFilterParams, AnnouncementResponse
from app.infrastructure.database.repository import AnnouncementRepository


def make(title, scores, **kw):
    priority = PriorityLevel.PRIORITY_P3 if ScoreType.P3 in scores else PriorityLevel.NORMAL
    return Announcement(
        source_key=kw.pop("source_key", "kariyer_kapisi"),
        source_name="Kaynak",
        title=title,
        institution=kw.pop("institution", "Kurum"),
        url=kw.pop("url", f"https://example.test/{title}"),
        matched_score_types=scores,
        priority_level=priority,
        **kw,
    )


@pytest.fixture
async def repo(db_ready):
    return AnnouncementRepository()


async def test_hash_and_dedup(repo):
    item = make("Bilişim Personeli", [ScoreType.P3], deadline_date="2026-10-25")
    assert len(item.hash_id) == 64
    assert await repo.save(item) > 0
    assert await repo.save(item) is None, "Mükerrer kayıt eklenmemeli"


async def test_save_many_counts_only_new(repo):
    a, b, c = make("A", [ScoreType.P3]), make("B", [ScoreType.P1]), make("C", [ScoreType.GENERAL])
    await repo.save(a)
    assert await repo.save_many([a, b, c]) == 2
    assert await repo.save_many([]) == 0


async def test_filters_and_pagination(repo):
    await repo.save_many([make("Zabıta Memuru", [ScoreType.P3]), make("Uzman Yardımcısı", [ScoreType.P1, ScoreType.P2])])

    items, total = await repo.list_announcements(AnnouncementFilterParams(only_p3=True))
    assert total == 1 and items[0].has_p3_score

    items, total = await repo.list_announcements(AnnouncementFilterParams(search_text="Zabıta"))
    assert total == 1 and "Zabıta" in items[0].title

    _, total = await repo.list_announcements(AnnouncementFilterParams(limit=1, offset=1))
    assert total == 2


async def test_search_treats_like_wildcards_literally(repo):
    await repo.save_many([make("Yüzde 50% indirim", [ScoreType.GENERAL]), make("Başka ilan", [ScoreType.GENERAL])])

    for wildcard in ("%", "_", "50%"):
        items, total = await repo.list_announcements(AnnouncementFilterParams(search_text=wildcard))
        assert all(wildcard in i.title for i in items), wildcard
    _, total = await repo.list_announcements(AnnouncementFilterParams(search_text="%"))
    assert total == 1, "'%' tüm kayıtları eşleştirmemeli"


async def test_notification_state(repo):
    await repo.save_many([make("A", [ScoreType.P3]), make("B", [ScoreType.P3]), make("C", [ScoreType.P3])])
    unnotified = await repo.get_unnotified_announcements(limit=10)
    assert len(unnotified) == 3
    assert await repo.mark_as_notified([unnotified[0].id, unnotified[1].id]) == 2
    assert len(await repo.get_unnotified_announcements(limit=10)) == 1


async def test_stats_general_count_is_not_distorted_by_overlap(repo):
    await repo.save_many(
        [
            make("P3 ve P1", [ScoreType.P3, ScoreType.P1]),  # iki kategoride de sayılır
            make("Sadece P3", [ScoreType.P3]),
            make("Genel 1", [ScoreType.GENERAL]),
            make("Genel 2", [ScoreType.GENERAL]),
        ]
    )
    stats = await repo.get_system_stats()
    assert stats.total_announcements == 4
    assert stats.p3_count == 2
    assert stats.p1_p2_count == 1
    assert stats.general_count == 2


async def test_dto_conversion(repo):
    item = make("Zabıta", [ScoreType.P3])
    await repo.save(item)
    stored, _ = await repo.list_announcements(AnnouncementFilterParams())
    dto = AnnouncementResponse.from_entity(stored[0])
    assert dto.priority_icon == "🎓"
    assert dto.document_url == f"/api/announcements/{stored[0].id}/document"


async def test_init_database_fixes_legacy_kariyer_kapisi_urls(db_ready):
    from app.infrastructure.database.connection import init_database

    repo = AnnouncementRepository()
    bad = "https://kariyerkapisi.gov.tr/isealim/IlanDetay?i=g1"
    good = "https://kariyerkapisi.gov.tr/IlanDetay?i=g1"
    legacy = make("Eski", [ScoreType.P3], url=bad)
    legacy_dup = make("Cift", [ScoreType.P3], url=bad)
    already_fixed = make("Cift", [ScoreType.P3], url=good)  # düzeltilmiş hali zaten kayıtlı
    await repo.save_many([legacy, legacy_dup, already_fixed])

    await init_database()

    items, total = await repo.list_announcements(AnnouncementFilterParams())
    assert total == 2, "Mükerrer olacak eski satır silinmeli"
    assert all("/isealim/" not in i.url for i in items)

    # Düzeltilen ilan bir sonraki taramada yeni sanılmamalı
    assert await repo.save(make("Eski", [ScoreType.P3], url=good)) is None
