"""KPSS Atama Takip - İlan REST Uç Noktaları."""

from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from app.api.dependencies import AnnouncementServiceDep
from app.config import settings
from app.core.constants.settings import NetworkConstants, ScraperLimits
from app.core.constants.strings import ErrorStrings
from app.core.logging import get_logger
from app.core.security import host_in_domains, is_http_url
from app.domain.models import ScoreType
from app.domain.schemas import (
    AnnouncementFilterParams,
    AnnouncementResponse,
    CityCountResponse,
    SystemStatsResponse,
)

logger = get_logger("routes.announcements")

router = APIRouter(prefix="/announcements", tags=["İlanlar"])


@router.get("", response_model=dict)
async def list_announcements(
    service: AnnouncementServiceDep,
    search: Optional[str] = Query(None, description="Arama metni"),
    city: Optional[str] = Query(None, description="Şehir / İl filtresi"),
    score_type: Optional[List[ScoreType]] = Query(None, description="Puan türleri"),
    source_key: Optional[List[str]] = Query(None, description="Kaynak portallar"),
    only_p3: bool = Query(False, description="Sadece öncelikli P3 ilanları"),
    only_it: bool = Query(False, description="Sadece Bilgisayar & Bilişim / Yazılım ilanları"),
    field_tag: Optional[str] = Query(None, description="Bilişim alt uzmanlık etiketi"),
    only_unnotified: bool = Query(False, description="Sadece bildirilmemiş olanlar"),
    only_active: bool = Query(False, description="Süresi dolmamış (veya tarihi bilinmeyen) ilanlar"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa boyutu"),
    offset: int = Query(0, ge=0, description="Sayfa başlangıcı"),
):
    """Filtrelenmiş ve sayfalanmış KPSS atama ilanlarını döner."""
    params = AnnouncementFilterParams(
        search_text=search,
        city=city,
        score_types=score_type,
        source_keys=source_key,
        only_p3=only_p3,
        only_it=only_it,
        field_tag=field_tag,
        only_unnotified=only_unnotified,
        only_active=only_active,
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


@router.get("/cities", response_model=List[CityCountResponse])
async def list_cities(
    service: AnnouncementServiceDep,
    only_active: bool = Query(False, description="Yalnızca süresi dolmamış ilanlar"),
):
    """İlanlarda geçen şehirleri ve ilan sayılarını döner."""
    return await service.repository.get_distinct_cities(only_active=only_active)


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    service: AnnouncementServiceDep,
    only_active: bool = Query(False, description="Yalnızca süresi dolmamış ilanlar"),
):
    """Sistem geneli toplam ve puan türü bazlı istatistikleri döner."""
    return await service.get_stats(only_active=only_active)


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


def _pdf_response(path, institution: str) -> FileResponse:
    """Önbellekteki PDF dosyasını tarayıcıda görüntülenecek şekilde döner."""
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"{institution[:30]}_ilan_metni.pdf",
        content_disposition_type="inline",
    )


async def _download_pdf_capped(url: str) -> Optional[bytes]:
    """PDF'i boyut sınırıyla indirir; geçerli bir PDF değilse None döner."""
    headers = {
        "User-Agent": NetworkConstants.DEFAULT_USER_AGENT,
        "Referer": "https://kamuilan.sbb.gov.tr/",
    }
    max_bytes = ScraperLimits.MAX_DOCUMENT_BYTES
    # Yönlendirmeler kapalı: izin verilen host'tan başka adrese sıçrama (SSRF) engellenir
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        async with client.stream("GET", url, headers=headers) as resp:
            if resp.status_code != 200:
                logger.warning(f"SBB ilan belgesi alınamadı (HTTP {resp.status_code}): {url}")
                return None
            chunks: List[bytes] = []
            size = 0
            async for chunk in resp.aiter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=502, detail=ErrorStrings.DOCUMENT_TOO_LARGE)
                chunks.append(chunk)
    content = b"".join(chunks)
    return content if content.startswith(b"%PDF") else None


@router.get("/{announcement_id}/document")
async def view_announcement_document(
    announcement_id: int,
    service: AnnouncementServiceDep,
):
    """İlanın resmi belgesini (PDF) önbellekten veya kaynaktan güvenli şekilde proxy ederek döner."""
    item = await service.repository.get_by_id(announcement_id)
    if not item:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")

    allowed_domains = ScraperLimits.DOCUMENT_ALLOWED_DOMAINS

    # Kamu İlan SBB ise, referer hotlink korumasını aşarak PDF'i sun
    if item.source_key == "kamu_ilan_sbb" or host_in_domains(item.url, allowed_domains):
        if not host_in_domains(item.url, allowed_domains):
            logger.warning(f"İzin verilmeyen belge adresi reddedildi (ilan {item.id}): {item.url}")
            raise HTTPException(status_code=400, detail=ErrorStrings.DOCUMENT_HOST_NOT_ALLOWED)

        settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        cached_file = settings.DOCUMENTS_DIR / f"sbb_{item.id}.pdf"
        if (
            cached_file.exists()
            and cached_file.stat().st_size > ScraperLimits.DOCUMENT_MIN_VALID_BYTES
        ):
            return _pdf_response(cached_file, item.institution)

        try:
            content = await _download_pdf_capped(item.url)
        except httpx.RequestError as exc:
            logger.error(f"SBB bağlantı hatası: {exc}")
            raise HTTPException(
                status_code=502, detail="Kamu İlan sunucusuna erişilemedi."
            ) from exc

        if content is None:
            raise HTTPException(
                status_code=502,
                detail="Kamu İlan (SBB) kaynağından ilan belgesi alınamadı.",
            )
        cached_file.write_bytes(content)
        return _pdf_response(cached_file, item.institution)

    # Diğer portallarda PDF varsa ona, yoksa normal web URL'sine yönlendir (yalnızca http/https)
    target_url = item.pdf_url or item.url
    if not is_http_url(target_url):
        raise HTTPException(status_code=404, detail="Geçerli bir belge adresi bulunamadı.")
    return RedirectResponse(url=target_url, status_code=307)
