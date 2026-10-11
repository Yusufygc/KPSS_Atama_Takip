"""KPSS Atama Takip - Şehir / İl Tespit ve Normalizasyon Motoru.

İlan metni, kurum unvanı ve mevcut şehir verisinden Türkiye'nin 81 ili,
üniversiteleri, merkezi kamu teşkilatları ve ilçeleri üzerinden il tespiti yapar.
"""

import re
from typing import Dict, List, Optional, Tuple

from app.core.text import turkish_upper


def _normalize_turkish(text: str) -> str:
    """Türkçe karakterleri büyük harf ve arama için normalize eder."""
    return turkish_upper(text)


class CityMatcher:
    """Kamu ilanlarından il/şehir tespit eden kural motoru."""

    TURKIYE_GENELI = "Türkiye Geneli"

    # Türkiye'nin 81 İli
    PROVINCES: List[str] = [
        "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin",
        "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
        "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan",
        "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta",
        "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
        "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla",
        "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop",
        "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van",
        "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak",
        "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
    ]

    # İl Adı Taşımayan Tanınmış Devlet Üniversiteleri -> İl Eşleştirmesi
    UNIVERSITY_MAPPING: Dict[str, str] = {
        "ATATÜRK ÜNİVERSİTESİ": "Erzurum",
        "HACETTEPE ÜNİVERSİTESİ": "Ankara",
        "ORTA DOĞU TEKNİK ÜNİVERSİTESİ": "Ankara",
        "ODTÜ": "Ankara",
        "GAZİ ÜNİVERSİTESİ": "Ankara",
        "BOĞAZİÇİ ÜNİVERSİTESİ": "İstanbul",
        "MARMARA ÜNİVERSİTESİ": "İstanbul",
        "İSTANBUL TEKNİK ÜNİVERSİTESİ": "İstanbul",
        "İTÜ": "İstanbul",
        "YILDIZ TEKNİK ÜNİVERSİTESİ": "İstanbul",
        "GALATASARAY ÜNİVERSİTESİ": "İstanbul",
        "EGE ÜNİVERSİTESİ": "İzmir",
        "DOKUZ EYLÜL ÜNİVERSİTESİ": "İzmir",
        "ÇUKUROVA ÜNİVERSİTESİ": "Adana",
        "AKDENİZ ÜNİVERSİTESİ": "Antalya",
        "ERCİYES ÜNİVERSİTESİ": "Kayseri",
        "SELÇUK ÜNİVERSİTESİ": "Konya",
        "NECMETTİN ERBAKAN": "Konya",
        "FIRAT ÜNİVERSİTESİ": "Elazığ",
        "DİCLE ÜNİVERSİTESİ": "Diyarbakır",
        "İNÖNÜ ÜNİVERSİTESİ": "Malatya",
        "ONDOKUZ MAYIS ÜNİVERSİTESİ": "Samsun",
        "KARADENİZ TEKNİK ÜNİVERSİTESİ": "Trabzon",
        "KTÜ": "Trabzon",
        "ANADOLU ÜNİVERSİTESİ": "Eskişehir",
        "OSMANGAZİ ÜNİVERSİTESİ": "Eskişehir",
        "KAFKAS ÜNİVERSİTESİ": "Kars",
        "TRAKYA ÜNİVERSİTESİ": "Edirne",
        "PAMUKKALE ÜNİVERSİTESİ": "Denizli",
        "SÜLEYMAN DEMİREL ÜNİVERSİTESİ": "Isparta",
        "GEBZE TEKNİK ÜNİVERSİTESİ": "Kocaeli",
        "RECEP TAYYİP ERDOĞAN ÜNİVERSİTESİ": "Rize",
        "HARRAN ÜNİVERSİTESİ": "Şanlıurfa",
        "MUSTAFA KEMAL ÜNİVERSİTESİ": "Hatay",
        "CELAL BAYAR ÜNİVERSİTESİ": "Manisa",
        "ADNAN MENDERES ÜNİVERSİTESİ": "Aydın",
        "BÜLENT ECEVİT ÜNİVERSİTESİ": "Zonguldak",
        "AHİ EVRAN ÜNİVERSİTESİ": "Kırşehir",
        "MEHMET AKİF ERSOY ÜNİVERSİTESİ": "Burdur",
        "NAMIK KEMAL ÜNİVERSİTESİ": "Tekirdağ",
        "ABANT İZZET BAYSAL": "Bolu",
        "BOZOK ÜNİVERSİTESİ": "Yozgat",
        "KORU KAMPÜSÜ": "Ankara"
    }

    # Öne Çıkan İlçeler -> İl Eşleştirmesi
    DISTRICT_MAPPING: Dict[str, str] = {
        "ELEŞKİRT": "Ağrı",
        "DOĞUBAYAZIT": "Ağrı",
        "PATNOS": "Ağrı",
        "İNEBOLU": "Kastamonu",
        "TOSYA": "Kastamonu",
        "MELİKGAZİ": "Kayseri",
        "KOCASİNAN": "Kayseri",
        "TALAS": "Kayseri",
        "MARMARİS": "Muğla",
        "BODRUM": "Muğla",
        "FETHİYE": "Muğla",
        "SARIYER": "İstanbul",
        "KADIKÖY": "İstanbul",
        "ÜSKÜDAR": "İstanbul",
        "BEŞİKTAŞ": "İstanbul",
        "FATİH": "İstanbul",
        "ÇANKAYA": "Ankara",
        "KEÇİÖREN": "Ankara",
        "YENİMAHALLE": "Ankara",
        "MAMAK": "Ankara",
        "ETİMESGUT": "Ankara",
        "SİNCAN": "Ankara",
        "ALTINDAĞ": "Ankara",
        "GÖLBAŞI": "Ankara",
        "POLATLI": "Ankara",
        "ALANYA": "Antalya",
        "MANAVGAT": "Antalya",
        "KUŞADASI": "Aydın",
        "DİDİM": "Aydın",
        "İNEGÖL": "Bursa",
        "NİLÜFER": "Bursa",
        "OSMANGAZİ": "Bursa",
        "BANDIRMA": "Balıkesir",
        "EDREMİT": "Balıkesir",
        "ÇORLU": "Tekirdağ",
        "ÇERKEZKÖY": "Tekirdağ",
        "GEBZE": "Kocaeli",
        "İZMİT": "Kocaeli",
        "DARICA": "Kocaeli",
        "KÖRFEZ": "Kocaeli",
        "İSKENDERUN": "Hatay",
        "SÖKE": "Aydın",
        "MERZİFON": "Amasya",
        "AKHİSAR": "Manisa",
        "TURGUTLU": "Manisa",
        "CİHANBEYLİ": "Konya",
        "EREĞLİ": "Konya",
        "ERCİŞ": "Van",
        "SİVEREK": "Şanlıurfa",
        "VİRANŞEHİR": "Şanlıurfa",
        "NUSAYBİN": "Mardin",
        "KIZILTEPE": "Mardin",
        "CİZRE": "Şırnak",
        "SİLOPİ": "Şırnak",
        "YÜKSEKOVA": "Hakkari",
        "ŞEBİNKARAHİSAR": "Giresun",
        "ÜNYE": "Ordu",
        "FATSA": "Ordu",
        "BAFRA": "Samsun",
        "ÇARŞAMBA": "Samsun",
    }

    # Ankara'da Yer Alan Merkezi Teşkilatlar (Başkanlık, Bakanlık, vb.)
    CENTRAL_ANKARA_ORGANIZATIONS: List[str] = [
        "BAKANLIĞI",
        "BAKANLIK",
        "GENEL MÜDÜRLÜĞÜ",
        "GENEL MÜDÜRLÜK",
        "CUMHURBAŞKANLIĞI",
        "DANIŞTAY",
        "YARGITAY",
        "SAYIŞTAY",
        "TBMM",
        "ANAYASA MAHKEMESİ",
        "TÜBİTAK",
        "SGK",
        "SOSYAL GÜVENLİK KURUMU",
        "GELİR İDARESİ BAŞKANLIĞI",
        "KAMU İHALE KURUMU",
        "ÖZELLEŞTİRME İDARESİ",
        "TÜRK PATENT",
        "TAPU VE KADASTRO GENEL",
        "DEVLET HAVA MEYDANLARI",
        "DHMİ",
        "KARAYOLLARI GENEL",
        "MADEN TETKİK VE ARAMA",
        "MTA",
        "ETİ MADEN",
        "TPAO",
        "BOTAŞ",
        "SAVUNMA SANAYİİ",
        "JANDARMA VE SAHİL GÜVENLİK AKADEMİSİ",
        "AFAD",
        "DİYANET İŞLERİ",
        "TÜİK",
        "NÜFUS VE VATANDAŞLIK",
        "TÜRKİYE BİLİMLER AKADEMİSİ",
        "TÜBA",
        "REKABET KURUMU",
        "BİLGİ TEKNOLOJİLERİ VE İLETİŞİM KURUMU",
        "BTK",
        "RADYO VE TELEVİZYON ÜST KURULU",
        "RTÜK",
        "MERKEZ BANKASI",
        "TCMB",
    ]

    _PROVINCE_PATTERNS: List[Tuple[str, re.Pattern]] = []

    @classmethod
    def _init_patterns(cls):
        """Performans için regex desenlerini bir kere derler."""
        if cls._PROVINCE_PATTERNS:
            return
        for p in cls.PROVINCES:
            norm_p = _normalize_turkish(p)
            # Kelime sınırıyla eşleşsin (örn. "KARS" "KARŞIYAKA" ile karışmasın)
            pattern = re.compile(rf"\b{re.escape(norm_p)}\b", re.IGNORECASE)
            cls._PROVINCE_PATTERNS.append((p, pattern))

    @classmethod
    def detect_city(
        cls,
        title: str = "",
        institution: str = "",
        position: str = "",
        raw_city: Optional[str] = None,
    ) -> str:
        """İlan alanlarını tarayarak geçerli bir il veya 'Türkiye Geneli' döner."""
        cls._init_patterns()

        # 1. Halihazırda mevcut şehir bilgisi varsa (örn: İŞKUR 'KAYSERİ / MELİKGAZİ')
        if raw_city:
            clean_raw = raw_city.strip()
            # Slash ayracı kontrolü
            parts = [part.strip() for part in clean_raw.split("/") if part.strip()]
            for part in parts:
                norm_part = _normalize_turkish(part)
                for p, _ in cls._PROVINCE_PATTERNS:
                    if _normalize_turkish(p) == norm_part:
                        return p
                # İlçe eşleşmesi kontrolü
                for district, mapped_province in cls.DISTRICT_MAPPING.items():
                    if _normalize_turkish(district) == norm_part:
                        return mapped_province

        combined = _normalize_turkish(f"{title} {institution} {position}")

        # 2. Özel Üniversiteler Eşleştirmesi (Atatürk Üni -> Erzurum vb.)
        for univ, mapped_province in cls.UNIVERSITY_MAPPING.items():
            if _normalize_turkish(univ) in combined:
                return mapped_province

        # 3. Belirgin İlçe Eşleştirmesi (Eleşkirt Belediyesi -> Ağrı vb.)
        for district, mapped_province in cls.DISTRICT_MAPPING.items():
            pattern = rf"\b{re.escape(_normalize_turkish(district))}\b"
            if re.search(pattern, combined):
                return mapped_province

        # 4. Doğrudan 81 İl Adı Eşleştirmesi
        for p, pattern in cls._PROVINCE_PATTERNS:
            if pattern.search(combined):
                return p

        # 5. Ankara Merkez Teşkilatı Kurumları
        for org in cls.CENTRAL_ANKARA_ORGANIZATIONS:
            if _normalize_turkish(org) in combined:
                return "Ankara"

        return cls.TURKIYE_GENELI
