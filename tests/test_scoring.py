"""KPSS puan, bilişim alanı ve şehir eşleştirme motorları."""

import pytest

from app.core.scoring.city_matcher import CityMatcher
from app.core.scoring.it_field_matcher import ITFieldMatcher, ITSubField
from app.core.scoring.strategy import KPSSScoreMatcher
from app.core.text import turkish_upper
from app.domain.models import PriorityLevel, ScoreType


def test_turkish_upper_handles_dotted_and_dotless_i():
    assert turkish_upper("mühendis") == "MÜHENDİS"
    assert turkish_upper("ışık") == "IŞIK"
    assert turkish_upper("") == ""


@pytest.mark.parametrize(
    "title",
    [
        "Bilgisayar mühendisi alımı",  # küçük harfli "mühendis": eskiden GENEL dönüyordu
        "Yazılım Mühendisi alımı",
        "sözleşmeli personel alım ilanı",
        "ZABITA MEMURU ALIMI",
    ],
)
def test_p3_keywords_match_regardless_of_case(title):
    scores, priority = KPSSScoreMatcher.match(title=title)
    assert ScoreType.P3 in scores
    assert priority == PriorityLevel.PRIORITY_P3


def test_career_match():
    scores, priority = KPSSScoreMatcher.match(
        title="İletişim Başkanlığı 15 Uzman Yardımcısı Alacak", institution="İletişim Başkanlığı"
    )
    assert ScoreType.P1 in scores
    assert priority == PriorityLevel.CAREER_P1_P2


def test_explicit_p3_regex():
    scores, _ = KPSSScoreMatcher.match(title="İlan", raw_content="2026 KPSSP3 puan türünden")
    assert scores == [ScoreType.P3]


def test_general_when_nothing_matches():
    scores, priority = KPSSScoreMatcher.match(title="Duyuru")
    assert scores == [ScoreType.GENERAL]
    assert priority == PriorityLevel.NORMAL


def test_it_matcher_multiple_subfields():
    tags = ITFieldMatcher.match_tags(
        title="Sözleşmeli Bilişim Personeli (Yazılım Geliştirici & Siber Güvenlik Uzmanı) Alımı",
        institution="TÜBİTAK",
    )
    assert {ITSubField.CONTRACTED_IT.value, ITSubField.SOFTWARE.value, ITSubField.CYBER_SECURITY.value} <= set(tags)


def test_it_matcher_lowercase_title():
    assert ITSubField.COMPUTER_ENGINEERING.value in ITFieldMatcher.match_tags(title="bilgisayar mühendisi aranıyor")


@pytest.mark.parametrize(
    ("title", "institution", "expected"),
    [
        ("Sözleşmeli Bilişim Personeli Alımı", "Çalışma ve Sosyal Güvenlik Bakanlığı", "Ankara"),
        ("İzmir Bakırçay Üniversitesi Sözleşmeli Personel", "İzmir Bakırçay Üniversitesi", "İzmir"),
        ("Atatürk Üniversitesi Sözleşmeli Personel İlanı", "Atatürk Üniversitesi Rektörlüğü", "Erzurum"),
        ("Eleşkirt Belediye Başkanlığı Zabıta Memuru Alımı", "Eleşkirt Belediyesi", "Ağrı"),
    ],
)
def test_city_matcher(title, institution, expected):
    assert CityMatcher.detect_city(title=title, institution=institution) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Adaylarda KPSS-P3 puanı aranır",
        "KPSS (P3) puan türünden en az 70",
        "KPSS P-3 puanı",
        "kpss p3 puan türü",
        "P3 puan türü ile",
    ],
)
def test_explicit_p3_spellings(text):
    scores, _ = KPSSScoreMatcher.match(title="Duyuru", raw_content=text)
    assert scores == [ScoreType.P3]


@pytest.mark.parametrize(
    "title",
    [
        "Mühendislik Fakültesi öğretim üyesi alımı",
        "Mimarlık Fakültesi Doç. Dr. alımı",
        "Üniversite Doktor Öğretim Üyesi alım ilanı",
        "Belediye sürekli işçi alımı (şoför)",
        "2024/B sınıfı duyuru",  # "4/B" kalıbı sayının içinde eşleşmemeli
    ],
)
def test_implicit_match_skips_academic_labour_and_embedded_numbers(title):
    scores, priority = KPSSScoreMatcher.match(title=title)
    assert scores == [ScoreType.GENERAL]
    assert priority == PriorityLevel.NORMAL


@pytest.mark.parametrize("title", ["4/B sözleşmeli alım", "4-B Sözleşmeli", "Belediye 4 / B Sözleşmeli personel"])
def test_4b_pattern_still_matches(title):
    assert KPSSScoreMatcher.match(title=title)[0] == [ScoreType.P3]


def test_explicit_score_wins_even_for_academic_wording():
    scores, _ = KPSSScoreMatcher.match(title="Öğretim görevlisi alımı", raw_content="KPSS P3 en az 60")
    assert scores == [ScoreType.P3]
