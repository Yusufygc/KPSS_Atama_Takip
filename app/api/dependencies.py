"""KPSS Atama Takip - FastAPI Bağımlılık Enjeksiyonu (Dependency Injection)."""

from typing import Annotated

from fastapi import Depends

from app.infrastructure.database.repository import AnnouncementRepository
from app.infrastructure.notification.telegram import TelegramNotifier
from app.scrapers.orchestrator import ScraperOrchestrator
from app.services.announcement_service import AnnouncementService

# Paylaşılan tekil servis örnekleri
_repository = AnnouncementRepository()
_orchestrator = ScraperOrchestrator()
_notifier = TelegramNotifier()
_service = AnnouncementService(
    repository=_repository,
    orchestrator=_orchestrator,
    notifier=_notifier,
)


def get_announcement_service() -> AnnouncementService:
    """İlan iş mantığı servisini sağlar."""
    return _service


def get_telegram_notifier() -> TelegramNotifier:
    """Telegram bildirim servisini sağlar."""
    return _notifier


AnnouncementServiceDep = Annotated[AnnouncementService, Depends(get_announcement_service)]
TelegramNotifierDep = Annotated[TelegramNotifier, Depends(get_telegram_notifier)]
