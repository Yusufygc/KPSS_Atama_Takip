"""KPSS Atama Takip - Veritabanı ve Kalıcılık İstisnaları."""

from typing import Any, Dict, Optional

from app.core.exceptions.base import KPSSBaseException


class DatabaseException(KPSSBaseException):
    """Veritabanı erişimi veya işlem hataları."""

    http_status = 500

    def __init__(
        self,
        message: str,
        error_code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


class RecordDuplicateException(DatabaseException):
    """İlanın veritabanında zaten kayıtlı olması durumu (SHA-256 hash çakışması)."""

    def __init__(self, hash_id: str) -> None:
        super().__init__(
            message=f"Kayıt zaten mevcut (Hash: {hash_id}).",
            error_code="RECORD_ALREADY_EXISTS",
            details={"hash_id": hash_id},
        )
        self.hash_id = hash_id


class QueryExecutionException(DatabaseException):
    """SQL sorgusu çalıştırılırken oluşan hata."""

    def __init__(self, query: str, original_error: str) -> None:
        super().__init__(
            message="SQL sorgusu çalıştırılamadı.",
            error_code="QUERY_EXECUTION_ERROR",
            details={"query": query[:100], "original_error": original_error},
        )
