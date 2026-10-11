"""KPSS Atama Takip - Merkezi İstisnalar Paketi."""

from app.core.exceptions.base import KPSSBaseException
from app.core.exceptions.database import (
    DatabaseException,
    QueryExecutionException,
    RecordDuplicateException,
)
from app.core.exceptions.notification import (
    NotificationException,
    TelegramDeliveryException,
)
from app.core.exceptions.scraper import (
    NetworkScraperException,
    ParsingScraperException,
    RateLimitScraperException,
    ScrapeInProgressException,
    ScraperException,
)
from app.core.exceptions.validation import ValidationException

__all__ = [
    "KPSSBaseException",
    "ScraperException",
    "NetworkScraperException",
    "ParsingScraperException",
    "RateLimitScraperException",
    "ScrapeInProgressException",
    "DatabaseException",
    "RecordDuplicateException",
    "QueryExecutionException",
    "NotificationException",
    "TelegramDeliveryException",
    "ValidationException",
]
