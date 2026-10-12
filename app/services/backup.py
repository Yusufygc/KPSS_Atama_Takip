"""KPSS Atama Takip - SQLite Veritabanı Yedekleme (çalışırken tutarlı anlık görüntü)."""

import asyncio
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import List

from app.config import settings
from app.core.dates import TURKEY_TZ
from app.core.logging import get_logger

logger = get_logger("services.backup")

BACKUP_PREFIX = "kpss_backup_"


def _backup_blocking(source: Path, target: Path) -> None:
    """SQLite online backup API: uygulama çalışırken (WAL açıkken) tutarlı kopya alır.

    Dosya kopyalamanın aksine yazma sırasında bozuk/yarım kopya üretmez.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_suffix(".tmp")
    # sqlite3.connect() bağlam yöneticisi bağlantıyı KAPATMAZ (yalnızca commit eder); Windows'ta açık kalan
    # dosya tutamacı yeniden adlandırmayı engeller. closing() bağlantıları kesin olarak kapatır.
    with closing(sqlite3.connect(str(source))) as src, closing(sqlite3.connect(str(temp_target))) as dst:
        src.backup(dst)
    temp_target.replace(target)  # yarım dosya asla "yedek" adını almaz


def _prune(backup_dir: Path, keep: int) -> List[Path]:
    """En yeni `keep` yedeği tutar, eskilerini siler; silinenleri döner."""
    backups = sorted(backup_dir.glob(f"{BACKUP_PREFIX}*.db"), key=lambda p: p.name, reverse=True)
    removed = backups[max(keep, 1):]
    for path in removed:
        path.unlink(missing_ok=True)
    return removed


async def backup_database() -> Path:
    """Veritabanının zaman damgalı yedeğini alır ve eski yedekleri temizler. Yedek dosya yolunu döner."""
    source = settings.resolved_database_path
    backup_dir = settings.BASE_DIR / settings.DB_BACKUP_DIR
    stamp = datetime.now(TURKEY_TZ).strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"{BACKUP_PREFIX}{stamp}.db"

    await asyncio.to_thread(_backup_blocking, source, target)
    removed = await asyncio.to_thread(_prune, backup_dir, settings.DB_BACKUP_KEEP)

    size_kb = target.stat().st_size // 1024
    logger.info(f"Veritabanı yedeği alındı: {target.name} ({size_kb} KB), {len(removed)} eski yedek silindi.")
    return target
