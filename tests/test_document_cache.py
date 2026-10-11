"""PDF önbelleği: hash tabanlı adlandırma, eski dosyaların taşınması ve temizlik."""

import os
import time

from app.config import settings
from app.domain.models import Announcement, ScoreType
from app.infrastructure.database.repository import AnnouncementRepository
from app.services.document_cache import cache_path_for, migrate_and_cleanup


def sbb(title):
    return Announcement(
        source_key="kamu_ilan_sbb", source_name="SBB", title=title, institution="K",
        url="https://kamuilan.sbb.gov.tr/d?kod=1", matched_score_types=[ScoreType.P3], stable_url=False,
    )


async def test_legacy_id_files_are_renamed_to_hash_and_orphans_removed(db_ready):
    repo = AnnouncementRepository()
    item = sbb("İlan A")
    item_id = await repo.save(item)
    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    (settings.DOCUMENTS_DIR / f"sbb_{item_id}.pdf").write_bytes(b"%PDF-legacy")
    (settings.DOCUMENTS_DIR / "sbb_9999.pdf").write_bytes(b"%PDF-orphan")  # DB'de karşılığı olmayan ID

    stats = await migrate_and_cleanup(repo)

    assert stats == {"migrated": 1, "removed": 1}
    assert cache_path_for(item.hash_id).read_bytes() == b"%PDF-legacy"
    assert not (settings.DOCUMENTS_DIR / f"sbb_{item_id}.pdf").exists()
    assert not (settings.DOCUMENTS_DIR / "sbb_9999.pdf").exists()


async def test_hash_named_files_are_kept_unless_orphaned_or_too_old(db_ready):
    repo = AnnouncementRepository()
    keep, old = sbb("Güncel"), sbb("Eski")
    await repo.save(keep)
    await repo.save(old)
    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    cache_path_for(keep.hash_id).write_bytes(b"%PDF-keep")
    old_file = cache_path_for(old.hash_id)
    old_file.write_bytes(b"%PDF-old")
    ancient = time.time() - 200 * 86400
    os.utime(old_file, (ancient, ancient))
    orphan = settings.DOCUMENTS_DIR / ("sbb_" + "a" * 32 + ".pdf")
    orphan.write_bytes(b"%PDF-orphan")

    stats = await migrate_and_cleanup(repo)

    assert stats["removed"] == 2
    assert cache_path_for(keep.hash_id).exists()
    assert not old_file.exists() and not orphan.exists()


async def test_cache_name_does_not_depend_on_row_id_or_changing_url():
    a, b = sbb("Aynı ilan"), sbb("Aynı ilan")
    b.url = "https://kamuilan.sbb.gov.tr/d?kod=DEGISTI"
    b.hash_id = ""
    b.__post_init__()
    assert cache_path_for(a.hash_id) == cache_path_for(b.hash_id)
