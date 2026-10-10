"""KPSS Atama Takip - İlan Veritabanı Deposu (Repository Pattern)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import aiosqlite

from app.core.exceptions.database import DatabaseException
from app.core.logging import get_logger
from app.domain.models import Announcement, PriorityLevel, ScoreType
from app.domain.schemas import AnnouncementFilterParams, SystemStatsResponse
from app.infrastructure.database.connection import get_db_connection

logger = get_logger("database.repository")


class AnnouncementRepository:
    """İlanların kalıcılığını asenkron yöneten Repository sınıfı."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path

    def _row_to_entity(self, row: aiosqlite.Row) -> Announcement:
        """aiosqlite.Row nesnesini Announcement Domain Entity'sine dönüştürür."""
        # JSON puan türlerini ScoreType listesine dönüştür
        score_types_raw = row["matched_score_types"]
        score_types: List[ScoreType] = []
        if score_types_raw:
            try:
                parsed = json.loads(score_types_raw)
                score_types = [ScoreType(s) for s in parsed if s in ScoreType._value2member_map_]
            except Exception:
                pass

        return Announcement(
            id=row["id"],
            hash_id=row["hash_id"],
            source_key=row["source_key"],
            source_name=row["source_name"],
            title=row["title"],
            institution=row["institution"],
            position=row["position"],
            city=row["city"],
            url=row["url"],
            pdf_url=row["pdf_url"],
            publish_date=row["publish_date"],
            deadline_date=row["deadline_date"],
            raw_content=row["raw_content"],
            matched_score_types=score_types,
            priority_level=PriorityLevel(row["priority_level"]),
            is_notified=bool(row["is_notified"]),
            notified_at=row["notified_at"],
            created_at=row["created_at"],
        )

    async def exists_by_hash(self, hash_id: str) -> bool:
        """Verilen hash_id'ye sahip bir ilanın kayıtlı olup olmadığını kontrol eder."""
        sql = "SELECT 1 FROM announcements WHERE hash_id = ? LIMIT 1;"
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(sql, (hash_id,)) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def save(self, item: Announcement) -> Optional[int]:
        """Yeni bir ilanı kaydeder. İlan zaten varsa None döner (Mükerrer koruması)."""
        score_types_json = json.dumps([s.value for s in item.matched_score_types])
        sql = """
        INSERT OR IGNORE INTO announcements (
            hash_id, source_key, source_name, title, institution,
            position, city, url, pdf_url, publish_date, deadline_date,
            raw_content, matched_score_types, priority_level,
            is_notified, notified_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        async with get_db_connection(self.db_path) as conn:
            cursor = await conn.execute(
                sql,
                (
                    item.hash_id,
                    item.source_key,
                    item.source_name,
                    item.title,
                    item.institution,
                    item.position,
                    item.city,
                    item.url,
                    item.pdf_url,
                    item.publish_date,
                    item.deadline_date,
                    item.raw_content,
                    score_types_json,
                    item.priority_level.value,
                    1 if item.is_notified else 0,
                    item.notified_at,
                    item.created_at,
                ),
            )
            await conn.commit()
            if cursor.rowcount > 0:
                item.id = cursor.lastrowid
                return cursor.lastrowid
            return None

    async def save_many(self, items: List[Announcement]) -> int:
        """Toplu ilan kaydeder. Eklenen yeni kayıt sayısını döner."""
        if not items:
            return 0

        inserted_count = 0
        async with get_db_connection(self.db_path) as conn:
            for item in items:
                score_types_json = json.dumps([s.value for s in item.matched_score_types])
                sql = """
                INSERT OR IGNORE INTO announcements (
                    hash_id, source_key, source_name, title, institution,
                    position, city, url, pdf_url, publish_date, deadline_date,
                    raw_content, matched_score_types, priority_level,
                    is_notified, notified_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                cursor = await conn.execute(
                    sql,
                    (
                        item.hash_id,
                        item.source_key,
                        item.source_name,
                        item.title,
                        item.institution,
                        item.position,
                        item.city,
                        item.url,
                        item.pdf_url,
                        item.publish_date,
                        item.deadline_date,
                        item.raw_content,
                        score_types_json,
                        item.priority_level.value,
                        1 if item.is_notified else 0,
                        item.notified_at,
                        item.created_at,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted_count += 1
            await conn.commit()
        return inserted_count

    async def get_by_id(self, announcement_id: int) -> Optional[Announcement]:
        """ID ile ilan getirir."""
        sql = "SELECT * FROM announcements WHERE id = ?;"
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(sql, (announcement_id,)) as cursor:
                row = await cursor.fetchone()
                return self._row_to_entity(row) if row else None

    async def list_announcements(
        self,
        params: AnnouncementFilterParams,
    ) -> Tuple[List[Announcement], int]:
        """Filtre parametrelerine göre ilanları ve toplam eşleşen sayısını döner."""
        conditions: List[str] = []
        sql_params: List[Any] = []

        if params.search_text:
            text = f"%{params.search_text.strip()}%"
            conditions.append("(title LIKE ? OR institution LIKE ? OR position LIKE ?)")
            sql_params.extend([text, text, text])

        if params.source_keys:
            placeholders = ",".join("?" for _ in params.source_keys)
            conditions.append(f"source_key IN ({placeholders})")
            sql_params.extend(params.source_keys)

        if params.only_unnotified:
            conditions.append("is_notified = 0")

        if params.only_p3:
            conditions.append("matched_score_types LIKE '%P3%'")
        elif params.score_types:
            sub = " OR ".join("matched_score_types LIKE ?" for _ in params.score_types)
            conditions.append(f"({sub})")
            sql_params.extend([f"%{st.value}%" for st in params.score_types])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Toplam eşleşme sayısı sorgusu
        count_sql = f"SELECT COUNT(*) FROM announcements {where_clause};"

        # Sayfalanmış veri sorgusu (Öncelikli P3 en üstte, ardından son tarihe göre)
        data_sql = f"""
        SELECT * FROM announcements
        {where_clause}
        ORDER BY priority_level DESC, id DESC
        LIMIT ? OFFSET ?;
        """

        async with get_db_connection(self.db_path) as conn:
            # Toplam sayı
            async with conn.execute(count_sql, sql_params) as cursor:
                total_row = await cursor.fetchone()
                total_count = total_row[0] if total_row else 0

            # Sayfa kayıtları
            data_params = list(sql_params) + [params.limit, params.offset]
            async with conn.execute(data_sql, data_params) as cursor:
                rows = await cursor.fetchall()
                items = [self._row_to_entity(r) for r in rows]

        return items, total_count

    async def get_unnotified_announcements(self, limit: int = 50) -> List[Announcement]:
        """Henüz Telegram ile bildirilmemiş ilanları döner."""
        sql = """
        SELECT * FROM announcements
        WHERE is_notified = 0
        ORDER BY priority_level DESC, id ASC
        LIMIT ?;
        """
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(sql, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_entity(r) for r in rows]

    async def mark_as_notified(self, ids: List[int]) -> int:
        """Verilen ID'lere sahip ilanları bildirilmiş olarak işaretler."""
        if not ids:
            return 0

        now_iso = datetime.now(timezone.utc).isoformat()
        placeholders = ",".join("?" for _ in ids)
        sql = f"""
        UPDATE announcements
        SET is_notified = 1, notified_at = ?
        WHERE id IN ({placeholders});
        """
        params = [now_iso] + ids

        async with get_db_connection(self.db_path) as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.rowcount

    async def get_system_stats(self) -> SystemStatsResponse:
        """Sistem genel istatistiklerini hesaplar."""
        async with get_db_connection(self.db_path) as conn:
            # Toplam ve bildirilmemiş
            async with conn.execute(
                "SELECT COUNT(*), SUM(CASE WHEN is_notified = 0 THEN 1 ELSE 0 END) FROM announcements;"
            ) as cursor:
                row = await cursor.fetchone()
                total = row[0] or 0
                unnotified = row[1] or 0

            # Puan türleri
            async with conn.execute(
                "SELECT COUNT(*) FROM announcements WHERE matched_score_types LIKE '%P3%';"
            ) as cursor:
                p3_count = (await cursor.fetchone())[0] or 0

            async with conn.execute(
                "SELECT COUNT(*) FROM announcements WHERE matched_score_types LIKE '%P1%' OR matched_score_types LIKE '%P2%';"
            ) as cursor:
                p1_p2_count = (await cursor.fetchone())[0] or 0

            # Portallara göre dağılım
            by_source: Dict[str, int] = {}
            async with conn.execute(
                "SELECT source_key, COUNT(*) FROM announcements GROUP BY source_key;"
            ) as cursor:
                rows = await cursor.fetchall()
                for r in rows:
                    by_source[r[0]] = r[1]

        general_count = total - (p3_count + p1_p2_count)

        return SystemStatsResponse(
            total_announcements=total,
            total_unnotified=unnotified,
            p3_count=p3_count,
            p1_p2_count=p1_p2_count,
            general_count=max(0, general_count),
            by_source=by_source,
        )
