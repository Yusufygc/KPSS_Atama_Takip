"""KPSS Atama Takip - İlan REST Uç Noktaları."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import AnnouncementServiceDep
from app.domain.models import ScoreType
from app.domain.schemas import (
    AnnouncementFilterParams,
    AnnouncementResponse,
    SystemStatsResponse,
)

router = APIRouter(prefix="/announcements", tags=["İlanlar"])


@router.get("", response_model=dict)
async def list_announcements(
    service: AnnouncementServiceDep,
    search: Optional[str] = Query(None, description="Arama metni"),
    score_type: Optional[List[ScoreType]] = Query(None, description="Puan türleri"),
    source_key: Optional[List[str]] = Query(None, description="Kaynak portallar"),
    only_p3: bool = Query(False, description="Sadece öncelikli P3 ilanları"),
    only_unnotified: bool = Query(False, description="Sadece bildirilmemiş olanlar"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa boyutu"),
    offset: int = Query(0, ge=0, description="Sayfa başlangıcı"),
):
    """Filtrelenmiş ve sayfalanmış KPSS atama ilanlarını döner."""
    params = AnnouncementFilterParams(
        search_text=search,
        score_types=score_type,
        source_keys=source_key,
        only_p3=only_p3,
        only_unnotified=only_unnotified,
        limit=limit,
        offset=offset,
    )
    items, total = await service.get_announcements(params)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(service: AnnouncementServiceDep):
    """Sistem geneli toplam ve puan türü bazlı istatistikleri döner."""
    return await service.get_stats()


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement_by_id(
    announcement_id: int,
    service: AnnouncementServiceDep,
):
    """Tek bir ilanın detayını döner."""
    item = await service.repository.get_by_id(announcement_id)
    if not item:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")
    return AnnouncementResponse.from_entity(item)
