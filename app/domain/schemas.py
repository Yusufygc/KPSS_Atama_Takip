"""KPSS Atama Takip - Pydantic Veri Transfer Nesneleri (DTO / Schemas)."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.constants.icons import PortalIcons, ScoreIcons
from app.domain.models import PriorityLevel, ScoreType


class AnnouncementCreate(BaseModel):
    """Kazıyıcı adaptörlerinin ürettiği ham ilan DTO'su."""

    source_key: str
    source_name: str
    title: str
    institution: str
    url: str
    position: Optional[str] = None
    city: Optional[str] = None
    pdf_url: Optional[str] = None
    publish_date: Optional[str] = None
    deadline_date: Optional[str] = None
    raw_content: Optional[str] = None


class AnnouncementResponse(BaseModel):
    """API ve UI için formatlanmış zengin ilan yanıt modeli."""

    id: int
    hash_id: str
    source_key: str
    source_name: str
    source_icon: str = Field(default="")
    title: str
    institution: str
    position: Optional[str] = None
    city: Optional[str] = None
    url: str
    pdf_url: Optional[str] = None
    document_url: Optional[str] = None
    publish_date: Optional[str] = None
    deadline_date: Optional[str] = None
    matched_score_types: List[ScoreType] = []
    priority_level: PriorityLevel = PriorityLevel.NORMAL
    priority_icon: str = Field(default="")
    is_notified: bool = False
    notified_at: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, entity) -> "AnnouncementResponse":
        """Domain Entity'sinden API DTO'su üretir."""
        # İkon belirleme
        s_icon = PortalIcons.get_for_portal(entity.source_key)
        
        if entity.has_p3_score:
            p_icon = ScoreIcons.P3_PRIORITY
        elif entity.has_career_score:
            p_icon = ScoreIcons.P1_CAREER
        else:
            p_icon = ScoreIcons.GENERAL

        doc_url = f"/api/announcements/{entity.id}/document" if entity.id else None
        pdf_url = entity.pdf_url
        if entity.source_key == "kamu_ilan_sbb":
            pdf_url = pdf_url or doc_url

        return cls(
            id=entity.id or 0,
            hash_id=entity.hash_id,
            source_key=entity.source_key,
            source_name=entity.source_name,
            source_icon=s_icon,
            title=entity.title,
            institution=entity.institution,
            position=entity.position,
            city=entity.city,
            url=entity.url,
            pdf_url=pdf_url,
            document_url=doc_url,
            publish_date=entity.publish_date,
            deadline_date=entity.deadline_date,
            matched_score_types=entity.matched_score_types,
            priority_level=entity.priority_level,
            priority_icon=p_icon,
            is_notified=entity.is_notified,
            notified_at=entity.notified_at,
            created_at=entity.created_at,
        )


class AnnouncementFilterParams(BaseModel):
    """İlan filtreleme ve sorgulama parametreleri."""

    score_types: Optional[List[ScoreType]] = None
    source_keys: Optional[List[str]] = None
    search_text: Optional[str] = None
    only_unnotified: bool = False
    only_p3: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ScraperRunStatus(BaseModel):
    """Bir kazıyıcının çalışma durumunu ve metriklerini temsil eden DTO."""

    portal_key: str
    portal_name: str
    portal_icon: str = ""
    status: str  # "success", "error", "running"
    found_count: int = 0
    new_count: int = 0
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    last_run_at: Optional[str] = None


class SystemStatsResponse(BaseModel):
    """Sistem genel istatistikleri DTO'su."""

    total_announcements: int = 0
    total_unnotified: int = 0
    p3_count: int = 0
    p1_p2_count: int = 0
    general_count: int = 0
    by_source: dict = Field(default_factory=dict)
