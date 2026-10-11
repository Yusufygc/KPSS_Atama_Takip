"""KPSS Atama Takip - Yönetim Uç Noktaları İçin API Anahtarı Doğrulaması."""

import secrets
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from app.config import settings
from app.core.constants.strings import ErrorStrings
from app.core.logging import get_logger

logger = get_logger("api.security")

API_KEY_HEADER = "X-API-Key"


async def require_api_key(
    x_api_key: Annotated[Optional[str], Header(alias=API_KEY_HEADER)] = None,
) -> None:
    """Hassas uç noktalar için X-API-Key başlığını sabit sürede doğrular."""
    configured = settings.API_KEY
    if not configured:
        if settings.is_production:
            logger.error(ErrorStrings.API_KEY_NOT_CONFIGURED)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ErrorStrings.API_KEY_NOT_CONFIGURED,
            )
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorStrings.API_KEY_INVALID,
        )


ApiKeyDep = Depends(require_api_key)
