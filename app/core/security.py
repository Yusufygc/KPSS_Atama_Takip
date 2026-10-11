"""KPSS Atama Takip - Güvenlik Yardımcıları (URL doğrulama, HTML kaçışlama)."""

import html
from typing import Iterable
from urllib.parse import urlparse

ALLOWED_URL_SCHEMES = ("http", "https")


def is_http_url(url: str | None) -> bool:
    """URL'nin http/https şemasına ve bir host'a sahip olup olmadığını döner."""
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    return parsed.scheme.lower() in ALLOWED_URL_SCHEMES and bool(parsed.hostname)


def host_in_domains(url: str | None, domains: Iterable[str]) -> bool:
    """URL'nin host'unun izin verilen alan adlarından biri (veya alt alan adı) olup olmadığını döner.

    Alt dize kontrolünün (`"example.com" in url`) aksine yalnızca ayrıştırılmış
    host üzerinden karşılaştırma yapar; `https://evil.test/?example.com` geçmez.
    """
    if not is_http_url(url):
        return False
    hostname = (urlparse(url.strip()).hostname or "").lower()
    return any(hostname == d or hostname.endswith(f".{d}") for d in (x.lower() for x in domains))


def escape_html(value: str | None) -> str:
    """Telegram HTML parse_mode için metni kaçışlar (tırnaklar dahil, öznitelik güvenli)."""
    return html.escape(value or "", quote=True)
