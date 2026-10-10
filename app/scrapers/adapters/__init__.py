"""KPSS Atama Takip - Kazıyıcı Adaptörleri Paketi."""

# Otomatik tescil için tüm adaptörleri içe aktar
from app.scrapers.adapters.kariyer_kapisi import KariyerKapisiScraper
from app.scrapers.adapters.resmi_gazete import ResmiGazeteScraper
from app.scrapers.adapters.kamu_ilan import KamuIlanSbbScraper
from app.scrapers.adapters.yerel_yonetimler import YerelYonetimlerScraper
from app.scrapers.adapters.iskur import IskurScraper
from app.scrapers.adapters.ilan_gov_tr import IlanGovTrScraper

__all__ = [
    "KariyerKapisiScraper",
    "ResmiGazeteScraper",
    "KamuIlanSbbScraper",
    "YerelYonetimlerScraper",
    "IskurScraper",
    "IlanGovTrScraper",
]
