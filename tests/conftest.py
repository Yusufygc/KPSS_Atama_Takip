"""Ortak pytest fixture'ları: her test için izole geçici veritabanı ve belge dizini."""

import sys
from pathlib import Path

import httpx
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import settings  # noqa: E402
from app.infrastructure.database.connection import init_database  # noqa: E402
from app.main import app  # noqa: E402


def pytest_addoption(parser):
    parser.addoption("--run-live", action="store_true", default=False, help="Canlı portal testlerini çalıştır")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return
    skip_live = pytest.mark.skip(reason="Canlı ağ testi: --run-live ile çalıştırın")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Gerçek data/ dizinine ve .env değerlerine dokunmadan test ortamı kurar."""
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "DOCUMENTS_DIR", tmp_path / "documents")
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "API_KEY", "")
    monkeypatch.setattr(settings, "TELEGRAM_NOTIFICATIONS_ENABLED", False)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(settings, "TELEGRAM_NOTIFY_FILTER", "all")  # filtre testleri kendi modunu ayarlar
    monkeypatch.setattr(settings, "TELEGRAM_CHAT_ID", "")

    # api.dependencies içindeki paylaşılan bildirici içe aktarma anında .env değerleriyle üretilir;
    # testlerin gerçek Telegram hesabına mesaj atmaması için bu örnek de etkisizleştirilir.
    from app.api import dependencies

    monkeypatch.setattr(dependencies._notifier, "bot_token", "")
    monkeypatch.setattr(dependencies._notifier, "chat_id", "")
    monkeypatch.setattr(dependencies._notifier, "is_enabled", False)
    return settings


@pytest.fixture(autouse=True)
def forbid_real_network(request, monkeypatch):
    """Testlerin gerçek ağ isteği atmasını engeller (sahte/ASGI transport'lar serbest).

    Canlı portal testleri `@pytest.mark.live` ile bu korumadan muaf tutulur.
    """
    if "live" in request.keywords:
        return

    real_send = httpx.AsyncClient.send

    async def guarded_send(self, request_obj, *args, **kwargs):
        if isinstance(self._transport, httpx.AsyncHTTPTransport):
            raise RuntimeError(f"Testte gerçek ağ isteği yasak: {request_obj.method} {request_obj.url}")
        return await real_send(self, request_obj, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", guarded_send)


@pytest.fixture
async def db_ready(isolated_settings):
    await init_database()


@pytest.fixture
async def client(db_ready):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
