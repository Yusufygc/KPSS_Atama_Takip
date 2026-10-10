"""KPSS Atama Takip - Merkezi İstisnalar Paketi."""

from app.core.exceptions.base import KPSSBaseException
from app.core.exceptions.scraper import (
    ScraperException,
    NetworkScraperException,
    ParsingScraperException,
    RateLimitScraperException,
)
from app.core.exceptions.database import (
    DatabaseException,
    RecordDuplicateException,
    QueryExecutionException,
)
from app.core.exceptions.notification import (
    NotificationException,
    TelegramDeliveryException,
)
from app.core.exceptions.validation import ValidationException

__all__ = [
    "KPSSBaseException",
    "ScraperException",
    "NetworkScraperException",
    "ParsingScraperException",
    "RateLimitScraperException",
    "DatabaseException",
    "RecordDuplicateException",
    "QueryExecutionException",
    "NotificationException",
    "TelegramDeliveryException",
    "ValidationException",
]
