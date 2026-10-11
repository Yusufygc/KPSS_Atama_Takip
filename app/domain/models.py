"""KPSS Atama Takip - Domain (İş Alanı) Modelleri."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from app.core.text import fold_turkish


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
    stable_url: bool = True,
) -> str:
    """İlan için deterministik SHA-256 parmak izi üretir (Mükerrer önleme).

    stable_url=False ise URL hash'e katılmaz: bazı portallar (örn. Kamu İlan SBB) her istekte
    farklı şifreli bir bağlantı üretir; URL'ye bağlı hash her taramada aynı ilanı "yeni" gösterirdi.
    Bu durumda kimlik kaynak + başlık + son tarihten oluşur.
    """
    url_part = url.strip().lower() if stable_url else ""
    raw_payload = f"{source_key.strip().lower()}|{title.strip().lower()}|{url_part}|{(deadline_date or '').strip()}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


def build_search_text(title: str, institution: str, position: Optional[str] = None) -> str:
    """Arama için başlık, kurum ve unvanı Türkçe katlanmış tek metne birleştirir."""
    return fold_turkish(f"{title} {institution} {position or ''}")


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
    # False: URL her istekte değişen portallar için hash URL'siz hesaplanır
    stable_url: bool = True
    position: Optional[str] = None
    city: Optional[str] = None
    pdf_url: Optional[str] = None
    publish_date: Optional[str] = None
    deadline_date: Optional[str] = None
    raw_content: Optional[str] = None
    matched_score_types: List[ScoreType] = field(default_factory=list)
    priority_level: PriorityLevel = PriorityLevel.NORMAL
    field_tags: List[str] = field(default_factory=list)
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
                stable_url=self.stable_url,
            )

    @property
    def has_p3_score(self) -> bool:
        """İlanın P3 puanı gerektirip gerektirmediğini döner."""
        return ScoreType.P3 in self.matched_score_types

    @property
    def has_career_score(self) -> bool:
        """İlanın P1 veya P2 puanı gerektirip gerektirmediğini döner."""
        return ScoreType.P1 in self.matched_score_types or ScoreType.P2 in self.matched_score_types

    @property
    def is_it_field(self) -> bool:
        """İlanın Bilgisayar Mühendisliği / Bilişim / Yazılım alanı olup olmadığını döner."""
        return bool(self.field_tags)
