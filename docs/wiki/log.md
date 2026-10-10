# KPSS Atama Takip - Operasyonel Kayıt Defteri (Log)

Bu dosya, proje üzerinde gerçekleştirilen tüm önemli mimari kararların, kaynak analizlerinin ve altyapı adımlarının kronolojik özetidir. En yeni kayıt daima en üsttedir.

---

## [2026-10-10] PHASE 3-6 COMPLETE | Scrapers, KPSS Eşleştirme, Telegram, Servisler ve FastAPI API İnşa Edildi
* `BaseScraper` ve `ScraperRegistry` mimarisiyle 6 portalın somut adaptörleri kodlandı (Kariyer Kapısı, Resmî Gazete, Kamu İlan SBB, Yerel Yönetimler, İŞKUR, İlan.gov.tr).
* `ScraperOrchestrator` ile hata izolasyonlu eşzamanlı (asenkron paralel) kazıma motoru hayata geçirildi.
* `KPSSScoreMatcher` stratejisi ile P3 Lisans (Öncelik 3), P1/P2 Kariyer (Öncelik 2) ve Genel kadrolar regex + anahtar kelime ağırlıklarıyla sınıflandırıldı.
* `TelegramNotifier` ile HTML zengin formatlı, çift linkli (ilan ve PDF) anlık bildirim servisi yazıldı.
* `AnnouncementService` ile Kazıma -> Skorlama -> Mükerrer Önleme -> SQLite Kayıt -> Bildirim boru hattı (pipeline) bağlandı.
* `SchedulerService` ile APScheduler arka plan zamanlayıcısı entegre edildi.
* `FastAPI` REST API katmanı (`/api/announcements`, `/api/scrapers`, `/api/settings`, `/health`) kodlandı ve `tests/test_full_system.py` ile E2E doğrulandı.
* Canlı testte Kariyer Kapısı'ndan 24 gerçek atama ilanı çekildi; 9 adet P3 lisans, 6 adet P1/P2 kariyer meslek ilanı başarıyla veritabanına işlendi.
* Bağlantılar: [[scrapers]], [[kpss_scoring]], [[notifications]], [[architecture]]

## [2026-10-10] PHASE 2 COMPLETE | Domain Modelleri ve Asenkron SQLite Repository İnşa Edildi
* `Announcement` ana domain varlığı, `ScoreType` (P3, P1, P2) ve `PriorityLevel` modelleri kodlandı (`models.py`).
* Deterministik SHA-256 hash parmak izi ile mükerrer ilan önleme mantığı uygulandı.
* API ve sunum katmanı için Pydantic DTO'ları (`schemas.py`) yazıldı (`AnnouncementResponse`, `AnnouncementFilterParams`, `SystemStatsResponse`).
* `aiosqlite` ile WAL modunda çalışan asenkron bağlantı ve şema yöneticisi (`connection.py`) kuruldu.
* Repository Pattern uygulandı (`AnnouncementRepository`): Mükerrer önleme, toplu kayıt, P3/P1/P2 filtreleme, okunmamış bildirim yönetimi ve istatistik hesaplama test edildi.
* `tests/test_repository.py` ile tüm veritabanı ve model işlevleri uçtan uca doğrulandı.
* Bağlantılar: [[architecture]], [[rules]], [[kpss_scoring]]

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
