"""KPSS Atama Takip - Asenkron SQLite Bağlantı ve Şema Yönetimi."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiosqlite

from app.config import settings
from app.core.exceptions.database import DatabaseException
from app.core.logging import get_logger
from app.domain.models import compute_announcement_hash

logger = get_logger("database.connection")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash_id TEXT UNIQUE NOT NULL,
    source_key TEXT NOT NULL,
    source_name TEXT NOT NULL,
    title TEXT NOT NULL,
    institution TEXT NOT NULL,
    position TEXT,
    city TEXT,
    url TEXT NOT NULL,
    pdf_url TEXT,
    publish_date TEXT,
    deadline_date TEXT,
    raw_content TEXT,
    matched_score_types TEXT,      -- JSON dizisi: '["P3"]'
    priority_level INTEGER DEFAULT 1,
    field_tags TEXT,               -- JSON dizisi: '["Yazılım & Web", "Siber Güvenlik"]'
    is_it_field INTEGER DEFAULT 0, -- 1: Bilgisayar/Bilişim, 0: Diğer
    is_notified INTEGER DEFAULT 0,
    notified_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_announcements_hash ON announcements(hash_id);
CREATE INDEX IF NOT EXISTS idx_announcements_source ON announcements(source_key);
CREATE INDEX IF NOT EXISTS idx_announcements_notified ON announcements(is_notified);
CREATE INDEX IF NOT EXISTS idx_announcements_priority ON announcements(priority_level);
CREATE INDEX IF NOT EXISTS idx_announcements_city ON announcements(city);
"""


@asynccontextmanager
async def get_db_connection(
    custom_path: Optional[Path] = None,
) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Asenkron SQLite bağlantısı sağlayan güvenli context manager.
    
    WAL (Write-Ahead Logging) modunu açarak eşzamanlı okuma/yazma kilitlenmelerini önler.
    """
    db_path = custom_path or settings.resolved_database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiosqlite.connect(str(db_path)) as conn:
            conn.row_factory = aiosqlite.Row
            # Performans ve eşzamanlılık pragma ayarları
            await conn.execute("PRAGMA journal_mode = WAL;")
            await conn.execute("PRAGMA synchronous = NORMAL;")
            await conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
    except Exception as e:
        logger.error(f"Veritabanı bağlantı hatası ({db_path}): {e}")
        raise DatabaseException(f"Veritabanı bağlantısı kurulamadı: {e}") from e


LEGACY_KK_URL_PREFIX = "https://kariyerkapisi.gov.tr/isealim/IlanDetay?"
FIXED_KK_URL_PREFIX = "https://kariyerkapisi.gov.tr/IlanDetay?"


async def _fix_legacy_kariyer_kapisi_urls(conn: aiosqlite.Connection) -> None:
    """Hatalı '/isealim/IlanDetay' bağlantılarını ('/IlanDetay') düzeltir.

    Eski yol portalın WAF'ında 406 ile engelleniyordu. hash_id URL'den türetildiği için
    hash de yeniden hesaplanır; aksi halde bir sonraki taramada aynı ilanlar yeni sanılıp
    mükerrer eklenir ve tekrar bildirilirdi.
    """
    async with conn.execute(
        "SELECT id, source_key, title, url, deadline_date FROM announcements WHERE url LIKE ?;",
        (f"{LEGACY_KK_URL_PREFIX}%",),
    ) as cursor:
        rows = await cursor.fetchall()

    for row in rows:
        new_url = FIXED_KK_URL_PREFIX + row["url"][len(LEGACY_KK_URL_PREFIX):]
        new_hash = compute_announcement_hash(row["source_key"], row["title"], new_url, row["deadline_date"])
        cursor = await conn.execute(
            "UPDATE OR IGNORE announcements SET url = ?, hash_id = ? WHERE id = ?;",
            (new_url, new_hash, row["id"]),
        )
        if cursor.rowcount == 0:
            # Düzeltilmiş hash zaten kayıtlı: eski mükerrer satır silinir
            await conn.execute("DELETE FROM announcements WHERE id = ?;", (row["id"],))
    if rows:
        logger.info(f"{len(rows)} Kariyer Kapısı ilan bağlantısı düzeltildi.")


async def init_database(custom_path: Optional[Path] = None) -> None:
    """Veritabanı tablolarını ve indekslerini başlatır."""
    async with get_db_connection(custom_path) as conn:
        await conn.executescript(SCHEMA_SQL)

        # Mevcut veritabanları için güvenli kolon kontrolü ve yükseltme (Migration)
        async with conn.execute("PRAGMA table_info(announcements);") as cursor:
            rows = await cursor.fetchall()
            existing_cols = {row["name"] for row in rows}
            if "field_tags" not in existing_cols:
                await conn.execute("ALTER TABLE announcements ADD COLUMN field_tags TEXT;")
            if "is_it_field" not in existing_cols:
                await conn.execute("ALTER TABLE announcements ADD COLUMN is_it_field INTEGER DEFAULT 0;")

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_announcements_it ON announcements(is_it_field);")
        await _fix_legacy_kariyer_kapisi_urls(conn)
        await conn.commit()
        logger.info("Veritabanı şeması ve indeksleri başarıyla doğrulandı.")
