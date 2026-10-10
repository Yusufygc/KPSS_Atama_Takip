"""KPSS Atama Takip - Kazıyıcı Yönetimi REST Uç Noktaları."""

from typing import List
from fastapi import APIRouter

from app.api.dependencies import AnnouncementServiceDep
from app.domain.schemas import ScraperRunStatus

router = APIRouter(prefix="/scrapers", tags=["Kazıyıcılar"])


@router.post("/run", response_model=dict)
async def trigger_scraping(service: AnnouncementServiceDep):
    """Tüm portalları anlık olarak eşzamanlı tarar ve sonuçları döner."""
    new_count, statuses = await service.run_full_cycle()
    return {
        "success": True,
        "new_announcements": new_count,
        "statuses": statuses,
    }


@router.get("/status", response_model=List[ScraperRunStatus])
async def get_scrapers_status(service: AnnouncementServiceDep):
    """Tüm portalların en son çalışma durumu ve performans metriklerini döner."""
    return service.get_scraper_statuses()
