"""KPSS Atama Takip - Doğrulama ve Veri Bütünlüğü İstisnaları."""

from typing import Any, Dict, Optional
from app.core.exceptions.base import KPSSBaseException


class ValidationException(KPSSBaseException):
    """Gelen verinin kurallara veya şemaya uymaması hatası."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged = {"field": field, **(details or {})}
        super().__init__(
            message=message,
            error_code="VALIDATION_FAILED",
            details=merged,
        )
        self.field = field
