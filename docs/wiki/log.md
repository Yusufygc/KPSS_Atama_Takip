# KPSS Atama Takip - Operasyonel Kayıt Defteri (Log)

Bu dosya, proje üzerinde gerçekleştirilen tüm önemli mimari kararların, kaynak analizlerinin ve altyapı adımlarının kronolojik özetidir. En yeni kayıt daima en üsttedir.

---

## [2026-10-12] QA-2 | Tarih Normalizasyonu, Arka Plan Tarama ve Kalan QA Maddeleri
* **Tarih normalizasyonu:** `app/core/dates.py` farklı portal biçimlerini (`13.10.2026`, ISO, `09 Ekim 2026`, yılsız `12 Ekim - 26 Ekim`) `deadline_on` (YYYY-MM-DD) alanına çevirir. API `only_active`, `deadline_on`, `is_expired` sunar; arayüzde "Süresi dolanları gizle" anahtarı ve kalan gün rozeti vardır; süresi dolanlar listenin sonuna alınır ve Telegram'a bildirilmez.
* **Arka plan tarama:** `POST /api/scrapers/run` 202 döner (`?wait=true` eşzamanlı), `GET /api/scrapers/run/status` durumu verir; "Şimdi Tara" ilerlemeyi bu uç noktadan izler.
* **Arayüz:** `AbortController` ile istek yarışı giderildi.
* **PDF önbelleği:** Dosyalar `hash_id` ile adlandırılır; eski ID tabanlı dosyalar taşınır, yetim/90 günden eski dosyalar silinir.
* **Diğer:** kalıcı 4xx hataları yeniden denenmez, `Retry-After` HTTP-date güvenli, açılışta ilk tarama (`SCRAPER_RUN_ON_STARTUP`), portal başına tek commit, `BaseNotifier.is_ready`, doküman düzeltmeleri.
* **Test altyapısı:** Testler gerçek ağa/Telegram'a çıkamaz (`forbid_real_network`), paylaşılan bildirici etkisizleştirilir. Bir test hatası (`monkeypatch.undo()`) geliştirme sırasında gerçek DB'ye yazıp Telegram'a mesaj göndermişti; kök neden kapatıldı.
* Bağlantılar: [[notifications]], [[scrapers]], [[architecture]]

---

## [2026-10-12] QA | QA Taraması Bulgularının Düzeltilmesi
* **SBB mükerrer ilan hatası (kritik):** `kod` URL parametresi her istekte değiştiği için hash URL'ye bağlıyken her taramada ~128 SBB ilanı "yeni" ekleniyordu. Kimlik artık başlık+son tarihten üretiliyor (`stable_url=False`); eski kayıtlar açılışta yeniden hash'lenip mükerrerler siliniyor.
* **Arama / etiket:** `search_text` ile Türkçe harf duyarsız arama; `field_tags` gerçek Türkçe karakterle saklanıyor, eski kaçışlı kayıtlar onarılıyor.
* **DB hata yönetimi:** Gövde hataları artık "bağlantı kurulamadı" diye sarılmıyor; alan istisnaları `http_status` taşıyor (5xx'te ayrıntı sızmıyor).
* **Tek servis örneği:** Zamanlayıcı ve API aynı `AnnouncementService`'i paylaşıyor (kilit ve portal durumları ortak).
* **P3 puanlaması:** Kelime başı eşleşme, akademik/işçi ilanları hariç, `KPSS-P3`/`KPSS (P3)` yazımları; `SCORING_VERSION` ile mevcut kayıtlar yeniden puanlanıyor.
* **İŞKUR:** Kazıyıcı sıfırdan yazıldı (alan bazlı ayrıştırma, tüm sayfalar, benzersiz URL).
* **Bildirimler:** İlk çalıştırma tabanı, döngü başı üst sınır + özet mesajı, 429 yönetimi, 24 saat içinde yeniden deneme.
* **Kariyer Kapısı:** Detay bağlantısı `/IlanDetay?i=` olarak düzeltildi (`/isealim/IlanDetay` 406 veriyordu).
* Bağlantılar: [[notifications]], [[scrapers]], [[kpss_scoring]]

---

## [2026-10-12] SECURITY & QUALITY | Güvenlik Sertleştirmesi, Puanlama Hatası ve Test Altyapısı
* **XSS:** Arayüzde kazınan veriler `escapeHtml`/`safeUrl` ile basılıyor; `javascript:` adresleri sunucuda reddediliyor.
* **Puanlama hatası:** `str.upper()` Türkçe `i` harfini `I` yaptığı için "Bilgisayar mühendisi" gibi küçük harfli başlıklar P3 olarak eşleşmiyordu. Ortak `turkish_upper` (`app/core/text.py`) eklendi ve üç eşleştiricide kullanıldı.
* **Telegram:** Mesaj alanları HTML kaçışlanıyor, bot token'ı loglardan temizleniyor.
* **API anahtarı, CORS, güvenlik başlıkları, SSRF, TLS doğrulaması:** Ayrıntılar için [[security]].
* **Güvenilirlik:** Chrome zaman aşımında öldürülüyor (süreç sızıntısı giderildi), eşzamanlı tarama kilidi (`409`), zamanlayıcıda `max_instances=1`, İŞKUR/İlan.gov.tr hataları artık "başarılı" görünmüyor, Resmî Gazete yalnızca ilan PDF bağlantılarını alıyor ve TRT (UTC+3) kullanıyor.
* **Veri:** `general_count` düzeltildi (P3 ve P1/P2 örtüşmesi), `LIKE` joker karakterleri kaçışlandı, `save`/`save_many` SQL tekrarı kaldırıldı.
* **Dağıtım:** Python 3.12, root olmayan kullanıcı, `.dockerignore`, sabitlenmiş bağımlılıklar (`requirements.txt`), geliştirme bağımlılıkları (`requirements-dev.txt`), CI iş akışı.
* **Test:** Betik tarzı testler gerçek `pytest` testlerine çevrildi (geçici veritabanı, ağ yok; canlı testler `--run-live`). 71 test, kapsam %52 -> %75.
* Bağlantılar: [[security]], [[rules]], [[scrapers]]


## [2026-10-10] REFACTOR & FEATURE | SVG Vektörel İkonlara Geçildi, Filtre Karmaşası Çözüldü ve Şehir Filtresi Eklendi
* **Vektörel İkon Mimarisi (`web/js/icons.js`):** Arayüzdeki tüm emojiler kaldırıldı; Lucide ve modern tasarım standartlarında temiz SVG vektörel ikon kütüphanesi entegre edildi.
* **Filtre Karmaşasının Çözülmesi:** Üst üste yığılan, tekrarlayan ve ekranı boğan 4 sıralı filtreleme yapısı kaldırıldı:
  - Üstte tek satırlı 12 kolonluk birleşik araç çubuğu oluşturuldu: Arama (temizleme butonlu), Şehir Seçici, Portal Seçici ve Tek Tık Filtre Sıfırlama butonu.
  - Altta sade kategori sekmesi (Tüm İlanlar, Bölümüm, P3, P1/P2) ve sağda anlık sonuç sayısı yerleştirildi.
  - Mükerrer olan "Hızlı Arama" satırı kaldırıldı; alt uzmanlık çipleri yalnızca "Bölümüm" sekmesi aktifken gösterilecek şekilde bağlamsal hale getirildi.
* **Şehir Tespit ve Filtreleme Motoru (`app/core/scoring/city_matcher.py`):**
  - Türkiye'nin 81 ili, il adı geçmeyen tanınmış devlet üniversiteleri (Atatürk Üni -> Erzurum vb.), merkezi kamu teşkilatları (Bakanlıklar, Başkanlıklar -> Ankara) ve belirgin ilçeler (Eleşkirt -> Ağrı vb.) üzerinden il tespit motoru yazıldı.
  - SQLite veritabanındaki 241 ilanın tamamı geriye dönük taranarak şehirleri güncellendi ve `idx_announcements_city` indeksi eklendi (Ankara: 74, Türkiye Geneli: 46, İstanbul: 18, Rize: 12, vb.).
  - `GET /api/announcements/cities` uç noktası ve `GET /api/announcements?city=...` filtreleme parametresi bağlandı.
* Uçtan uca testler (`tests/test_full_system.py`) güncellendi ve başarıyla geçti.
* Bağlantılar: [[architecture]], [[rules]], [[kpss_scoring]]

## [2026-10-10] FEATURE | Bilgisayar Mühendisliği ve Bilişim Odaklı Profesyonel Filtreleme Sistemi Entegre Edildi
* Kullanıcının bölümü olan **Bilgisayar Mühendisliği** ve kamu sektöründeki ilgili uzmanlık kadrolarını (Yazılım, Siber Güvenlik, Sözleşmeli Bilişim Personeli - SBP, Ağ/Sistem, Çözümleyici, Veri/Yapay Zeka) anında tespit eden `ITFieldMatcher` kural ve regex motoru (`app/core/scoring/it_field_matcher.py`) geliştirildi.
* Kamudaki 375 sayılı KHK Ek 6. madde kapsamındaki Sözleşmeli Bilişim Personeli (SBP), Bilgisayar Mühendisi, Çözümleyici, Programcı ve Siber Güvenlik ilanları normalize edilmiş Türkçe regex modelleriyle 7 alt uzmanlık etiketine (`ITSubField`) ayrıştırıldı.
* Domain modeli `Announcement` ve REST şemaları `field_tags: List[str]` ve `is_it_field: bool` alanlarıyla zenginleştirildi.
* SQLite veritabanına `field_tags` ve `is_it_field` sütunları ile `idx_announcements_it` indeksi eklenerek geriye dönük uyumlu dinamik migrasyon uygulandı. Mevcut tüm 241 kayıt etiketlendi ve 14 adet bilişim ilanı anında indekslendi.
* `AnnouncementRepository` ve `AnnouncementService` katmanlarına `only_it: bool` ve `field_tag: Optional[str]` parametreleri eklendi; `GET /api/announcements/stats` uç noktasına `it_count` metriği dahil edildi.
* Web Dashboard'a:
  - 5. KPI Metrik Kartı: "💻 Bilişim & Yazılım - Bilgisayar Müh."
  - Hızlı tek tık arama butonları (Bilgisayar Mühendisi, Sözleşmeli Bilişim, Yazılım, Siber Güvenlik, Çözümleyici, Sistem)
  - Hızlı Filtre Barına "💻 Bölümüm (Bilgisayar & Bilişim)" butonu ve rozeti
  - Bilişim alt uzmanlık branş çipleri (Tümü, SBP, Yazılım & Web, Siber Güvenlik, Bilgisayar Mühendisliği, Ağ & Sistem, Veri & Yapay Zeka)
  - İlan kartlarında belirgin camgöbeği (cyan) şerit (`priority-it-stripe`) ve alt uzmanlık etiketleri eklendi.
  - Seçimler `localStorage` üzerinde saklanarak sayfa yenilemelerinde korunur hale getirildi.
* Uçtan uca sistem test paketi (`tests/test_full_system.py`) yeni Bilişim motorunu ve API filtreleme yeteneklerini kapsayacak şekilde güncellendi ve tüm testler başarıyla geçti.
* Bağlantılar: [[kpss_scoring]], [[architecture]], [[rules]]

## [2026-10-10] BUGFIX | Kamu İlan (SBB) 404 Hotlink Koruması Çözüldü ve PDF Proxy Entegre Edildi
* SBB sunucusunun (`kamuilan.sbb.gov.tr/ilanDetay.aspx`) doğrudan harici tarayıcı yönlendirmelerinde HTTP `Referer` başlığı doğrulaması yaptığı ve referer eksik/harici olduğunda 404 döndürdüğü tespit edildi.
* İlan detay sayfasının aslında doğrudan resmi işe alım PDF belgesi akıttığı (`application/pdf`) keşfedildi.
* FastAPI'ye `GET /api/announcements/{id}/document` asenkron proxy ve önbellek uç noktası eklendi; `Referer: https://kamuilan.sbb.gov.tr/` başlığıyla PDF çekilerek yerel önbelleğe (`data/documents/`) kaydedildi ve tarayıcıya kesintisiz akıtıldı.
* Web Dashboard'da SBB ilanları için "📄 İlan Metni (PDF)" doğrudan proxy uç noktasına bağlandı, yanına "🏛️ SBB Portalı" ana sayfa butonu eklendi.
* SBB kazıyıcı adaptörü `span.black`, `span.patrol` ve `span.h5date` etiketlerini ayrıştıracak şekilde optimize edildi; kurum, pozisyon ve son başvuru tarihleri tam ayrıştırıldı.
* Veritabanı 131 adet temiz, hatasız ve tıklandığında anında PDF açılan ilan kaydıyla güncellendi.
* Bağlantılar: [[scrapers]], [[architecture]], [[rules]]

## [2026-10-10] BUGFIX & FEATURE | Türkçe Karakter Kodlaması Düzeltildi ve Tema Değişimi Eklendi
* Kamu İlan (SBB) adaptöründe `windows-1254` kaynaklı Türkçe karakter bozulması (`GELÄ°R Ä°DARESÄ°...`) UTF-8 kod çözümüyle giderildi.
* Veritabanındaki eski bozuk SBB kayıtları temizlenerek 131 adet ilan eksiksiz Türkçe karakterlerle yeniden işlendi.
* Web Dashboard'a Aydınlık / Karanlık Mod (Dark / Light Mode) eklendi; kullanıcı tercihi `localStorage` ile kalıcı hale getirildi.
* Bağlantılar: [[scrapers]], [[architecture]], [[rules]]

## [2026-10-10] WEB DASHBOARD COMPLETE | Modern Web Arayüzü ve FastAPI Entegrasyonu Tamamlandı
* `web/index.html`, `web/css/style.css` ve `web/js/app.js` modüler istemci yapısıyla kodlandı.
* UI-Backend mutlak ayrımı sağlandı; arayüz yalnızca `/api/...` REST uç noktalarını tüketiyor.
* KPSS P3 (Lisans) ve P1/P2 (Kariyer) hızlı filtre butonları, unvan arama, portal seçici eklendi.
* Canlı "Şimdi Tara" butonu, anlık toast bildirimleri ve 6 portalın sağlık durumunu gösteren alt panel entegre edildi.
* Telegram yapılandırma ve anlık test bildirimi gönderen ayarlar modalı hayata geçirildi.
* FastAPI statik dosya sunumu (`/`, `/css/...`, `/js/...`) `aiofiles` ile asenkron bağlandı ve E2E test ile doğrulandı.
* Bağlantılar: [[architecture]], [[rules]], [[notifications]]

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
