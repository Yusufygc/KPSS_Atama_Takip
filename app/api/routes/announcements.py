"""KPSS Atama Takip - İlan REST Uç Noktaları."""

from pathlib import Path
from typing import List, Optional
import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from app.api.dependencies import AnnouncementServiceDep
from app.core.logging import get_logger

logger = get_logger("routes.announcements")
DOCUMENTS_DIR = Path("data/documents")
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
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


@router.get("/{announcement_id}/document")
async def view_announcement_document(
    announcement_id: int,
    service: AnnouncementServiceDep,
):
    """İlanın resmi belgesini (PDF) önbellekten veya kaynaktan güvenli şekilde proxy ederek döner."""
    item = await service.repository.get_by_id(announcement_id)
    if not item:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")

    # Kamu İlan SBB ise, referer hotlink korumasını aşarak PDF'i sun
    if item.source_key == "kamu_ilan_sbb" or "kamuilan.sbb.gov.tr" in item.url:
        cached_file = DOCUMENTS_DIR / f"sbb_{item.id}.pdf"
        if cached_file.exists() and cached_file.stat().st_size > 2000:
            return FileResponse(
                path=str(cached_file),
                media_type="application/pdf",
                filename=f"{item.institution[:30]}_ilan_metni.pdf",
                content_disposition_type="inline",
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://kamuilan.sbb.gov.tr/",
        }
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                resp = await client.get(item.url, headers=headers)
                if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                    # Yerel önbelleğe kaydet
                    cached_file.write_bytes(resp.content)
                    return FileResponse(
                        path=str(cached_file),
                        media_type="application/pdf",
                        filename=f"{item.institution[:30]}_ilan_metni.pdf",
                        content_disposition_type="inline",
                    )
                else:
                    logger.warning(
                        f"SBB ilan belgesi alınamadı (HTTP {resp.status_code}): {item.url}"
                    )
                    raise HTTPException(
                        status_code=502,
                        detail="Kamu İlan (SBB) kaynağından ilan belgesi alınamadı.",
                    )
        except httpx.RequestError as exc:
            logger.error(f"SBB bağlantı hatası: {exc}")
            raise HTTPException(
                status_code=502,
                detail=f"Kamu İlan sunucusuna erişilemedi: {str(exc)}",
            )

    # Diğer portallarda PDF varsa ona, yoksa normal web URL'sine yönlendir
    target_url = item.pdf_url or item.url
    return RedirectResponse(url=target_url, status_code=307)

