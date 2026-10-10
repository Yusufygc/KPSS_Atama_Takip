"""KPSS Atama Takip - Kazıyıcı (Scraper) Katmanı İstisnaları."""

from typing import Any, Dict, Optional
from app.core.exceptions.base import KPSSBaseException


class ScraperException(KPSSBaseException):
    """Kazıyıcı işlemlerinde meydana gelen genel hata."""

    def __init__(
        self,
        message: str,
        portal_key: str,
        error_code: str = "SCRAPER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged_details = {"portal_key": portal_key, **(details or {})}
        super().__init__(message=message, error_code=error_code, details=merged_details)
        self.portal_key = portal_key


class NetworkScraperException(ScraperException):
    """Ağ bağlantısı, zaman aşımı veya HTTP durum kodu hataları."""

    def __init__(
        self,
        message: str,
        portal_key: str,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            portal_key=portal_key,
            error_code="SCRAPER_NETWORK_ERROR",
            details={"status_code": status_code, "url": url},
        )
        self.status_code = status_code
        self.url = url


class ParsingScraperException(ScraperException):
    """HTML veya JSON yanıtının beklenen şablonla uyuşmaması / ayrıştırma hatası."""

    def __init__(
        self,
        message: str,
        portal_key: str,
        raw_snippet: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            portal_key=portal_key,
            error_code="SCRAPER_PARSING_ERROR",
            details={"snippet": raw_snippet[:200] if raw_snippet else None},
        )


class RateLimitScraperException(ScraperException):
    """Hedef portalın istek hızını sınırlandırması durumu (HTTP 429)."""

    def __init__(
        self,
        portal_key: str,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(
            message="Portal istek limiti aşıldı (Rate limit).",
            portal_key=portal_key,
            error_code="SCRAPER_RATE_LIMIT",
            details={"retry_after_seconds": retry_after},
        )
        self.retry_after = retry_after
