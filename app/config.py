"""KPSS Atama Takip - Merkezi Yapılandırma Yönetimi."""

import os
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Gerçek (canlı) veritabanı dosya adı; test ortamı bu dosyayı kullanamaz
LIVE_DATABASE_FILENAME = "kpss_atama.db"

# Hangi .env dosyasının okunacağı APP_ENV_FILE ile seçilir (örn. test ortamı için ".env.test").
# Seçilen dosya yalnızca kendisi okunur; böylece .env içindeki gerçek Telegram bilgileri yüklenmez.
ENV_FILE = os.environ.get("APP_ENV_FILE", ".env")


class AppSettings(BaseSettings):
    """Uygulama genel ayarlarını .env dosyasından okuyan tip güvenli sınıf."""

    # Uygulama Temel Ayarları
    APP_NAME: str = "KPSS Atama Takip Sistemi"
    APP_ENV: Literal["development", "production", "test"] = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # Güvenlik: Yönetim uç noktaları (tarama tetikleme, ayarlar) için X-API-Key değeri.
    # Boş bırakılırsa geliştirme ortamında kontrol atlanır, prodüksiyonda uç noktalar kapalıdır.
    API_KEY: str = ""
    # Virgülle ayrılmış CORS kaynak listesi. Web UI aynı origin'den sunulduğu için varsayılan boştur.
    CORS_ORIGINS: str = ""

    # Dizin Yolları
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_PATH: str = "data/kpss_atama.db"
    DOCUMENTS_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "documents"
    LOGS_DIR: Path = Path(__file__).resolve().parent.parent / "logs"

    # Telegram Entegrasyon Ayarları
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_NOTIFICATIONS_ENABLED: bool = False
    # Bir portal art arda bu kadar taramada hata verirse tek bir Telegram uyarısı gönderilir (0: kapalı)
    PORTAL_FAILURE_ALERT_THRESHOLD: int = 3
    # Boş veritabanında ilk taramada bulunan mevcut ilanlar için bildirim gönderilsin mi (varsayılan: hayır)
    NOTIFY_ON_FIRST_RUN: bool = False
    # Tek taramada tek tek gönderilecek en fazla bildirim; fazlası tek özet mesajıyla bildirilir
    TELEGRAM_MAX_PER_CYCLE: int = 15
    # Mesajlar arası bekleme (Telegram aynı sohbete saniyede ~1 mesaj önerir)
    TELEGRAM_SEND_INTERVAL_SECONDS: float = 1.1
    # Gönderilemeyen bildirimler yalnızca bu kadar saat içinde yeniden denenir (eski ilanlar yağmuru olmasın)
    TELEGRAM_RETRY_WINDOW_HOURS: int = 24

    # Veritabanı yedekleme (günlük, TRT saatiyle DB_BACKUP_HOUR; en yeni DB_BACKUP_KEEP yedek tutulur)
    DB_BACKUP_ENABLED: bool = True
    DB_BACKUP_DIR: str = "data/backups"
    DB_BACKUP_KEEP: int = 7
    DB_BACKUP_HOUR: int = 4

    # Kazıma & Zamanlama Parametreleri
    SCRAPER_INTERVAL_MINUTES: int = 15
    SCRAPER_CONCURRENT_WORKERS: int = 3
    # Uygulama açıldığında ilk taramayı beklemeden (kısa gecikmeyle) başlat
    SCRAPER_RUN_ON_STARTUP: bool = True
    SCRAPER_STARTUP_DELAY_SECONDS: int = 20
    # İlan.gov.tr için Chrome/Edge/Chromium yolu (boşsa otomatik aranır)
    BROWSER_EXECUTABLE_PATH: str = ""
    # Chromium sandbox'ı yalnızca zaten izole bir kapsayıcı (Docker) içinde kapatılmalıdır
    BROWSER_NO_SANDBOX: bool = False

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _isolate_test_environment(self) -> "AppSettings":
        """Test ortamı gerçek dünyaya dokunamaz: Telegram kapatılır ve canlı veritabanı yasaktır."""
        if self.APP_ENV != "test":
            return self
        self.TELEGRAM_NOTIFICATIONS_ENABLED = False
        self.TELEGRAM_BOT_TOKEN = ""
        self.TELEGRAM_CHAT_ID = ""
        if Path(self.DATABASE_PATH).name == LIVE_DATABASE_FILENAME:
            raise ValueError(
                f"APP_ENV=test gerçek veritabanını ({LIVE_DATABASE_FILENAME}) kullanamaz; "
                "DATABASE_PATH olarak ayrı bir test dosyası verin (örn. data/test/kpss_test.db)."
            )
        return self

    @property
    def is_production(self) -> bool:
        """Ortamın prodüksiyon olup olmadığını döner."""
        return self.APP_ENV == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        """Virgülle ayrılmış CORS_ORIGINS değerini temiz bir listeye çevirir."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]

    @property
    def resolved_database_path(self) -> Path:
        """Veritabanı dosyasının mutlak yolunu döner ve dizinini garanti eder."""
        db_path = self.BASE_DIR / self.DATABASE_PATH
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path


# Tekil örnek (Singleton pattern)
settings = AppSettings()
