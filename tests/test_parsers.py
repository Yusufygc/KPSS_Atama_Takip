"""SBB, Yerel Yönetimler, Resmî Gazete ve Kariyer Kapısı ayrıştırıcıları (sahte HTML/JSON ile, ağ yok)."""

from datetime import datetime

from app.core.dates import TURKEY_TZ
from app.scrapers.adapters.kamu_ilan import KamuIlanSbbScraper
from app.scrapers.adapters.resmi_gazete import ResmiGazeteScraper
from app.scrapers.adapters.yerel_yonetimler import YerelYonetimlerScraper


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.status_code = 200


def patch_request(monkeypatch, scraper, payload: bytes):
    async def fake_request(*args, **kwargs):
        return FakeResponse(payload)

    monkeypatch.setattr(scraper, "_request", fake_request)


async def test_sbb_parses_cards_and_marks_url_as_unstable(monkeypatch):
    html = """
    <a href="ilanDetay.aspx?kod=AAA%2b">
      <span class="black">SAVUNMA SANAYİİ BAŞKANLIĞI</span>
      <span class="patrol">22 UZMAN YARDIMCISI ALACAK</span>
      <span class="h5date">12 Ekim - 26 Ekim</span>
    </a>
    <a href="/ilanDetay.aspx?kod=BBB"><span class="black">KURUM</span></a>
    <a href="hakkimizda.aspx">Hakkımızda</a>
    <a href="ilanDetay.aspx?kod=CCC">çok kısa</a>
    """.encode()
    scraper = KamuIlanSbbScraper()
    patch_request(monkeypatch, scraper, html)

    items = await scraper.scrape()

    assert len(items) == 3  # 'hakkimizda.aspx' ilan bağlantısı olmadığı için dışarıda
    first = items[0]
    assert first.title == "SAVUNMA SANAYİİ BAŞKANLIĞI - 22 UZMAN YARDIMCISI ALACAK"
    assert first.deadline_date == "12 Ekim - 26 Ekim"
    assert first.url == "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=AAA%2b"
    assert all(item.stable_url is False for item in items)


async def test_yerel_yonetimler_parses_date_title_and_institution(monkeypatch):
    html = """
    <a href="/ispartada-duyuru-1">09 Ekim 2026 ISPARTA İLİ SARIİDRİS BELEDİYE BAŞKANLIĞINA ZABITA MEMURU ALIMI</a>
    <a href="/baska-sayfa">ilgisiz</a>
    <a href="https://yerelyonetimler.csb.gov.tr/x-duyuru-2">kısa</a>
    """.encode()
    scraper = YerelYonetimlerScraper()
    patch_request(monkeypatch, scraper, html)

    items = await scraper.scrape()

    assert len(items) == 1
    assert items[0].publish_date == "09 Ekim 2026"
    assert items[0].title.startswith("ISPARTA İLİ")
    assert "BELEDİYE" in items[0].institution
    assert items[0].url == "https://yerelyonetimler.csb.gov.tr/ispartada-duyuru-1"


async def test_resmi_gazete_keeps_only_announcement_pdfs(monkeypatch):
    today = datetime.now(TURKEY_TZ)
    stamp = today.strftime("%Y%m%d")
    html = f"""
    <a href="{stamp}-4-1.pdf">İçişleri Bakanlığı Emniyet Genel Müdürlüğünden:</a>
    <a href="{stamp}-4-2.pdf">Ankara Üniversitesi Rektörlüğünden:</a>
    <a href="../index.htm">Ana sayfa menüsü bağlantısı</a>
    <a href="{stamp}-4.htm">Bölüm sayfası bağlantısı</a>
    """.encode("windows-1254")
    scraper = ResmiGazeteScraper()
    patch_request(monkeypatch, scraper, html)

    items = await scraper.scrape()

    titles = {i.title for i in items}
    assert "İçişleri Bakanlığı Emniyet Genel Müdürlüğünden:" in titles
    assert not any("menüsü" in t or "Bölüm sayfası" in t for t in titles)
    assert all(i.url.endswith(".pdf") and i.pdf_url == i.url for i in items)
