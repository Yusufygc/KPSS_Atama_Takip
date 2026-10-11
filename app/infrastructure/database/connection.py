"""KPSS Atama Takip - Asenkron SQLite Bağlantı ve Şema Yönetimi."""

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiosqlite

from app.config import settings
from app.core.exceptions.database import DatabaseException, QueryExecutionException
from app.core.logging import get_logger
from app.core.scoring.strategy import KPSSScoreMatcher
from app.domain.models import build_search_text, compute_announcement_hash

logger = get_logger("database.connection")

# Puanlama kuralları değiştiğinde artırılır; mevcut kayıtlar bir kez yeniden puanlanır (PRAGMA user_version)
SCORING_VERSION = 2

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
    created_at TEXT NOT NULL,
    search_text TEXT               -- Türkçe katlanmış arama metni (başlık, kurum, unvan)
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
    Yalnızca bağlantı kurulumu "bağlantı hatası" sayılır; çağıranın gövdesindeki hatalar
    yanıltıcı biçimde sarmalanmaz. SQL hataları QueryExecutionException olur.
    """
    db_path = custom_path or settings.resolved_database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = await aiosqlite.connect(str(db_path))
        try:
            conn.row_factory = aiosqlite.Row
            # Performans ve eşzamanlılık pragma ayarları
            await conn.execute("PRAGMA journal_mode = WAL;")
            await conn.execute("PRAGMA synchronous = NORMAL;")
            await conn.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            await conn.close()
            raise
    except (sqlite3.Error, OSError) as e:
        logger.error(f"Veritabanı bağlantı hatası ({db_path}): {e}")
        raise DatabaseException(f"Veritabanı bağlantısı kurulamadı: {e}") from e

    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Veritabanı sorgu hatası ({db_path}): {e}")
        raise QueryExecutionException(query="", original_error=str(e)) from e
    finally:
        await conn.close()


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


async def _backfill_search_text(conn: aiosqlite.Connection) -> None:
    """search_text değeri boş olan (eski) kayıtlar için katlanmış arama metnini üretir."""
    async with conn.execute(
        "SELECT id, title, institution, position FROM announcements WHERE search_text IS NULL;"
    ) as cursor:
        rows = await cursor.fetchall()
    for row in rows:
        await conn.execute(
            "UPDATE announcements SET search_text = ? WHERE id = ?;",
            (build_search_text(row["title"], row["institution"], row["position"]), row["id"]),
        )
    if rows:
        logger.info(f"{len(rows)} kaydın arama metni oluşturuldu.")


async def _normalize_field_tags_encoding(conn: aiosqlite.Connection) -> None:
    """ASCII-kaçışlı (\u00fc) field_tags değerlerini gerçek Türkçe karakterlerle yeniden yazar.

    Etiket filtresi ham metin üzerinde LIKE ile çalıştığından kaçışlı kayıtlar eşleşmiyordu.
    """
    backslash = chr(92)
    async with conn.execute(
        "SELECT id, field_tags FROM announcements WHERE field_tags LIKE ?;", (f"%{backslash}u%",)
    ) as cursor:
        rows = await cursor.fetchall()
    for row in rows:
        try:
            tags = json.loads(row["field_tags"])
        except ValueError:
            continue
        await conn.execute(
            "UPDATE announcements SET field_tags = ? WHERE id = ?;",
            (json.dumps(tags, ensure_ascii=False), row["id"]),
        )
    if rows:
        logger.info(f"{len(rows)} kaydın etiket kodlaması düzeltildi.")


async def _rescore_if_outdated(conn: aiosqlite.Connection) -> None:
    """Puanlama sürümü eskiyse tüm kayıtların KPSS puan türü ve önceliğini güncel kurallarla yeniler."""
    async with conn.execute("PRAGMA user_version;") as cursor:
        current_version = (await cursor.fetchone())[0]
    if current_version >= SCORING_VERSION:
        return

    async with conn.execute(
        "SELECT id, title, institution, raw_content, matched_score_types, priority_level FROM announcements;"
    ) as cursor:
        rows = await cursor.fetchall()

    changed = 0
    for row in rows:
        scores, priority = KPSSScoreMatcher.match(
            title=row["title"], institution=row["institution"], raw_content=row["raw_content"] or ""
        )
        scores_json = json.dumps([s.value for s in scores])
        if scores_json != row["matched_score_types"] or priority.value != row["priority_level"]:
            await conn.execute(
                "UPDATE announcements SET matched_score_types = ?, priority_level = ? WHERE id = ?;",
                (scores_json, priority.value, row["id"]),
            )
            changed += 1
    await conn.execute(f"PRAGMA user_version = {int(SCORING_VERSION)};")
    logger.info(f"Puanlama sürümü {SCORING_VERSION}: {changed}/{len(rows)} kayıt yeniden puanlandı.")


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
            if "search_text" not in existing_cols:
                await conn.execute("ALTER TABLE announcements ADD COLUMN search_text TEXT;")

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_announcements_it ON announcements(is_it_field);")
        await _fix_legacy_kariyer_kapisi_urls(conn)
        await _backfill_search_text(conn)
        await _normalize_field_tags_encoding(conn)
        await _rescore_if_outdated(conn)
        await conn.commit()
        logger.info("Veritabanı şeması ve indeksleri başarıyla doğrulandı.")
