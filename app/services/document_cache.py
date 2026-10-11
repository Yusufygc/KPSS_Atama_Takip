"""KPSS Atama Takip - İlan Belgesi (PDF) Önbellek Yönetimi.

Önbellek dosyaları ilanın kalıcı `hash_id` değerine göre adlandırılır. Önceden `sbb_{id}.pdf`
biçimindeki ID tabanlı adlar, veritabanı sıfırlanıp ID'ler yeniden kullanıldığında yanlış ilana
ait PDF'in sunulmasına yol açabiliyordu; ayrıca önbellek hiç temizlenmiyordu.
"""

import re
import time
from pathlib import Path
from typing import Dict

from app.config import settings
from app.core.constants.settings import ScraperLimits
from app.core.logging import get_logger
from app.infrastructure.database.repository import AnnouncementRepository

logger = get_logger("services.document_cache")

_LEGACY_NAME_RE = re.compile(r"^sbb_(\d+)\.pdf$")
_HASH_NAME_RE = re.compile(r"^sbb_([0-9a-f]{32})\.pdf$")
_HASH_PREFIX_LENGTH = 32
_SECONDS_PER_DAY = 86400


def cache_path_for(hash_id: str) -> Path:
    """Verilen ilan kimliği (hash_id) için önbellek dosya yolunu döner."""
    return settings.DOCUMENTS_DIR / f"sbb_{hash_id[:_HASH_PREFIX_LENGTH]}.pdf"


async def migrate_and_cleanup(repository: AnnouncementRepository, source_key: str = "kamu_ilan_sbb") -> Dict[str, int]:
    """Eski ID tabanlı dosyaları hash adına taşır; yetim ve süresi geçmiş dosyaları siler.

    Döner: {"migrated": n, "removed": n} sayıları.
    """
    directory = settings.DOCUMENTS_DIR
    stats = {"migrated": 0, "removed": 0}
    if not directory.exists():
        return stats

    identifiers = await repository.list_identifiers(source_key)  # [(id, hash_id)]
    hash_by_id = {item_id: hash_id for item_id, hash_id in identifiers}
    valid_prefixes = {hash_id[:_HASH_PREFIX_LENGTH] for hash_id in hash_by_id.values()}
    max_age_seconds = ScraperLimits.DOCUMENT_CACHE_MAX_AGE_DAYS * _SECONDS_PER_DAY
    now = time.time()

    for path in directory.glob("sbb_*.pdf"):
        legacy = _LEGACY_NAME_RE.match(path.name)
        if legacy:
            hash_id = hash_by_id.get(int(legacy.group(1)))
            target = cache_path_for(hash_id) if hash_id else None
            if target is not None and not target.exists():
                path.rename(target)
                stats["migrated"] += 1
            else:
                path.unlink(missing_ok=True)
                stats["removed"] += 1
            continue

        hashed = _HASH_NAME_RE.match(path.name)
        if hashed is None:
            continue
        orphaned = hashed.group(1) not in valid_prefixes
        expired = now - path.stat().st_mtime > max_age_seconds
        if orphaned or expired:
            path.unlink(missing_ok=True)
            stats["removed"] += 1

    if stats["migrated"] or stats["removed"]:
        logger.info(f"PDF önbelleği: {stats['migrated']} dosya taşındı, {stats['removed']} dosya silindi.")
    return stats
