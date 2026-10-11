"""Güvenlik yardımcıları: URL doğrulama, host allow-list, HTML kaçışlama."""

import pytest

from app.core.security import escape_html, host_in_domains, is_http_url

SBB = ("kamuilan.sbb.gov.tr",)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=1", True),
        ("http://kamuilan.sbb.gov.tr/x", True),
        ("https://sub.kamuilan.sbb.gov.tr/x", True),
        ("https://evil.test/?kamuilan.sbb.gov.tr", False),  # eski alt dize kontrolü bunu kabul ediyordu
        ("https://kamuilan.sbb.gov.tr.evil.test/x", False),
        ("https://evilkamuilan.sbb.gov.tr/x", False),
        ("https://user@evil.test/kamuilan.sbb.gov.tr", False),
        ("ftp://kamuilan.sbb.gov.tr/x", False),
        ("javascript:alert(1)", False),
        ("", False),
        (None, False),
    ],
)
def test_host_in_domains(url, expected):
    assert host_in_domains(url, SBB) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://a.test", True),
        ("HTTP://a.test/x", True),
        ("javascript:alert(1)", False),
        ("data:text/html,<script>", False),
        ("//a.test/x", False),
        ("/relative", False),
        (None, False),
    ],
)
def test_is_http_url(url, expected):
    assert is_http_url(url) is expected


def test_escape_html_escapes_tags_and_quotes():
    payload = "<script>\"x\"&'y'</script>"
    escaped = escape_html(payload)
    assert "<" not in escaped
    assert '"' not in escaped
    assert "&lt;script&gt;" in escaped
    assert escape_html(None) == ""
