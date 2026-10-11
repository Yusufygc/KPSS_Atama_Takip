# Güvenlik (Security)

Bu doküman, uygulamanın güvenlik kararlarını ve işletim gereksinimlerini özetler.

## 1. Kimlik Doğrulama (API Anahtarı)
* Yönetim uç noktaları `X-API-Key` başlığı ister: `POST /api/scrapers/run`, `GET /api/settings`, `POST /api/settings/telegram/test`.
* Anahtar `.env` içindeki `API_KEY` değerinden okunur ve `secrets.compare_digest` ile sabit sürede karşılaştırılır.
* `API_KEY` boşsa: geliştirme ortamında kontrol atlanır; `APP_ENV=production` iken bu uç noktalar `503` döner (güvensiz açık kalmaz).
* Okuma uç noktaları (`/api/announcements*`, `/api/scrapers/status`, `/health`) kamuya açık veriler sunar ve anahtar istemez.
* Web arayüzü `401` aldığında anahtarı bir kez sorar ve yalnızca `sessionStorage` içinde tutar.
* Üretimde servis yalnızca `127.0.0.1`'e bağlanır (`docker-compose.yml`); dışarı açmak için HTTPS sonlandıran bir ters vekil kullanın.

## 2. Girdi / Çıktı Güvenliği
* **XSS:** Kazınan tüm alanlar arayüzde `escapeHtml` ile basılır, bağlantılar `safeUrl` ile yalnızca `http(s)` olarak kabul edilir (`web/js/app.js`).
* **Sunucu tarafı URL doğrulaması:** `javascript:` vb. şemalı ilanlar kaydedilmez (`AnnouncementService`); `pdf_url` geçersizse temizlenir.
* **SSRF:** Belge proxy'si yalnızca ayrıştırılmış host'u `ScraperLimits.DOCUMENT_ALLOWED_DOMAINS` içinde olan adreslere istek atar (`app/core/security.py::host_in_domains`), yönlendirme izlemez ve indirmeyi `MAX_DOCUMENT_BYTES` ile sınırlar.
* **Telegram:** Mesaja giren tüm kazınmış alanlar `html.escape` ile kaçışlanır; bot token'ı log ve hata metinlerinden temizlenir.
* **SQL:** Tüm sorgular parametrelidir; `LIKE` aramalarında `%` ve `_` kaçışlanır.

## 3. Taşıma ve Tarayıcı Güvenliği
* Kazıyıcılar TLS sertifikasını doğrular (`BaseScraper.verify_ssl = True`). Sertifika zinciri bozuk bir portal için yalnızca ilgili adaptörde bilinçli olarak `False` yapılmalı ve gerekçesi yazılmalıdır.
* Tüm yanıtlara `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` ve CSP eklenir (`SecurityConstants`).
* CORS varsayılan olarak kapalıdır (arayüz aynı origin'den sunulur). Gerekirse `CORS_ORIGINS` ile açık kaynak listesi verilir; `*` yok sayılır.
* `/docs`, `/redoc` ve `/openapi.json` üretimde kapalıdır.
* Bilinen sınırlama: Tailwind Play CDN (`cdn.tailwindcss.com`) SRI olmadan yüklenir ve CSP'de `script-src 'unsafe-inline'` gerektirir. Kalıcı çözüm Tailwind'i build adımıyla statik CSS'e derlemektir.

## 4. Kapsayıcı
* Konteyner `root` olmayan `app` (uid 1000) kullanıcısıyla çalışır; `cap_drop: ALL` ve `no-new-privileges` etkindir.
* `./data` ve `./logs` bağlama dizinleri uid 1000 tarafından yazılabilir olmalıdır (`chown 1000:1000 data logs`).
* Chromium'un kendi sandbox'ı yalnızca kapsayıcıda (`BROWSER_NO_SANDBOX=true`) kapatılır; yerel çalıştırmada sandbox açıktır.

## 5. Test Ortamı (gerçek dünyaya kapalı)
* `APP_ENV=test` iken `app/config.py` doğrulayıcısı Telegram'ı **zorla kapatır** (token/chat ID boşaltılır, bildirim kapalı); ortam değişkeni veya `.env` ne derse desin geçersizdir.
* `APP_ENV=test` ile gerçek veritabanı dosyası (`kpss_atama.db`) kullanılamaz; ayar yüklenirken hata verir.
* Test ortamı `.env.test` dosyasını okur (`python run.py --test`, `baslat-test.bat` veya `docker-compose.test.yml`); gerçek `.env` hiç okunmaz. Port 8001, veritabanı `data/test/kpss_test.db`.
* Örnek veri: `python scripts/seed_test_db.py [--reset]` (18 gerçekçi ilan; süresi dolmuş, yaklaşan, tarihsiz, bildirilmiş/bekleyen karışımı). Betik gerçek DB dosya adını yazmayı reddeder.
* `pytest` testleri ayrıca gerçek ağa çıkamaz ve paylaşılan bildirici etkisizleştirilir (`tests/conftest.py`).

## 6. Geliştirme Kontrolleri
* `ruff check .`, `bandit -r app run.py -ll`, `pip-audit -r requirements.txt` ve `pytest` CI'da (`.github/workflows/ci.yml`) çalışır.
* Canlı portal testleri varsayılan olarak atlanır: `pytest --run-live`.

Bağlantılar: [[rules]], [[architecture]], [[notifications]]
