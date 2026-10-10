"""KPSS Atama Takip - Kazıyıcı Kayıt Defteri (Factory / Registry Pattern)."""

from typing import Dict, List, Type
from app.core.exceptions.scraper import ScraperException
from app.core.logging import get_logger
from app.scrapers.base import BaseScraper

logger = get_logger("scrapers.registry")


class ScraperRegistry:
    """Tüm portal kazıyıcı adaptörlerini merkezi olarak tescil eden ve yöneten sınıf."""

    _registry: Dict[str, Type[BaseScraper]] = {}

    @classmethod
    def register(cls, scraper_cls: Type[BaseScraper]) -> Type[BaseScraper]:
        """Bir kazıyıcı sınıfını kayıt defterine ekler (Decorator olarak kullanılabilir)."""
        key = getattr(scraper_cls, "portal_key", None)
        if not key:
            raise ValueError(f"{scraper_cls.__name__} sınıfında portal_key tanımlanmamış!")

        cls._registry[key] = scraper_cls
        logger.debug(f"Kazıyıcı tescil edildi: [{key}] -> {scraper_cls.__name__}")
        return scraper_cls

    @classmethod
    def get(cls, portal_key: str) -> BaseScraper:
        """Belirtilen portal_key'e ait kazıyıcı nesnesini üretir (Factory)."""
        if portal_key not in cls._registry:
            raise ScraperException(
                message=f"Kayıtlı olmayan kazıyıcı anahtarı: {portal_key}",
                portal_key=portal_key,
                error_code="SCRAPER_NOT_FOUND",
            )
        scraper_cls = cls._registry[portal_key]
        return scraper_cls()

    @classmethod
    def get_all(cls) -> List[BaseScraper]:
        """Kayıtlı tüm kazayıcıların yeni örneklerini liste olarak döner."""
        return [scraper_cls() for scraper_cls in cls._registry.values()]

    @classmethod
    def get_registered_keys(cls) -> List[str]:
        """Kayıtlı portal anahtarlarının listesini döner."""
        return list(cls._registry.keys())
