"""KPSS Atama Takip - İlan Veritabanı Deposu (Repository Pattern)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from app.core.dates import today_in_turkey
from app.core.logging import get_logger
from app.core.text import fold_turkish
from app.domain.models import Announcement, PriorityLevel, ScoreType, build_search_text
from app.domain.schemas import AnnouncementFilterParams, SystemStatsResponse
from app.infrastructure.database.connection import get_db_connection

logger = get_logger("database.repository")

INSERT_SQL = """
INSERT OR IGNORE INTO announcements (
    hash_id, source_key, source_name, title, institution,
    position, city, url, pdf_url, publish_date, deadline_date, deadline_on,
    raw_content, matched_score_types, priority_level,
    field_tags, is_it_field,
    is_notified, notified_at, created_at, search_text
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


LIKE_ESCAPE = "ESCAPE '" + chr(92) + "'"


def _escape_like(value: str) -> str:
    """LIKE sorgusunda özel anlam taşıyan %, _ ve ters eğik çizgiyi kaçışlar (ESCAPE ters eğik çizgi)."""
    escape_char = chr(92)
    return (
        value.replace(escape_char, escape_char * 2)
        .replace("%", escape_char + "%")
        .replace("_", escape_char + "_")
    )


def _insert_params(item: Announcement) -> tuple:
    """Announcement varlığını INSERT_SQL parametre sırasına çevirir."""
    return (
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
        item.deadline_on,
        item.raw_content,
        json.dumps([s.value for s in item.matched_score_types]),
        item.priority_level.value,
        json.dumps(item.field_tags, ensure_ascii=False),
        1 if item.is_it_field else 0,
        1 if item.is_notified else 0,
        item.notified_at,
        item.created_at,
        build_search_text(item.title, item.institution, item.position),
    )


class AnnouncementRepository:
    """İlanların kalıcılığını asenkron yöneten Repository sınıfı."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path

    @staticmethod
    def _safe_priority(value: Optional[int]) -> PriorityLevel:
        """Geçersiz/boş öncelik değerlerinde NORMAL seviyeye döner."""
        try:
            return PriorityLevel(value)
        except ValueError:
            return PriorityLevel.NORMAL

    def _row_to_entity(self, row: aiosqlite.Row) -> Announcement:
        """aiosqlite.Row nesnesini Announcement Domain Entity'sine dönüştürür."""
        # JSON puan türlerini ScoreType listesine dönüştür
        score_types_raw = row["matched_score_types"]
        score_types: List[ScoreType] = []
        if score_types_raw:
            try:
                parsed = json.loads(score_types_raw)
                score_types = [ScoreType(s) for s in parsed if s in ScoreType._value2member_map_]
            except (ValueError, TypeError) as exc:
                logger.warning(f"Geçersiz matched_score_types değeri yok sayıldı: {exc}")

        field_tags_raw = row["field_tags"] if "field_tags" in row.keys() else None
        field_tags: List[str] = []
        if field_tags_raw:
            try:
                parsed_tags = json.loads(field_tags_raw)
                field_tags = [str(t) for t in parsed_tags] if isinstance(parsed_tags, list) else []
            except ValueError as exc:
                logger.warning(f"Geçersiz field_tags değeri yok sayıldı: {exc}")

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
            deadline_on=row["deadline_on"] if "deadline_on" in row.keys() else None,
            raw_content=row["raw_content"],
            matched_score_types=score_types,
            priority_level=self._safe_priority(row["priority_level"]),
            field_tags=field_tags,
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
        async with get_db_connection(self.db_path) as conn:
            cursor = await conn.execute(INSERT_SQL, _insert_params(item))
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
                cursor = await conn.execute(INSERT_SQL, _insert_params(item))
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
            # Türkçe harf duyarsız arama: hem sorgu hem kayıt katlanmış (search_text) biçimde karşılaştırılır
            folded = fold_turkish(params.search_text)
            if folded:
                conditions.append(f"search_text LIKE ? {LIKE_ESCAPE}")
                sql_params.append(f"%{_escape_like(folded)}%")

        if params.source_keys:
            placeholders = ",".join("?" for _ in params.source_keys)
            conditions.append(f"source_key IN ({placeholders})")
            sql_params.extend(params.source_keys)

        if params.only_unnotified:
            conditions.append("is_notified = 0")

        if params.only_active:
            # Son başvuru günü geçmemiş veya tarihi bilinmeyen ilanlar
            conditions.append("(deadline_on IS NULL OR deadline_on >= ?)")
            sql_params.append(today_in_turkey().isoformat())

        if params.only_p3:
            conditions.append("matched_score_types LIKE '%P3%'")
        elif params.score_types:
            sub = " OR ".join("matched_score_types LIKE ?" for _ in params.score_types)
            conditions.append(f"({sub})")
            sql_params.extend([f"%{st.value}%" for st in params.score_types])

        if params.only_it:
            conditions.append("(is_it_field = 1 OR (field_tags IS NOT NULL AND field_tags != '[]'))")

        if params.field_tag:
            # Etiket JSON dizisinde tırnaklı tam değer olarak aranır ("Ağ & Sistem" -> kısmi eşleşme yok)
            conditions.append(f"field_tags LIKE ? {LIKE_ESCAPE}")
            sql_params.append(f"%\"{_escape_like(params.field_tag.strip())}\"%")

        if params.city:
            conditions.append("city = ?")
            sql_params.append(params.city.strip())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Toplam eşleşme sayısı sorgusu
        # where_clause yalnızca sabit koşul ve ? yer tutucularından oluşur; kullanıcı girdisi parametre olarak geçer
        count_sql = f"SELECT COUNT(*) FROM announcements {where_clause};"  # noqa: S608  # nosec B608

        # Sayfalanmış veri sorgusu: önce süresi dolmamışlar, sonra öncelik (P3 en üstte), sonra en yeni
        data_sql = (
            f"SELECT * FROM announcements {where_clause} "  # noqa: S608  # nosec B608
            "ORDER BY (deadline_on IS NOT NULL AND deadline_on < ?) ASC, priority_level DESC, id DESC "
            "LIMIT ? OFFSET ?;"
        )

        async with get_db_connection(self.db_path) as conn:
            # Toplam sayı
            async with conn.execute(count_sql, sql_params) as cursor:
                total_row = await cursor.fetchone()
                total_count = total_row[0] if total_row else 0

            # Sayfa kayıtları
            data_params = [*sql_params, today_in_turkey().isoformat(), params.limit, params.offset]
            async with conn.execute(data_sql, data_params) as cursor:
                rows = await cursor.fetchall()
                items = [self._row_to_entity(r) for r in rows]

        return items, total_count

    async def count_all(self) -> int:
        """Toplam ilan sayısını döner."""
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute("SELECT COUNT(*) FROM announcements;") as cursor:
                return (await cursor.fetchone())[0] or 0

    async def get_unnotified_announcements(
        self,
        limit: int = 50,
        since_hours: Optional[int] = None,
    ) -> List[Announcement]:
        """Henüz Telegram ile bildirilmemiş ilanları (öncelik sırasıyla) döner.

        since_hours verilirse yalnızca son N saatte eklenen ilanlar döner; böylece eski
        bildirilmemiş kayıtlar yeniden deneme sırasında toplu mesaj yağmuruna yol açmaz.
        """
        conditions = ["is_notified = 0"]
        params: List[Any] = []
        if since_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
            conditions.append("created_at >= ?")
            params.append(cutoff.isoformat())
        sql = (
            f"SELECT * FROM announcements WHERE {' AND '.join(conditions)} "  # noqa: S608  # nosec B608
            "ORDER BY priority_level DESC, id ASC LIMIT ?;"
        )
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(sql, [*params, limit]) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_entity(r) for r in rows]

    async def mark_as_notified(self, ids: List[int]) -> int:
        """Verilen ID'lere sahip ilanları bildirilmiş olarak işaretler."""
        if not ids:
            return 0

        now_iso = datetime.now(timezone.utc).isoformat()
        placeholders = ",".join("?" for _ in ids)
        sql = (
            "UPDATE announcements SET is_notified = 1, notified_at = ? "  # noqa: S608  # nosec B608
            f"WHERE id IN ({placeholders});"
        )
        params = [now_iso] + ids

        async with get_db_connection(self.db_path) as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.rowcount

    @staticmethod
    def _active_clause(only_active: bool) -> Tuple[str, List[Any]]:
        """only_active için WHERE parçası ve parametresi (süresi dolmamış veya tarihi bilinmeyen)."""
        if not only_active:
            return "", []
        return " WHERE (deadline_on IS NULL OR deadline_on >= ?)", [today_in_turkey().isoformat()]

    async def get_system_stats(self, only_active: bool = False) -> SystemStatsResponse:
        """Sistem genel istatistiklerini hesaplar (only_active: süresi dolanlar sayılmaz)."""
        where, params = self._active_clause(only_active)
        # Tek tarama: koşullu toplamlar. Puan türleri JSON metni içinde aranır ve örtüşebilir.
        stats_sql = (
            "SELECT COUNT(*), "  # noqa: S608  # nosec B608 (where yalnızca sabit koşul + ? yer tutucusu)
            "SUM(CASE WHEN is_notified = 0 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN matched_score_types LIKE '%P3%' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN matched_score_types LIKE '%P1%' OR matched_score_types LIKE '%P2%' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN matched_score_types NOT LIKE '%P1%' AND matched_score_types NOT LIKE '%P2%' "
            "AND matched_score_types NOT LIKE '%P3%' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN is_it_field = 1 OR (field_tags IS NOT NULL AND field_tags != '[]') THEN 1 ELSE 0 END) "
            f"FROM announcements{where};"
        )
        source_sql = f"SELECT source_key, COUNT(*) FROM announcements{where} GROUP BY source_key;"  # noqa: S608  # nosec B608

        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(stats_sql, params) as cursor:
                row = await cursor.fetchone()
            async with conn.execute(source_sql, params) as cursor:
                by_source = {r[0]: r[1] for r in await cursor.fetchall()}

        total, unnotified, p3_count, p1_p2_count, general_count, it_count = (v or 0 for v in row)
        return SystemStatsResponse(
            total_announcements=total,
            total_unnotified=unnotified,
            p3_count=p3_count,
            p1_p2_count=p1_p2_count,
            general_count=general_count,
            it_count=it_count,
            by_source=by_source,
        )

    async def get_distinct_cities(self, only_active: bool = False) -> List[Dict[str, Any]]:
        """Kayıtlı şehirlerin listesini ve her birindeki ilan sayısını döner."""
        where, params = self._active_clause(only_active)
        condition = "city IS NOT NULL AND city != ''"
        where = f"{where} AND {condition}" if where else f" WHERE {condition}"
        sql = (
            f"SELECT city, COUNT(*) AS count FROM announcements{where} "  # noqa: S608  # nosec B608
            "GROUP BY city ORDER BY count DESC, city ASC;"
        )
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [{"name": row["city"], "count": row["count"]} for row in rows]
