"""KPSS Atama Takip - Tarih Ayrıştırma ve Normalizasyon Yardımcıları.

Portallar son başvuru tarihini farklı biçimlerde döner:
  * İŞKUR:           "13.10.2026"
  * Kariyer Kapısı:  "2026-10-22T23:59:00"
  * Kamu İlan (SBB): "12 Ekim - 26 Ekim" (yılsız aralık; bitiş tarihi son başvurudur)
  * Yerel Yönetimler: "09 Ekim 2026"
Bu modül hepsini tek bir `date` değerine (ISO: YYYY-MM-DD) indirger.
"""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.core.text import fold_turkish

# Türkiye'de yaz/kış saati uygulaması yoktur (sabit UTC+3)
TURKEY_TZ = timezone(timedelta(hours=3))

_MONTHS = {
    "ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6,
    "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12,
}  # fold_turkish çıktısıyla karşılaştırılır (ş->s, ı->i, ü->u, ğ->g)

_ISO_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_DOTTED_RE = re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](\d{4})(?!\d)")
_TEXT_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s+(" + "|".join(_MONTHS) + r")[a-z]*(?:\s+(\d{4}))?(?!\d)"
)

# Yılsız tarihlerde, referans tarihten bu kadar gün geride kalan tarih "gelecek yıl" sayılır
_YEARLESS_LOOKBACK_DAYS = 180


def today_in_turkey() -> date:
    """Türkiye saatine göre bugünün tarihini döner."""
    return datetime.now(TURKEY_TZ).date()


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _infer_year(month: int, day: int, reference: date) -> Optional[date]:
    """Yılsız gün/ay için referans tarihe göre en makul yılı seçer (yıl sonu aralıklarını da kapsar)."""
    candidate = _safe_date(reference.year, month, day)
    if candidate is None:
        return None
    if (reference - candidate).days > _YEARLESS_LOOKBACK_DAYS:
        return _safe_date(reference.year + 1, month, day)
    return candidate


def parse_deadline(raw: Optional[str], reference: Optional[date] = None) -> Optional[date]:
    """Serbest metin son başvuru tarihini `date` değerine çevirir; ayrıştırılamazsa None döner.

    Birden fazla tarih içeren aralıklarda ("12 Ekim - 26 Ekim") SON tarih alınır.
    `reference`: yılsız tarihlerde yıl çıkarımı için kullanılan tarih (varsayılan: bugün, TRT).
    """
    if not raw or not raw.strip():
        return None
    reference = reference or today_in_turkey()

    iso = _ISO_RE.findall(raw)
    if iso:
        year, month, day = (int(x) for x in iso[-1])
        return _safe_date(year, month, day)

    dotted = _DOTTED_RE.findall(raw)
    if dotted:
        day, month, year = (int(x) for x in dotted[-1])
        return _safe_date(year, month, day)

    text_matches = list(_TEXT_RE.finditer(fold_turkish(raw)))
    if text_matches:
        match = text_matches[-1]
        day, month = int(match.group(1)), _MONTHS[match.group(2)]
        if match.group(3):
            return _safe_date(int(match.group(3)), month, day)
        return _infer_year(month, day, reference)

    return None


def parse_deadline_iso(raw: Optional[str], reference: Optional[date] = None) -> Optional[str]:
    """parse_deadline sonucunu ISO (YYYY-MM-DD) metin olarak döner."""
    parsed = parse_deadline(raw, reference)
    return parsed.isoformat() if parsed else None


def day_of_timestamp(timestamp: Optional[str]) -> Optional[date]:
    """ISO zaman damgasından (created_at) günü döner; hatalı/boşsa None (çağıran bugünü kullanır)."""
    try:
        return datetime.fromisoformat(timestamp).date() if timestamp else None
    except (TypeError, ValueError):
        return None
