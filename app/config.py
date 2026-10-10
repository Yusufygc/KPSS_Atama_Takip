"""KPSS Atama Takip - Merkezi Yapılandırma Yönetimi."""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Uygulama genel ayarlarını .env dosyasından okuyan tip güvenli sınıf."""

    # Uygulama Temel Ayarları
    APP_NAME: str = "KPSS Atama Takip Sistemi"
    APP_ENV: Literal["development", "production", "test"] = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Dizin Yolları
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_PATH: str = "data/kpss_atama.db"
    LOGS_DIR: Path = Path(__file__).resolve().parent.parent / "logs"

    # Telegram Entegrasyon Ayarları
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_NOTIFICATIONS_ENABLED: bool = False

    # Kazıma & Zamanlama Parametreleri
    SCRAPER_INTERVAL_MINUTES: int = 15
    SCRAPER_CONCURRENT_WORKERS: int = 3
    DEFAULT_HTTP_TIMEOUT_SECONDS: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        """Ortamın prodüksiyon olup olmadığını döner."""
        return self.APP_ENV == "production"

    @property
    def resolved_database_path(self) -> Path:
        """Veritabanı dosyasının mutlak yolunu döner ve dizinini garanti eder."""
        db_path = self.BASE_DIR / self.DATABASE_PATH
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path


# Tekil örnek (Singleton pattern)
settings = AppSettings()
