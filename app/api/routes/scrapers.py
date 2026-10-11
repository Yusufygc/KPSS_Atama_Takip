"""KPSS Atama Takip - Kazıyıcı Yönetimi REST Uç Noktaları."""

from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.dependencies import AnnouncementServiceDep
from app.api.security import ApiKeyDep
from app.core.exceptions.scraper import ScrapeInProgressException
from app.domain.schemas import ScraperRunStatus

router = APIRouter(prefix="/scrapers", tags=["Kazıyıcılar"])


@router.post("/run", response_model=dict, dependencies=[ApiKeyDep])
async def trigger_scraping(
    service: AnnouncementServiceDep,
    wait: bool = Query(False, description="True: tarama bitene kadar bekle ve sonucu dön (uzun sürebilir)"),
):
    """Tüm portalları tarar.

    Varsayılan olarak taramayı arka planda başlatır (202) ve hemen döner; ilerlemeyi
    `GET /api/scrapers/run/status` ile izleyin. `wait=true` eşzamanlı çalışır.
    """
    try:
        if wait:
            new_count, statuses = await service.run_full_cycle()
            return {"success": True, "new_announcements": new_count, "statuses": statuses}
        service.start_background_cycle()
    except ScrapeInProgressException as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"success": True, "started": True})


@router.get("/run/status", response_model=dict)
async def get_run_status(service: AnnouncementServiceDep):
    """Taramanın çalışıp çalışmadığını ve son tamamlanan taramanın özetini döner."""
    return {"running": service.is_scraping, "last_cycle": service.last_cycle}


@router.get("/status", response_model=List[ScraperRunStatus])
async def get_scrapers_status(service: AnnouncementServiceDep):
    """Tüm portalların en son çalışma durumu ve performans metriklerini döner."""
    return service.get_scraper_statuses()
