"""REST API: kimlik doğrulama, güvenlik başlıkları, CORS ve belge proxy güvenliği."""

import asyncio

import pytest

from app.api import dependencies
from app.api.routes import announcements as announcements_route
from app.config import settings
from app.domain.models import Announcement, PriorityLevel, ScoreType


async def add_announcement(**overrides) -> int:
    data = {
        "source_key": "kariyer_kapisi",
        "source_name": "Kariyer Kapısı",
        "title": "Test İlanı",
        "institution": "Kurum",
        "url": "https://example.test/ilan",
        "matched_score_types": [ScoreType.P3],
        "priority_level": PriorityLevel.PRIORITY_P3,
    }
    data.update(overrides)
    return await dependencies._repository.save(Announcement(**data))


async def test_health_exposes_no_internal_details(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


async def test_security_headers_present(client):
    resp = await client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]


async def test_dashboard_and_static_assets_served(client):
    for path in ("/", "/js/app.js", "/js/icons.js", "/css/style.css"):
        assert (await client.get(path)).status_code == 200, path


async def test_cors_not_granted_to_foreign_origin(client):
    resp = await client.get("/api/announcements/stats", headers={"Origin": "https://evil.test"})
    assert "access-control-allow-origin" not in resp.headers


# --- API anahtarı ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/api/settings"), ("POST", "/api/settings/telegram/test"), ("POST", "/api/scrapers/run")],
)
async def test_admin_endpoints_require_key_when_configured(client, monkeypatch, method, path):
    monkeypatch.setattr(settings, "API_KEY", "s3cret")

    assert (await client.request(method, path)).status_code == 401
    assert (await client.request(method, path, headers={"X-API-Key": "yanlis"})).status_code == 401


async def test_settings_accessible_with_valid_key_and_masks_secrets(client, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "s3cret")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123456789:ABCDEFGHIJKLMNOP")
    monkeypatch.setattr(settings, "TELEGRAM_CHAT_ID", "987654321")

    resp = await client.get("/api/settings", headers={"X-API-Key": "s3cret"})
    assert resp.status_code == 200
    body = resp.text
    assert "123456789:ABCDEFGHIJKLMNOP" not in body
    assert "987654321" not in body
    assert resp.json()["telegram_chat_id_masked"] == "98...21"


async def test_admin_endpoints_closed_in_production_without_key(client, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "API_KEY", "")
    assert (await client.get("/api/settings")).status_code == 503
    assert (await client.post("/api/scrapers/run")).status_code == 503


async def test_public_read_endpoints_need_no_key(client, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "s3cret")
    for path in ("/api/announcements", "/api/announcements/stats", "/api/announcements/cities", "/api/scrapers/status"):
        assert (await client.get(path)).status_code == 200, path


async def test_concurrent_scrape_returns_409(client, monkeypatch):
    release = asyncio.Event()

    async def slow_run_all():
        await release.wait()
        return []

    monkeypatch.setattr(dependencies._service.orchestrator, "run_all", slow_run_all)

    first = asyncio.create_task(client.post("/api/scrapers/run"))
    await asyncio.sleep(0.05)
    second = await client.post("/api/scrapers/run")
    assert second.status_code == 409

    release.set()
    assert (await first).status_code == 200


# --- Belge proxy (SSRF) ----------------------------------------------------------


async def test_document_never_fetches_foreign_host_server_side(client, monkeypatch):
    called = []

    async def fake_download(url):
        called.append(url)

    monkeypatch.setattr(announcements_route, "_download_pdf_capped", fake_download)
    spoofed = "https://evil.test/?kamuilan.sbb.gov.tr"  # eski alt dize kontrolünü geçerdi

    # SBB olarak işaretli ama host'u farklı: reddedilir
    sbb_id = await add_announcement(title="sbb", source_key="kamu_ilan_sbb", url=spoofed)
    assert (await client.get(f"/api/announcements/{sbb_id}/document")).status_code == 400

    # Başka kaynak, URL'de SBB alan adı geçiyor: sunucu istek atmaz, tarayıcıya yönlendirir
    other_id = await add_announcement(title="diger", source_key="yerel_yonetimler", url=spoofed)
    resp = await client.get(f"/api/announcements/{other_id}/document", follow_redirects=False)
    assert resp.status_code == 307

    assert called == [], "Sunucu izin verilmeyen host'a istek atmamalı"


async def test_document_proxies_and_caches_valid_sbb_pdf(client, monkeypatch):
    calls = []

    async def fake_download(url):
        calls.append(url)
        return b"%PDF-1.4" + b"0" * 3000

    monkeypatch.setattr(announcements_route, "_download_pdf_capped", fake_download)
    item_id = await add_announcement(
        source_key="kamu_ilan_sbb", url="https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=1"
    )

    first = await client.get(f"/api/announcements/{item_id}/document")
    second = await client.get(f"/api/announcements/{item_id}/document")
    assert first.status_code == second.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert len(calls) == 1, "İkinci istek önbellekten karşılanmalı"


async def test_document_redirects_only_to_http_urls(client):
    ok_id = await add_announcement(title="ok", url="https://example.test/a", pdf_url="https://example.test/a.pdf")
    bad_id = await add_announcement(title="bad", url="https://example.test/b", pdf_url="javascript:alert(1)")

    ok = await client.get(f"/api/announcements/{ok_id}/document", follow_redirects=False)
    assert ok.status_code == 307 and ok.headers["location"] == "https://example.test/a.pdf"

    bad = await client.get(f"/api/announcements/{bad_id}/document", follow_redirects=False)
    assert bad.status_code == 404


async def test_document_unknown_id_is_404(client):
    assert (await client.get("/api/announcements/999/document")).status_code == 404


async def test_scheduler_and_api_share_one_service():
    from app.main import scheduler_service

    assert scheduler_service.service is dependencies._service


async def test_server_side_domain_errors_return_5xx_without_leaking_details(client, monkeypatch):
    from app.core.exceptions.database import DatabaseException

    async def boom(*args, **kwargs):
        raise DatabaseException("sqlite dosya yolu: C:/gizli/yol.db", details={"path": "C:/gizli/yol.db"})

    monkeypatch.setattr(dependencies._service.repository, "get_system_stats", boom)
    resp = await client.get("/api/announcements/stats")
    assert resp.status_code == 500
    assert "gizli" not in resp.text
