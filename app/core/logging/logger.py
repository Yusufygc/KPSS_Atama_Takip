"""KPSS Atama Takip - Detaylı ve Yapılandırılmış Loglama Sistemi."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.config import settings
from app.core.constants.settings import LoggingConstants


class UTF8RotatingFileHandler(RotatingFileHandler):
    """Windows sistemlerinde Türkçe karakter bozulmasını engelleyen UTF-8 FileHandler."""

    def __init__(self, filename: Path, **kwargs) -> None:
        super().__init__(filename=str(filename), encoding="utf-8", **kwargs)


def setup_root_logger() -> logging.Logger:
    """Kök loglayıcıyı konsol ve dönen dosya (rotating file) işleyicileriyle yapılandırır."""
    root_logger = logging.getLogger("kpss")
    
    # Çoklu başlatmayı önle
    if root_logger.handlers:
        return root_logger

    log_level = logging.DEBUG if settings.APP_DEBUG else logging.INFO
    root_logger.setLevel(log_level)

    # 1. Log dizinini garanti et
    logs_dir = settings.LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = logs_dir / "app.log"

    # 2. Standart Formatlayıcı
    formatter = logging.Formatter(
        fmt=LoggingConstants.LOG_FORMAT,
        datefmt=LoggingConstants.LOG_DATE_FORMAT,
    )

    # 3. Konsol İşleyicisi (Console StreamHandler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 4. Dönen Dosya İşleyicisi (Rotating File Handler)
    file_handler = UTF8RotatingFileHandler(
        filename=log_file_path,
        maxBytes=LoggingConstants.MAX_LOG_FILE_BYTES,
        backupCount=LoggingConstants.LOG_BACKUP_COUNT,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


def get_logger(module_name: Optional[str] = None) -> logging.Logger:
    """Belirtilen modül adına bağlı alt loglayıcı örneği döner."""
    setup_root_logger()
    if module_name:
        return logging.getLogger(f"kpss.{module_name}")
    return logging.getLogger("kpss")


class ScraperLoggerAdapter(logging.LoggerAdapter):
    """Kazıyıcı modüllerine özel bağlamsal loglayıcı (Context Adapter)."""

    def process(self, msg, kwargs):
        portal = self.extra.get("portal", "Genel")
        return f"[{portal}] {msg}", kwargs


def get_scraper_logger(portal_name: str) -> ScraperLoggerAdapter:
    """Portal adına özel bağlam etiketli loglayıcı döner."""
    base_logger = get_logger(f"scrapers.{portal_name}")
    return ScraperLoggerAdapter(base_logger, {"portal": portal_name})
