"""KPSS Atama Takip - Hiyerarşik Hata Yönetimi Temel Sınıfı."""

from typing import Any, Dict, Optional


class KPSSBaseException(Exception):
    """Tüm uygulama içi özel istisnaların atası olan temel sınıf."""

    # HTTP durum kodu: istemci hatası (4xx) ile sunucu/altyapı hatasını (5xx) ayırır
    http_status: int = 500

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """İstisnayı API yanıtı veya loglama için sözlüğe çevirir."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        if self.details:
            return f"[{self.error_code}] {self.message} | Detaylar: {self.details}"
        return f"[{self.error_code}] {self.message}"
