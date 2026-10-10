"""KPSS Atama Takip - Domain (İş Alanı) Modelleri."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class ScoreType(str, Enum):
    """KPSS puan türleri."""

    P3 = "P3"            # Lisans Genel B Grubu (Öncelikli)
    P1 = "P1"            # Lisans A Grubu / Kariyer
    P2 = "P2"            # Lisans A Grubu / Kariyer
    GENERAL = "GENEL"    # Belirtilmemiş veya genel şart


class PriorityLevel(int, Enum):
    """İlan öncelik seviyesi."""

    NORMAL = 1           # Genel ilanlar
    CAREER_P1_P2 = 2     # P1 ve P2 kariyer meslekleri
    PRIORITY_P3 = 3      # Kullanıcının 1. önceliği olan P3 lisans kadroları


def compute_announcement_hash(
    source_key: str,
    title: str,
    url: str,
    deadline_date: Optional[str] = None,
) -> str:
    """İlan için deterministik SHA-256 parmak izi üretir (Mükerrer önleme)."""
    raw_payload = f"{source_key.strip().lower()}|{title.strip().lower()}|{url.strip().lower()}|{(deadline_date or '').strip()}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


@dataclass
class Announcement:
    """KPSS atama veya alım ilanını temsil eden ana domain varlığı (Entity)."""

    source_key: str
    source_name: str
    title: str
    institution: str
    url: str
    hash_id: str = ""
    id: Optional[int] = None
    position: Optional[str] = None
    city: Optional[str] = None
    pdf_url: Optional[str] = None
    publish_date: Optional[str] = None
    deadline_date: Optional[str] = None
    raw_content: Optional[str] = None
    matched_score_types: List[ScoreType] = field(default_factory=list)
    priority_level: PriorityLevel = PriorityLevel.NORMAL
    is_notified: bool = False
    notified_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        """Hash ID boşsa otomatik olarak hesaplar."""
        if not self.hash_id:
            self.hash_id = compute_announcement_hash(
                source_key=self.source_key,
                title=self.title,
                url=self.url,
                deadline_date=self.deadline_date,
            )

    @property
    def has_p3_score(self) -> bool:
        """İlanın P3 puanı gerektirip gerektirmediğini döner."""
        return ScoreType.P3 in self.matched_score_types

    @property
    def has_career_score(self) -> bool:
        """İlanın P1 veya P2 puanı gerektirip gerektirmediğini döner."""
        return ScoreType.P1 in self.matched_score_types or ScoreType.P2 in self.matched_score_types
