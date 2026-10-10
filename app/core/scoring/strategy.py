"""KPSS Atama Takip - KPSS Puan Türü Eşleştirme ve Öncelik Stratejisi."""

import re
from typing import List, Tuple
from app.domain.models import PriorityLevel, ScoreType


class KPSSScoreMatcher:
    """İlan metninden (başlık, kurum, unvan) KPSS puan türünü ve önceliğini tespit eden strateji motoru."""

    # Açıkça belirtilen puan kalıpları (Regex)
    P3_REGEX = re.compile(r"\b(KPSS\s*P\s*3|KPSSP3|P3\s*PUAN|P-3)\b", re.IGNORECASE)
    P1_REGEX = re.compile(r"\b(KPSS\s*P\s*1|KPSSP1|P1\s*PUAN|P-1)\b", re.IGNORECASE)
    P2_REGEX = re.compile(r"\b(KPSS\s*P\s*2|KPSSP2|P2\s*PUAN|P-2)\b", re.IGNORECASE)

    # P3 ile doğrudan ilişkili B Grubu Lisans unvan ve anahtar kelimeleri
    P3_KEYWORDS = [
        "MÜHENDİS",
        "MÜHENDİSLİĞİ",
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
        "4/B",
        "4-B",
        "SÖZLEŞMELİ PERSONEL",
        "LİSANS DÜZEYİ",
        "LİSANS MEZUNU",
    ]

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

    @classmethod
    def match(
        cls,
        title: str,
        institution: str = "",
        raw_content: str = "",
    ) -> Tuple[List[ScoreType], PriorityLevel]:
        """Verilen metinleri analiz ederek eşleşen puan türlerini ve öncelik seviyesini döner."""
        full_text = f"{title} {institution} {raw_content}".upper()
        matched_scores: List[ScoreType] = []

        # 1. Açık (Explicit) Puan Kontrolü
        has_explicit_p3 = bool(cls.P3_REGEX.search(full_text))
        has_explicit_p1 = bool(cls.P1_REGEX.search(full_text))
        has_explicit_p2 = bool(cls.P2_REGEX.search(full_text))

        if has_explicit_p3:
            matched_scores.append(ScoreType.P3)
        if has_explicit_p1:
            matched_scores.append(ScoreType.P1)
        if has_explicit_p2:
            matched_scores.append(ScoreType.P2)

        # 2. Örtük (Implicit / Unvan Bazlı) Kontrol
        if not matched_scores:
            has_p3_kw = any(kw in full_text for kw in cls.P3_KEYWORDS)
            has_career_kw = any(kw in full_text for kw in cls.CAREER_P1_P2_KEYWORDS)

            if has_p3_kw:
                matched_scores.append(ScoreType.P3)
            if has_career_kw:
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
