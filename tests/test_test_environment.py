"""Test ortamı güvenceleri: Telegram zorla kapalı, canlı DB yasak, örnek veri betiği."""

import importlib.util
from pathlib import Path

import pytest

from app.config import AppSettings
from app.domain.schemas import AnnouncementFilterParams
from app.infrastructure.database.repository import AnnouncementRepository

BASE_DIR = Path(__file__).resolve().parent.parent


def test_test_env_forces_telegram_off_even_when_everything_asks_for_it(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "GERCEK-TOKEN")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("TELEGRAM_NOTIFICATIONS_ENABLED", "true")

    test_settings = AppSettings(_env_file=None, APP_ENV="test", DATABASE_PATH="data/test/x.db")

    assert test_settings.TELEGRAM_NOTIFICATIONS_ENABLED is False
    assert test_settings.TELEGRAM_BOT_TOKEN == "" and test_settings.TELEGRAM_CHAT_ID == ""


def test_other_environments_keep_their_telegram_settings(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOKEN")
    dev = AppSettings(_env_file=None, APP_ENV="development")
    assert dev.TELEGRAM_BOT_TOKEN == "TOKEN"


def test_test_env_cannot_use_the_live_database():
    with pytest.raises(ValueError, match="gerçek veritabanını"):
        AppSettings(_env_file=None, APP_ENV="test", DATABASE_PATH="data/kpss_atama.db")
    with pytest.raises(ValueError, match="gerçek veritabanını"):
        AppSettings(_env_file=None, APP_ENV="test", DATABASE_PATH="baska/dizin/kpss_atama.db")


def test_env_test_file_is_safe_by_itself():
    cfg = AppSettings(_env_file=BASE_DIR / ".env.test")
    assert cfg.APP_ENV == "test"
    assert cfg.TELEGRAM_NOTIFICATIONS_ENABLED is False and not cfg.TELEGRAM_BOT_TOKEN
    assert Path(cfg.DATABASE_PATH).name != "kpss_atama.db"
    assert cfg.APP_PORT == 8001 and cfg.SCRAPER_RUN_ON_STARTUP is False


def load_seed_module(monkeypatch):
    monkeypatch.setenv("APP_ENV_FILE", ".env")  # betik içe aktarılırken değiştirir; teardown eski değeri geri yükler
    spec = importlib.util.spec_from_file_location("seed_test_db", BASE_DIR / "scripts" / "seed_test_db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_seed_script_builds_realistic_test_database(tmp_path, monkeypatch):
    seed_module = load_seed_module(monkeypatch)
    db_path = tmp_path / "kpss_test.db"

    assert await seed_module.seed(db_path, reset=True) == len(seed_module.SAMPLES)
    assert await seed_module.seed(db_path, reset=False) == 0, "Dolu veritabanı yeniden doldurulmamalı"

    repo = AnnouncementRepository(db_path)
    items, total = await repo.list_announcements(AnnouncementFilterParams(limit=200))
    assert total == len(seed_module.SAMPLES)
    assert {i.source_key for i in items} == {"kariyer_kapisi", "kamu_ilan_sbb", "iskur", "yerel_yonetimler", "resmi_gazete", "ilan_gov_tr"}
    assert any(i.deadline_on for i in items) and any(not i.deadline_on for i in items)
    _, active_total = await repo.list_announcements(AnnouncementFilterParams(only_active=True, limit=200))
    assert active_total < total, "Süresi dolmuş örnek ilan bulunmalı"
    assert any(i.field_tags for i in items) and any(i.is_notified for i in items) and any(not i.is_notified for i in items)
    assert all(i.pdf_url for i in items if i.source_key == "resmi_gazete")


async def test_seed_script_refuses_the_live_database_name(tmp_path, monkeypatch):
    seed_module = load_seed_module(monkeypatch)
    with pytest.raises(SystemExit):
        await seed_module.seed(tmp_path / "kpss_atama.db", reset=False)
    assert not (tmp_path / "kpss_atama.db").exists()
