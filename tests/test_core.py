"""Çekirdek: yapılandırma, sabitler, istisna hiyerarşisi ve loglama."""

from app.config import settings
from app.core.constants import (
    NetworkConstants,
    PortalIcons,
    PortalStrings,
    ScoreIcons,
    StatusIcons,
)
from app.core.exceptions import (
    DatabaseException,
    KPSSBaseException,
    NetworkScraperException,
    NotificationException,
    RecordDuplicateException,
    ScraperException,
    TelegramDeliveryException,
    ValidationException,
)
from app.core.logging import get_logger, get_scraper_logger


def test_configuration(isolated_settings):
    assert settings.APP_NAME == "KPSS Atama Takip Sistemi"
    assert settings.resolved_database_path.name == "test.db"


def test_cors_origin_list_ignores_wildcard_and_blanks(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", " https://a.test , *, ,https://b.test")
    assert settings.cors_origin_list == ["https://a.test", "https://b.test"]


def test_constants():
    assert PortalStrings.KARIYER_KAPISI == "Kariyer Kapısı (CBİKO)"
    assert StatusIcons.SUCCESS == "✅"
    assert ScoreIcons.P3_PRIORITY == "🎓"
    assert PortalIcons.get_for_portal("kariyer_kapisi") == "💼"
    assert PortalIcons.get_for_portal("unknown") == "🌐"
    assert NetworkConstants.CONNECT_TIMEOUT_SECONDS == 10.0


def test_exceptions_hierarchy():
    base_ex = KPSSBaseException("Bilinmeyen hata", error_code="TEST_ERR", details={"k": "v"})
    assert base_ex.to_dict()["error_code"] == "TEST_ERR"

    net_ex = NetworkScraperException("Timeout", portal_key="kariyer_kapisi", status_code=504, url="https://api.test")
    assert isinstance(net_ex, ScraperException)
    assert net_ex.status_code == 504

    dup_ex = RecordDuplicateException("hash12345")
    assert isinstance(dup_ex, DatabaseException)

    tg_ex = TelegramDeliveryException("Chat not found", chat_id="12345")
    assert isinstance(tg_ex, NotificationException)

    assert ValidationException("Geçersiz URL", field="url").field == "url"


def test_logging(isolated_settings):
    get_logger("unit_test").info("Test log mesajı: Kök logger çalışıyor.")
    get_scraper_logger("KariyerKapisi").info("Test log mesajı: 24 ilan çekildi.")
    assert (settings.LOGS_DIR / "app.log").exists()


async def test_real_network_is_blocked_in_tests():
    import httpx
    import pytest

    with pytest.raises(RuntimeError, match="gerçek ağ isteği yasak"):
        async with httpx.AsyncClient() as http:
            await http.get("https://api.telegram.org/")


def test_shared_notifier_is_neutralised_in_tests():
    from app.api import dependencies

    assert dependencies._notifier.is_ready is False
