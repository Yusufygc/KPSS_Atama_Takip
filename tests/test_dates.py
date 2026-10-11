"""Son başvuru tarihi normalizasyonu ve süresi dolan ilan davranışları."""

from datetime import date, timedelta

import pytest

from app.core.dates import day_of_timestamp, parse_deadline, parse_deadline_iso, today_in_turkey
from app.domain.models import Announcement, ScoreType
from app.domain.schemas import AnnouncementFilterParams, AnnouncementResponse
from app.infrastructure.database.repository import AnnouncementRepository

REF = date(2026, 10, 12)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("13.10.2026", "2026-10-13"),  # İŞKUR
        ("16.10.2026 23:59", "2026-10-16"),
        ("2026-10-22T23:59:00", "2026-10-22"),  # Kariyer Kapısı
        ("09 Ekim 2026", "2026-10-09"),  # Yerel Yönetimler
        ("9 ekim 2026", "2026-10-09"),
        ("12 Ekim - 26 Ekim", "2026-10-26"),  # SBB aralığı: son tarih alınır
        ("7 Ekim - 22 Ekim", "2026-10-22"),
        ("19 Ekim - 2 Kasım", "2026-11-02"),
        ("1 Ağustos 2026", "2026-08-01"),
        ("15 ŞUBAT 2027", "2027-02-15"),
        ("15 Subat 2027", "2027-02-15"),  # ASCII yazım
        ("Son Başvuru: 5 Kasım", "2026-11-05"),
    ],
)
def test_parse_deadline_formats(raw, expected):
    assert parse_deadline_iso(raw, REF) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "yakında", "31 Şubat 2026", "32.13.2026", "Ekim"])
def test_unparseable_values_return_none(raw):
    assert parse_deadline(raw, REF) is None


def test_yearless_range_crossing_new_year_uses_next_year():
    assert parse_deadline_iso("28 Aralık - 5 Ocak", date(2026, 12, 30)) == "2027-01-05"


def test_yearless_past_date_stays_in_current_year_so_it_reads_as_expired():
    # Referans 20 Kasım, "26 Ekim" bitmiş bir ilan: gelecek yıla atılmamalı
    assert parse_deadline_iso("12 Ekim - 26 Ekim", date(2026, 11, 20)) == "2026-10-26"


def test_day_of_timestamp():
    assert day_of_timestamp("2026-10-10T19:34:47.164383+00:00") == date(2026, 10, 10)
    assert day_of_timestamp("bozuk") is None and day_of_timestamp(None) is None


def test_announcement_derives_deadline_on_from_creation_day():
    item = Announcement(
        source_key="s", source_name="S", title="T", institution="I", url="https://a.test",
        deadline_date="12 Ekim - 26 Ekim", created_at="2026-10-12T08:00:00+00:00",
    )
    assert item.deadline_on == "2026-10-26"


def make(title, deadline_date=None, deadline_on=None, **kw):
    return Announcement(
        source_key="s", source_name="S", title=title, institution="I", url=f"https://a.test/{title}",
        matched_score_types=[ScoreType.P3], deadline_date=deadline_date, deadline_on=deadline_on, **kw,
    )


async def test_only_active_hides_expired_but_keeps_unknown_dates(db_ready):
    repo = AnnouncementRepository()
    today = today_in_turkey()
    await repo.save_many(
        [
            make("gecmis", deadline_date="x", deadline_on=(today - timedelta(days=1)).isoformat()),
            make("bugun", deadline_date="x", deadline_on=today.isoformat()),
            make("gelecek", deadline_date="x", deadline_on=(today + timedelta(days=5)).isoformat()),
            make("tarihsiz"),
        ]
    )

    items, total = await repo.list_announcements(AnnouncementFilterParams(only_active=True))
    assert sorted(i.title for i in items) == ["bugun", "gelecek", "tarihsiz"] and total == 3
    _, total_all = await repo.list_announcements(AnnouncementFilterParams())
    assert total_all == 4

    assert (await repo.get_system_stats()).total_announcements == 4
    assert (await repo.get_system_stats(only_active=True)).total_announcements == 3
    cities_active = await repo.get_distinct_cities(only_active=True)
    assert cities_active == [] or sum(c["count"] for c in cities_active) <= 3


async def test_response_exposes_deadline_on_and_is_expired():
    past = (today_in_turkey() - timedelta(days=2)).isoformat()
    future = (today_in_turkey() + timedelta(days=2)).isoformat()
    expired = AnnouncementResponse.from_entity(make("a", deadline_date="x", deadline_on=past, id=1))
    active = AnnouncementResponse.from_entity(make("b", deadline_date="x", deadline_on=future, id=2))
    unknown = AnnouncementResponse.from_entity(make("c", id=3))
    assert expired.is_expired and expired.deadline_on == past
    assert not active.is_expired and not unknown.is_expired


async def test_init_database_backfills_deadline_on_using_creation_day(db_ready):
    import sqlite3

    from app.config import settings
    from app.infrastructure.database.connection import init_database

    repo = AnnouncementRepository()
    await repo.save(make("eski", deadline_date="12 Ekim - 26 Ekim", created_at="2026-10-12T08:00:00+00:00"))
    conn = sqlite3.connect(settings.resolved_database_path)
    conn.execute("UPDATE announcements SET deadline_on = NULL")
    conn.commit()
    conn.close()

    await init_database()

    items, _ = await repo.list_announcements(AnnouncementFilterParams())
    assert items[0].deadline_on == "2026-10-26"


async def test_api_only_active_param_and_fields(client):
    from app.api import dependencies

    today = today_in_turkey()
    await dependencies._repository.save_many(
        [
            make("gecmis", deadline_date="x", deadline_on=(today - timedelta(days=3)).isoformat()),
            make("gelecek", deadline_date="x", deadline_on=(today + timedelta(days=3)).isoformat()),
        ]
    )
    everything = (await client.get("/api/announcements")).json()
    active = (await client.get("/api/announcements?only_active=true")).json()
    assert everything["total"] == 2 and active["total"] == 1
    assert active["items"][0]["is_expired"] is False and active["items"][0]["deadline_on"]
    stats = (await client.get("/api/announcements/stats?only_active=true")).json()
    assert stats["total_announcements"] == 1


async def test_expired_items_are_listed_after_active_ones_regardless_of_priority(db_ready):
    repo = AnnouncementRepository()
    today = today_in_turkey()
    await repo.save_many(
        [
            make("gecmis-p3", deadline_date="x", deadline_on=(today - timedelta(days=1)).isoformat()),
            make("aktif", deadline_date="x", deadline_on=(today + timedelta(days=1)).isoformat()),
            make("tarihsiz"),
        ]
    )
    items, _ = await repo.list_announcements(AnnouncementFilterParams())
    assert [i.title for i in items][-1] == "gecmis-p3"

    # Filtre parametreleriyle birlikte de sıralama parametreleri doğru bağlanmalı
    items, total = await repo.list_announcements(AnnouncementFilterParams(search_text="aktif", only_active=True, limit=1))
    assert total == 1 and items[0].title == "aktif"
