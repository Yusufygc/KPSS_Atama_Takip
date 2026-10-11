"""KPSS Atama Takip - Sistem ve Entegrasyon Ayarları REST Uç Noktaları."""

from fastapi import APIRouter

from app.api.dependencies import TelegramNotifierDep
from app.api.security import ApiKeyDep
from app.config import settings

router = APIRouter(prefix="/settings", tags=["Ayarlar"], dependencies=[ApiKeyDep])


def _mask(value: str) -> str:
    """Hassas değeri ilk ve son 2 karakter dışında maskeler."""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:2]}...{value[-2:]}"


@router.get("", response_model=dict)
async def get_current_settings(notifier: TelegramNotifierDep):
    """Mevcut yapılandırma özetini döner (Token ve Chat ID maskelenir)."""
    return {
        "app_env": settings.APP_ENV,
        "scraper_interval_minutes": settings.SCRAPER_INTERVAL_MINUTES,
        "telegram_configured": notifier.is_configured,
        "telegram_enabled": notifier.is_enabled,
        "telegram_chat_id_masked": _mask(settings.TELEGRAM_CHAT_ID),
        "telegram_token_masked": _mask(settings.TELEGRAM_BOT_TOKEN),
    }


@router.post("/telegram/test", response_model=dict)
async def test_telegram_connection(notifier: TelegramNotifierDep):
    """Telegram botuna test mesajı göndererek bağlantıyı doğrular."""
    if not notifier.is_configured:
        return {
            "success": False,
            "message": "Telegram Bot Token veya Chat ID henüz .env dosyasında yapılandırılmamış.",
        }

    success = await notifier.test_connection()
    return {
        "success": success,
        "message": (
            "Telegram test mesajı başarıyla iletildi!"
            if success
            else "Telegram mesajı gönderilemedi. Token ve Chat ID'yi kontrol ediniz."
        ),
    }
