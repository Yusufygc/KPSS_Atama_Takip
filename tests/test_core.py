"""Aşama 1: Core ve Altyapı Temelleri Birim Testi."""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import settings
from app.core.constants import (
    PortalStrings,
    MessageStrings,
    ErrorStrings,
    NotificationStrings,
    StatusIcons,
    ScoreIcons,
    PortalIcons,
    ScraperLimits,
    NetworkConstants,
)
from app.core.exceptions import (
    KPSSBaseException,
    ScraperException,
    NetworkScraperException,
    ParsingScraperException,
    RateLimitScraperException,
    DatabaseException,
    RecordDuplicateException,
    QueryExecutionException,
    NotificationException,
    TelegramDeliveryException,
    ValidationException,
)
from app.core.logging import get_logger, get_scraper_logger


def test_configuration():
    print("1. Testing AppSettings...")
    assert settings.APP_NAME == "KPSS Atama Takip Sistemi"
    assert settings.APP_PORT == 8000
    assert settings.resolved_database_path.name == "kpss_atama.db"
    print("   [OK] Settings successfully loaded.")


def test_constants():
    print("2. Testing Constants (Strings & Icons & Settings)...")
    assert PortalStrings.KARIYER_KAPISI == "Kariyer Kapısı (CBİKO)"
    assert PortalStrings.RESMI_GAZETE == "T.C. Resmî Gazete"
    assert StatusIcons.SUCCESS == "✅"
    assert ScoreIcons.P3_PRIORITY == "🎓"
    assert PortalIcons.get_for_portal("kariyer_kapisi") == "💼"
    assert PortalIcons.get_for_portal("unknown") == "🌐"
    assert NetworkConstants.CONNECT_TIMEOUT_SECONDS == 10.0
    assert ScraperLimits.MAX_CONCURRENT_SCRAPERS == 5
    print("   [OK] Constants verified without magic strings.")


def test_exceptions_hierarchy():
    print("3. Testing Exception Hierarchy...")
    # Base
    base_ex = KPSSBaseException("Bilinmeyen hata", error_code="TEST_ERR", details={"k": "v"})
    assert base_ex.to_dict()["error_code"] == "TEST_ERR"
    assert base_ex.to_dict()["details"]["k"] == "v"

    # Scraper
    net_ex = NetworkScraperException("Timeout", portal_key="kariyer_kapisi", status_code=504, url="https://api.test")
    assert isinstance(net_ex, ScraperException)
    assert isinstance(net_ex, KPSSBaseException)
    assert net_ex.status_code == 504
    assert net_ex.portal_key == "kariyer_kapisi"

    # Database
    dup_ex = RecordDuplicateException("hash12345")
    assert isinstance(dup_ex, DatabaseException)
    assert dup_ex.hash_id == "hash12345"

    # Notification
    tg_ex = TelegramDeliveryException("Chat not found", chat_id="12345")
    assert isinstance(tg_ex, NotificationException)
    assert tg_ex.details["chat_id"] == "12345"

    # Validation
    val_ex = ValidationException("Geçersiz URL", field="url")
    assert isinstance(val_ex, KPSSBaseException)
    assert val_ex.field == "url"

    print("   [OK] Exception hierarchy works cleanly.")


def test_logging():
    print("4. Testing Structured and Rotating File Logging...")
    logger = get_logger("unit_test")
    logger.info("Test log mesajı: Kök logger çalışıyor.")

    scraper_logger = get_scraper_logger("KariyerKapisi")
    scraper_logger.info("Test log mesajı: 24 ilan başarıyla çekildi.")

    # Check if log file was created
    log_file = settings.LOGS_DIR / "app.log"
    assert log_file.exists(), f"Log file not found at {log_file}"
    content = log_file.read_text(encoding="utf-8")
    assert "Kök logger çalışıyor" in content
    assert "[KariyerKapisi] Test log mesajı" in content
    print(f"   [OK] Log file verified at: {log_file} ({len(content)} bytes)")


if __name__ == "__main__":
    print("=" * 50)
    print("RUNNING PHASE 1 CORE TEST SUITE")
    print("=" * 50)
    test_configuration()
    test_constants()
    test_exceptions_hierarchy()
    test_logging()
    print("=" * 50)
    print("ALL PHASE 1 CORE TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 50)
