"""KPSS Atama Takip - Ağ ve Kazıma Sabitleri (Magic Number Önleyici)."""


class NetworkConstants:
    """HTTP ve ağ yapılandırma sabitleri."""

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    DEFAULT_HEADERS = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    JSON_HEADERS = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    CONNECT_TIMEOUT_SECONDS = 10.0
    READ_TIMEOUT_SECONDS = 20.0
    TOTAL_TIMEOUT_SECONDS = 30.0

    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 1.5  # Katlanarak artan bekleme faktörü
    RETRY_STATUS_CODES = [429, 500, 502, 503, 504]


class ScraperLimits:
    """Kazıma motoru sınır ve eşik sabitleri."""

    MAX_CONCURRENT_SCRAPERS = 5
    DEFAULT_PAGE_SIZE = 50
    TITLE_MAX_LENGTH = 500
    INSTITUTION_MAX_LENGTH = 250
    CONTENT_PREVIEW_LENGTH = 300
    HASH_PREFIX_LENGTH = 16


class LoggingConstants:
    """Log dosyası ve format sınırları."""

    MAX_LOG_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
    LOG_BACKUP_COUNT = 5                  # 5 adet dönen yedek dosya
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s"
