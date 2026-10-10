"""KPSS Atama Takip - Bilgisayar Mühendisliği ve Bilişim / Yazılım Alan Eşleştirme Motoru."""

from enum import Enum
import re
import unicodedata
from typing import List, Tuple


class ITSubField(str, Enum):
    """Bilişim ve Bilgisayar Mühendisliği alt uzmanlık alanları."""

    COMPUTER_ENGINEERING = "Bilgisayar Mühendisliği"
    SOFTWARE = "Yazılım & Web"
    CYBER_SECURITY = "Siber Güvenlik"
    CONTRACTED_IT = "Sözleşmeli Bilişim (SBP)"
    NETWORK_SYSTEM = "Ağ & Sistem"
    DATA_AI = "Veri & Yapay Zeka"
    GENERAL_IT = "Bilişim & Bilgi İşlem"


def _normalize_text(text: str) -> str:
    """Türkçe karakterleri ve Unicode varyasyonlarını karşılaştırma için normalize eder."""
    if not text:
        return ""
    # Türkçe büyük harf dönüşümü
    t = text.replace("i", "İ").replace("ı", "I").upper()
    return t


class ITFieldMatcher:
    """İlan başlığı, kurum ve içeriğinden Bilgisayar Mühendisliği ve Bilişim branşlarını tespit eden motor."""

    # Her alt alan için regex desenleri
    PATTERNS: List[Tuple[ITSubField, List[str]]] = [
        (
            ITSubField.COMPUTER_ENGINEERING,
            [
                r"BİLGİSAYAR\s*MÜHENDİS",
                r"BILGISAYAR\s*MUHENDIS",
                r"BİLGİSAYAR\s*MÜHENDİSLİĞİ",
                r"BİLGİSAYAR\s*BİLİMLERİ",
                r"BİLGİSAYAR\s*PROGRAM",
                r"BİLGİSAYAR\s*TEKNOLOJİ",
            ],
        ),
        (
            ITSubField.SOFTWARE,
            [
                r"YAZILIM",
                r"PROGRAMCI",
                r"ÇÖZÜMLEYİCİ",
                r"COZUMLEYICI",
                r"FRONTEND",
                r"BACKEND",
                r"FULL\s*STACK",
                r"MOBİL\s*(GELİŞTİRİCİ|YAZILIM)",
                r"WEB\s*(GELİŞTİRİCİ|TASARIM|YAZILIM)",
                r"KODLAMA",
                r"YAZILIM\s*(GELİŞTİRİCİ|MÜHENDİS|UZMAN)",
            ],
        ),
        (
            ITSubField.CYBER_SECURITY,
            [
                r"SİBER",
                r"SIBER",
                r"BİLGİ\s*GÜVENLİĞİ",
                r"ADLİ\s*BİLİŞİM",
                r"PENETRASYON",
                r"SIZMA\s*TEST",
                r"SOC\s*ANALİST",
                r"ZAFİYET",
                r"KRİPTOGRAFİ",
            ],
        ),
        (
            ITSubField.CONTRACTED_IT,
            [
                r"SÖZLEŞMELİ\s*BİLİŞİM",
                r"SOZLESMELI\s*BILISIM",
                r"BİLİŞİM\s*PERSONELİ",
                r"BILISIM\s*PERSONELI",
                r"\bSBP\b",
                r"375\s*SAYILI\s*KHK",
            ],
        ),
        (
            ITSubField.NETWORK_SYSTEM,
            [
                r"SİSTEM\s*YÖNETİCİ",
                r"AĞ\s*YÖNETİCİ",
                r"AĞ\s*VE\s*SİSTEM",
                r"NETWORK\s*UZMAN",
                r"\bDEVOPS\b",
                r"BULUT\s*BİLİŞİM",
                r"\bCLOUD\b",
                r"VERİ\s*MERKEZİ",
                r"SUNUCU\s*YÖNETİCİ",
            ],
        ),
        (
            ITSubField.DATA_AI,
            [
                r"VERİ\s*TABANI",
                r"VERİTABANI",
                r"VERİ\s*ANALİST",
                r"VERİ\s*BİLİMCİ",
                r"YAPAY\s*ZEKA",
                r"MAKİNE\s*ÖĞRENMESİ",
                r"BÜYÜK\s*VERİ",
                r"BIG\s*DATA",
                r"\bDBA\b",
                r"İŞ\s*ZEKASI",
            ],
        ),
        (
            ITSubField.GENERAL_IT,
            [
                r"BİLGİ\s*İŞLEM",
                r"BİLİŞİM\s*UZMAN",
                r"BİLİŞİM\s*TEKNOLOJİ",
                r"BİLGİ\s*TEKNOLOJİ",
            ],
        ),
    ]

    # Derlenmiş regex listesi (Performans için ön derleme)
    _COMPILED_PATTERNS = [
        (subfield, [re.compile(p, re.IGNORECASE) for p in patterns])
        for subfield, patterns in PATTERNS
    ]

    @classmethod
    def match_tags(
        cls,
        title: str,
        institution: str = "",
        position: str = "",
        raw_content: str = "",
    ) -> List[str]:
        """İlan metinlerini tarayarak ilgili Bilişim / Bilgisayar Mühendisliği etiketlerini döner."""
        full_text = _normalize_text(f"{title} {institution} {position} {raw_content}")
        matched_tags: List[str] = []

        for subfield, regexes in cls._COMPILED_PATTERNS:
            for rx in regexes:
                if rx.search(full_text):
                    matched_tags.append(subfield.value)
                    break

        return matched_tags

    @classmethod
    def is_it_announcement(
        cls,
        title: str = "",
        institution: str = "",
        position: str = "",
        raw_content: str = "",
        tags: List[str] = None,
    ) -> bool:
        """İlanın Bilgisayar Mühendisliği / Bilişim ile ilgili olup olmadığını döner."""
        if tags is not None:
            return len(tags) > 0
        return len(cls.match_tags(title, institution, position, raw_content)) > 0
