"""KPSS Atama Takip - Bildirim ve Dağıtım İstisnaları."""

from typing import Any, Dict, Optional

from app.core.exceptions.base import KPSSBaseException


class NotificationException(KPSSBaseException):
    """Bildirim kanalları genel hatası."""

    http_status = 502

    def __init__(
        self,
        message: str,
        channel: str = "telegram",
        error_code: str = "NOTIFICATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged = {"channel": channel, **(details or {})}
        super().__init__(message=message, error_code=error_code, details=merged)
        self.channel = channel


class TelegramDeliveryException(NotificationException):
    """Telegram Bot API ile mesaj gönderilirken oluşan hata."""

    def __init__(self, original_error: str, chat_id: Optional[str] = None) -> None:
        super().__init__(
            message=f"Telegram mesajı iletilemedi: {original_error}",
            channel="telegram",
            error_code="TELEGRAM_DELIVERY_FAILED",
            details={"chat_id": chat_id, "error": original_error},
        )
