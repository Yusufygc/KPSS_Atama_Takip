"""KPSS Atama Takip - API Yönlendiricileri."""

from app.api.routes.announcements import router as announcements_router
from app.api.routes.scrapers import router as scrapers_router
from app.api.routes.settings import router as settings_router

__all__ = ["announcements_router", "scrapers_router", "settings_router"]
