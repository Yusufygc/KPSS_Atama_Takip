"""KPSS Atama Takip - KPSS Puan Türü Eşleştirme ve Öncelik Stratejisi."""

import re
from typing import List, Pattern, Tuple

from app.core.text import turkish_upper
from app.domain.models import PriorityLevel, ScoreType

# Anahtar kelime başlangıcında harf/rakam bulunmamalı: "4/B" ifadesi "2024/B" içinde,
# "MİMAR" ifadesi kelime ortasında eşleşmesin. Sonek serbesttir (MÜHENDİS -> MÜHENDİSİ / MÜHENDİSLİĞİ).
_WORD_START = r"(?<![A-ZÇĞİÖŞÜ0-9])"


def _keyword_patterns(keywords: List[str]) -> List[Pattern[str]]:
    return [re.compile(_WORD_START + re.escape(kw)) for kw in keywords]


def _score_pattern(label: str) -> Pattern[str]:
    """P1/P2/P3 için açık yazım biçimlerini yakalar: KPSS P3, KPSSP3, KPSS-P3, KPSS (P3), P-3, P3 puan."""
    n = label[1]
    return re.compile(
        rf"KPSS[\s\-:(]*P\s*-?\s*{n}(?!\d)"  # KPSS P3 / KPSSP3 / KPSS-P3 / KPSS (P3) / KPSS P-3
        rf"|{_WORD_START}P\s*-?\s*{n}\s*(?:PUAN|\))"  # P3 puan / (P3)
        rf"|{_WORD_START}P-{n}(?!\d)"  # P-3
    )


class KPSSScoreMatcher:
    """İlan metninden (başlık, kurum, unvan) KPSS puan türünü ve önceliğini tespit eden strateji motoru."""

    # Açıkça belirtilen puan kalıpları (metin büyük harfe çevrildikten sonra aranır)
    P3_REGEX = _score_pattern("P3")
    P1_REGEX = _score_pattern("P1")
    P2_REGEX = _score_pattern("P2")

    # KPSS puanıyla alınmayan ilan türleri: akademik kadro (ALES / ilan şartları ayrı) ve işçi alımları.
    # Bu ifadeler varsa ilan örtük (unvan bazlı) olarak P1/P2/P3 sayılmaz.
    NON_KPSS_KEYWORDS = [
        "ÖĞRETİM ÜYESİ",
        "ÖĞRETİM GÖREVLİSİ",
        "ARAŞTIRMA GÖREVLİSİ",
        "DOKTOR ÖĞRETİM",
        "PROFESÖR",
        "DOÇENT",
        "DOÇ. DR",
        "DR. ÖĞR",
        "SÜREKLİ İŞÇİ",
        "GEÇİCİ İŞÇİ",
        "İŞÇİ ALIMI",
    ]

    # P3 ile doğrudan ilişkili B Grubu Lisans unvan ve anahtar kelimeleri
    P3_KEYWORDS = [
        "MÜHENDİS",
        "BİLİŞİM PERSONELİ",
        "PROGRAMCI",
        "ÇÖZÜMLEYİCİ",
        "SİSTEM YÖNETİCİSİ",
        "YAZILIM",
        "BÜRO PERSONELİ",
        "VHKİ",
        "VERİ HAZIRLAMA",
        "ZABITA MEMURU",
        "İTFAİYE ERİ",
        "AVUKAT",
        "MİMAR",
        "ŞEHİR PLANCISI",
        "İSTATİSTİKÇİ",
        "KÜTÜPHANECİ",
        "PSİKOLOG",
        "SOSYOLOG",
        "SÖZLEŞMELİ PERSONEL",
        "LİSANS DÜZEYİ",
        "LİSANS MEZUNU",
    ]
    # Rakam içeren kalıplar: "4/B", "4-B", "4 / B" (ancak "2024/B" değil)
    P3_EXTRA_PATTERNS = [re.compile(_WORD_START + r"4\s*[/\-]\s*B(?![A-ZÇĞİÖŞÜ])")]

    # P1 ve P2 ile ilişkili A Grubu Kariyer unvan ve anahtar kelimeleri
    CAREER_P1_P2_KEYWORDS = [
        "UZMAN YARDIMCISI",
        "UZMAN YARDIMCILIĞI",
        "MÜFETTİŞ YARDIMCISI",
        "MÜFETTİŞ YARDIMCILIĞI",
        "DENETÇİ YARDIMCISI",
        "DENETMEN YARDIMCISI",
        "MESLEK PERSONELİ",
        "KALKINMA AJANSI",
        "STAJYER KONTROLÖR",
        "YARIŞMA SINAVI",
        "GİRİŞ SINAVI",
        "A GRUBU",
    ]

    _NON_KPSS_PATTERNS = _keyword_patterns(NON_KPSS_KEYWORDS)
    _P3_PATTERNS = _keyword_patterns(P3_KEYWORDS) + P3_EXTRA_PATTERNS
    _CAREER_PATTERNS = _keyword_patterns(CAREER_P1_P2_KEYWORDS)

    @classmethod
    def match(
        cls,
        title: str,
        institution: str = "",
        raw_content: str = "",
    ) -> Tuple[List[ScoreType], PriorityLevel]:
        """Verilen metinleri analiz ederek eşleşen puan türlerini ve öncelik seviyesini döner."""
        full_text = turkish_upper(f"{title} {institution} {raw_content}")
        matched_scores: List[ScoreType] = []

        # 1. Açık (Explicit) Puan Kontrolü: ilan puan türünü kendisi yazıyorsa her zaman geçerlidir
        if cls.P3_REGEX.search(full_text):
            matched_scores.append(ScoreType.P3)
        if cls.P1_REGEX.search(full_text):
            matched_scores.append(ScoreType.P1)
        if cls.P2_REGEX.search(full_text):
            matched_scores.append(ScoreType.P2)

        # 2. Örtük (Implicit / Unvan Bazlı) Kontrol: akademik kadro ve işçi ilanları hariç
        if not matched_scores and not any(p.search(full_text) for p in cls._NON_KPSS_PATTERNS):
            if any(p.search(full_text) for p in cls._P3_PATTERNS):
                matched_scores.append(ScoreType.P3)
            if any(p.search(full_text) for p in cls._CAREER_PATTERNS):
                matched_scores.extend([ScoreType.P1, ScoreType.P2])

        # Eğer hiçbiri bulunamadıysa genel kadro
        if not matched_scores:
            matched_scores.append(ScoreType.GENERAL)

        # 3. Öncelik Seviyesi Belirleme (Kullanıcının 1. önceliği P3)
        if ScoreType.P3 in matched_scores:
            priority = PriorityLevel.PRIORITY_P3      # Öncelik 3 (En Yüksek)
        elif ScoreType.P1 in matched_scores or ScoreType.P2 in matched_scores:
            priority = PriorityLevel.CAREER_P1_P2    # Öncelik 2 (Kariyer)
        else:
            priority = PriorityLevel.NORMAL          # Öncelik 1 (Normal)

        return matched_scores, priority
