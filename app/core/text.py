"""KPSS Atama Takip - Türkçe Metin Normalizasyon Yardımcıları."""


def turkish_upper(text: str) -> str:
    """Türkçe kurallarına uygun büyük harfe çevirir (i -> İ, ı -> I).

    Python'un `str.upper()` metodu `i` harfini `I` yaptığı için "mühendis" gibi
    küçük harfli metinler "MÜHENDIS" olur ve "MÜHENDİS" anahtar kelimesiyle eşleşmez.
    """
    if not text:
        return ""
    return text.replace("i", "İ").replace("ı", "I").upper()


_FOLD_TABLE = str.maketrans(
    {
        "İ": "i", "I": "i", "ı": "i",
        "Ç": "c", "ç": "c",
        "Ğ": "g", "ğ": "g",
        "Ö": "o", "ö": "o",
        "Ş": "s", "ş": "s",
        "Ü": "u", "ü": "u",
    }
)


def fold_turkish(text: str | None) -> str:
    """Arama için Türkçe metni küçük harfli ASCII benzeri biçime indirger.

    "MÜHENDİS", "mühendis" ve "muhendis" aynı değere dönüşür. SQLite `LIKE` yalnızca ASCII
    harflerde büyük/küçük harf duyarsız olduğundan arama bu katlanmış metin üzerinde yapılır.
    """
    if not text:
        return ""
    return " ".join(text.translate(_FOLD_TABLE).lower().split())
