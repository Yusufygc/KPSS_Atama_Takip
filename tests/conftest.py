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
    return settings


@pytest.fixture
async def db_ready(isolated_settings):
    await init_database()


@pytest.fixture
async def client(db_ready):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
