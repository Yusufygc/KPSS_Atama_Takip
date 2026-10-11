"""KPSS Atama Takip - Soyut Kazıyıcı Temel Sınıfı (Adapter Pattern)."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional

import httpx

from app.core.constants.settings import NetworkConstants
from app.core.exceptions.scraper import (
    NetworkScraperException,
    RateLimitScraperException,
)
from app.core.logging import ScraperLoggerAdapter, get_scraper_logger
from app.domain.schemas import AnnouncementCreate


class BaseScraper(ABC):
    """Tüm portal kazıyıcılarının uygulaması zorunlu olan soyut temel sınıf."""

    portal_key: str
    portal_name: str
    # TLS sertifikası doğrulaması varsayılan olarak açıktır; yalnızca sertifika zinciri
    # bozuk bir portal için alt sınıfta bilinçli olarak kapatılabilir.
    verify_ssl: ClassVar[bool] = True

    def __init__(self) -> None:
        self.logger: ScraperLoggerAdapter = get_scraper_logger(self.portal_key)

    @abstractmethod
    async def scrape(self) -> List[AnnouncementCreate]:
        """Portaldan en güncel ilanları çeker ve standart DTO listesi döner."""
        pass

    @staticmethod
    def _parse_retry_after(value: Optional[str]) -> int:
        """Retry-After başlığını saniyeye çevirir (sayı değilse varsayılan; üst sınır uygulanır)."""
        try:
            seconds = int(value) if value is not None else NetworkConstants.DEFAULT_RETRY_AFTER_SECONDS
        except ValueError:
            seconds = NetworkConstants.DEFAULT_RETRY_AFTER_SECONDS  # HTTP-date biçimi vb.
        return max(0, min(seconds, NetworkConstants.MAX_RETRY_AFTER_SECONDS))

    async def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        timeout: float = NetworkConstants.TOTAL_TIMEOUT_SECONDS,
        retries: int = NetworkConstants.MAX_RETRIES,
        verify_ssl: Optional[bool] = None,
    ) -> httpx.Response:
        """Hata yönetimi ve yeniden deneme (retry/backoff) içeren güvenli HTTP istemcisi."""
        req_headers = headers or NetworkConstants.DEFAULT_HEADERS.copy()
        verify = self.verify_ssl if verify_ssl is None else verify_ssl
        last_exception: Optional[Exception] = None

        for attempt in range(1, retries + 1):
            try:
                async with httpx.AsyncClient(
                    verify=verify,
                    timeout=httpx.Timeout(timeout),
                    follow_redirects=True,
                ) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=req_headers,
                        params=params,
                        json=json_data,
                        data=form_data,
                    )

                    if response.status_code == 429:
                        retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
                        self.logger.warning(
                            f"İstek limitine takıldı (429). {retry_after} sn bekleniyor..."
                        )
                        if attempt == retries:
                            raise RateLimitScraperException(
                                portal_key=self.portal_key,
                                retry_after=retry_after,
                            )
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status_code in NetworkConstants.RETRY_STATUS_CODES:
                        self.logger.warning(
                            f"Sunucu hatası ({response.status_code}) alındı. Deneme {attempt}/{retries}..."
                        )
                        if attempt == retries:
                            raise NetworkScraperException(
                                message=f"Sunucu hatası: {response.status_code}",
                                portal_key=self.portal_key,
                                status_code=response.status_code,
                                url=url,
                            )
                        await asyncio.sleep(NetworkConstants.RETRY_BACKOFF_FACTOR ** attempt)
                        continue

                    response.raise_for_status()
                    return response

            except httpx.HTTPStatusError as e:
                # Kalıcı istemci hataları (404, 403 vb.) yeniden denemekle düzelmez
                status_code = e.response.status_code
                self.logger.warning(f"HTTP {status_code} alındı, yeniden denenmeyecek: {url}")
                raise NetworkScraperException(
                    message=f"Sunucu hatası: {status_code}",
                    portal_key=self.portal_key,
                    status_code=status_code,
                    url=url,
                ) from e

            except httpx.TimeoutException as e:
                last_exception = e
                self.logger.warning(
                    f"Zaman aşımı ({url}). Deneme {attempt}/{retries}..."
                )
                if attempt == retries:
                    raise NetworkScraperException(
                        message=f"Bağlantı zaman aşımı: {e}",
                        portal_key=self.portal_key,
                        url=url,
                    ) from e
                await asyncio.sleep(NetworkConstants.RETRY_BACKOFF_FACTOR ** attempt)

            except httpx.HTTPError as e:
                last_exception = e
                self.logger.error(f"HTTP isteği başarısız: {e}")
                if attempt == retries:
                    raise NetworkScraperException(
                        message=f"Ağ hatası: {e}",
                        portal_key=self.portal_key,
                        url=url,
                    ) from e
                await asyncio.sleep(NetworkConstants.RETRY_BACKOFF_FACTOR ** attempt)

        raise NetworkScraperException(
            message=f"Tüm denemeler tükendi ({last_exception})",
            portal_key=self.portal_key,
            url=url,
        )
