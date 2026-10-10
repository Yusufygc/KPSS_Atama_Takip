# KPSS Atama Takip - Operasyonel Kayıt Defteri (Log)

Bu dosya, proje üzerinde gerçekleştirilen tüm önemli mimari kararların, kaynak analizlerinin ve altyapı adımlarının kronolojik özetidir. En yeni kayıt daima en üsttedir.

---

## [2026-10-10] PHASE 1 COMPLETE | Core Temelleri İnşa Edildi ve Doğrulandı
* Tip güvenli `AppSettings` (`app/config.py`) ve `.env` şablonu oluşturuldu.
* Merkezi sabitler (`strings.py`, `icons.py`, `settings.py`) hardcode ve magic number yasağına uygun kodlandı.
* Hiyerarşik `KPSSBaseException` sınıfı ve alt dalları (`ScraperException`, `DatabaseException`, `NotificationException`, `ValidationException`) oluşturuldu.
* UTF-8 destekli dönen dosya (`logs/app.log`) ve bağlamsal scraper loglayıcı (`get_scraper_logger`) mekanizması kuruldu.
* `tests/test_core.py` birim test paketi ile tüm altyapı bileşenleri doğrulandı.
* Bağlantılar: [[rules]], [[architecture]]

## [2026-10-10] INGEST | 6 Kamu Portalı Canlı Analizi ve Protokol Tespiti
* Kariyer Kapısı (`api.kariyerkapisi.gov.tr/api/ilan/GetIseAlimPage`) doğrudan REST JSON endpoint'i tespit edildi.
* Resmi Gazete (`resmigazete.gov.tr/ilanlar/eskiilanlar/YYYY/MM/YYYYMMDD-4.htm`) Çeşitli İlanlar sayfasının deterministik yapısı doğrulandı.
* Kamu İlan SBB (`kamuilan.sbb.gov.tr/ilan_menu.aspx`) masaüstü tablosu HTML scraping ile doğrulandı.
* Yerel Yönetimler GM (`yerelyonetimler.csb.gov.tr/duyurular`) belediye duyuruları doğrulandı.
* İŞKUR E-Şube (`esube.iskur.gov.tr`) ViewState + Kamu radyo filtresi postback mekanizması çözüldü.
* İlan.gov.tr Angular SPA yapısı headless Chrome üzerinden DOM dump ile doğrulandı.
* Bağlantılar: [[scrapers]], [[architecture]]

## [2026-10-10] ARCHITECTURE | Seçenek A (Web Dashboard + Arka Plan Servisi) Kararı
* Kullanıcı kararıyla Seçenek A benimsendi: FastAPI asenkron REST backend + Arka plan zamanlayıcı + SQLite + Telegram Bot + Ayrı Web UI.
* KPSS Puan Önceliği: P3 öncelikli, P1 ve P2 puanları aktif takip edilecek şekilde strateji belirlendi.
* Wiki Sistemi ve Kurallar Anayasası kuruldu.
* Bağlantılar: [[architecture]], [[rules]], [[kpss_scoring]]
