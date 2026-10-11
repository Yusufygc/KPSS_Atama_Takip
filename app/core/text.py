"""KPSS Atama Takip - Türkçe Metin Normalizasyon Yardımcıları."""


def turkish_upper(text: str) -> str:
    """Türkçe kurallarına uygun büyük harfe çevirir (i -> İ, ı -> I).

    Python'un `str.upper()` metodu `i` harfini `I` yaptığı için "mühendis" gibi
    küçük harfli metinler "MÜHENDIS" olur ve "MÜHENDİS" anahtar kelimesiyle eşleşmez.
    """
    if not text:
        return ""
    return text.replace("i", "İ").replace("ı", "I").upper()
