# Sürekli (7/24) Çalıştırma ve Telegram Bildirimi

Bu rehber uygulamayı bir makinede (ev bilgisayarı/mini PC, Raspberry Pi veya Türkiye'deki bir VPS) Docker ile 7/24
çalıştırır ve yeni ilan çıktığında Telegram'a bildirim gönderir. Uygulama internete yalnızca **dışarı** bağlanır
(portallar + Telegram); dışarıya açık bir port gerekmez.

## 0. Barındırma Yeri Seçimi: Türkiye IP'si Şart

**Ölçüm (2026-10-12):** Herkese açık bir ağ denetleme servisiyle (check-host.net) portallar Frankfurt, Amsterdam,
Zürih, Milano, Londra ve ABD veri merkezlerinden denendi:

| Portal | Türkiye (İstanbul) | Yurt dışı veri merkezleri |
|---|---|---|
| Kamu İlan (SBB) | HTTP 200 | **403 Forbidden** (denenen tüm ülkelerde) |
| Kariyer Kapısı API | ulaşılabiliyor | **bağlantı zaman aşımı** (tüm ülkelerde) |
| İŞKUR, İlan.gov.tr, Resmî Gazete | 200 | 200 |
| Yerel Yönetimler | 200 | karışık (çoğunda 200) |

En çok ilanı veren SBB ve Kariyer Kapısı yurt dışı IP'lerini reddeder. Bu nedenle **yurt dışındaki bulutlar
(Oracle, AWS, Azure, GCP, Vercel, Render, Fly.io, GitHub Actions vb.) uygun değildir**; kazıyıcının Türkiye çıkışlı
bir IP'den çalışması gerekir.

| Seçenek | Not |
|---|---|
| Evdeki 7/24 açık bilgisayar / mini PC / Raspberry Pi | Ev internetinin IP'si Türkiye'dedir; ek ücret yok (elektrik hariç). Önerilen. |
| Türkiye'de VPS | Aylık ücretli; IP Türkiye'de olduğundan çalışması beklenir, satın almadan `check_portals.py` ile doğrulayın. |
| Yurt dışı bulut + Türkiye çıkışlı proxy | Mümkün ama karmaşık (bkz. Sorun Giderme). |

**Veritabanı (SQLite) bir sorun değildir:** Neon vb. barındırılan bir veritabanı kazıyıcının IP'sini değiştirmez;
engel veritabanında değil, portallara giden isteğin çıkış IP'sindedir. Uygulama ayrıca SQLite'a göre yazılmıştır.

## 1. Hazırlık

* Docker ve Docker Compose kurun (Windows/Mac: Docker Desktop; Linux: `docker.io` + `docker-compose-v2`).
* Linux'ta veri dizinlerini konteyner kullanıcısı (uid 1000) için hazırlayın:
  ```bash
  mkdir -p data/backups logs && sudo chown -R 1000:1000 data logs
  ```
* `.env` dosyasını örnekten oluşturun: `cp deploy/env.production.example .env` (Linux/Mac) ve düzenleyin.
  `.env` git'e eklenmez.

## 2. Telegram Botu

1. Telegram'da **@BotFather** > `/newbot` > bot adı ve kullanıcı adı verin > **token**'ı kopyalayın.
2. Yeni botunuza mesaj atın (`/start`).
3. Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` açın; `"chat":{"id": 123456789 ...}` değeri **chat ID**'dir.
4. Grup/kanal kullanacaksanız botu ekleyip aynı yöntemle (negatif) chat ID'yi alın.

## 3. `.env` Dosyası

Doldurmanız gerekenler: `API_KEY` (üretmek için `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`),
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Diğer ayarlar `deploy/env.production.example` içinde açıklamalıdır.

* `NOTIFY_ON_FIRST_RUN=false` kalsın: boş veritabanındaki ilk taramada bulunan yüzlerce mevcut ilan için mesaj
  gönderilmez, yalnızca bundan sonra çıkan ilanlar bildirilir.
* `TELEGRAM_NOTIFY_FILTER=p3_or_it` varsayılandır; bkz. [[notifications]].

## 4. Portal Erişim Testi (başlatmadan önce)

```bash
docker compose build
docker compose run --rm kpss-tracker python scripts/check_portals.py
```
Her portal için `OK`/`FAIL`, ilan sayısı, süre ve makinenin çıkış IP'si yazılır. Betik veritabanına yazmaz ve
Telegram'a mesaj göndermez. Hepsi `OK` değilse "Sorun Giderme" bölümüne bakın.

## 5. Başlatma

```bash
docker compose up -d
docker compose ps                      # STATUS: Up ... (healthy)
docker compose logs -f --tail=50       # canlı log (Ctrl+C ile çık)
```
Makine yeniden başlasa bile uygulama kendiliğinden açılır (`restart: unless-stopped`; Docker'ın açılışta
başlaması gerekir: Linux'ta `sudo systemctl enable docker`, Docker Desktop'ta "Start when you sign in").
Açılıştan 20 saniye sonra ilk tarama yapılır, sonra her 15 dakikada bir.

**Telegram testi:**
```bash
curl -s -X POST -H "X-API-Key: <API_KEY>" http://127.0.0.1:8000/api/settings/telegram/test
# {"success":true,...}  ve Telegram'da "bağlantı kuruldu" mesajı gelmelidir
```

## 6. Web Arayüzü

Servis yalnızca `127.0.0.1:8000`'de dinler (güvenli varsayılan); makinenin tarayıcısında `http://127.0.0.1:8000`
açılır. Uzak bir Linux makinedeyse SSH tüneli kullanın: `ssh -L 8000:127.0.0.1:8000 kullanici@makine`.
"Şimdi Tara" gibi yönetim işlemleri API anahtarınızı sorar. Bildirimler web arayüzünden bağımsız çalışır.

## 7. İşletme

| İş | Komut |
|---|---|
| Durum | `docker compose ps` |
| Log | `docker compose logs --tail=100` ve `logs/app.log` |
| Yeniden başlat | `docker compose restart` |
| Güncelle | yeni kodu alın (`git pull`) sonra `docker compose up -d --build` |
| Durdur | `docker compose down` (veri `data/` içinde korunur) |

**Yedekler:** her gün 04:00'te (TRT) `data/backups/kpss_backup_*.db` oluşur, en yeni 7 tanesi saklanır
(SQLite online yedek: uygulama çalışırken tutarlıdır). Dosyaları düzenli olarak başka bir yere kopyalayın.

**Geri yükleme:** `docker compose down`, yedeği `data/kpss_atama.db` olarak kopyalayın (Linux'ta
`sudo chown 1000:1000 data/kpss_atama.db`; varsa `kpss_atama.db-wal` ve `-shm` dosyalarını silin), `docker compose up -d`.

**Arıza uyarısı:** bir portal art arda 3 taramada (≈45 dk) veri veremezse Telegram'a **tek** uyarı gelir, düzelince
**tek** "yeniden çalışıyor" mesajı gelir. Böylece sessizce yeni ilan kaçırmazsınız. Makine kapalıysa uyarı da gelmez;
7/24 açık kalması sizin sorumluluğunuzdadır.

## 8. Sorun Giderme

* **`check_portals.py` bazı portallarda FAIL (403/406/zaman aşımı):** IP engelleniyor olabilir (yurt dışı/veri
  merkezi IP'si). Seçenekler:
  1. Uygulamayı Türkiye'deki bir ev bağlantısında veya Türkiye'deki bir VPS'te çalıştırmak (önerilen).
  2. Türkiye çıkışlı bir proxy kullanmak: portal istekleri (httpx) `HTTPS_PROXY` ortam değişkenini kullanır;
     Telegram'ın proxy'den geçmemesi için `NO_PROXY=api.telegram.org` ekleyin. Chromium (yalnızca İlan.gov.tr) bu
     değişkeni kullanmaz, o portal için ayrıca `--proxy-server` ayarı gerekir (kod değişikliği).
  Engelli portal dışındakiler normal çalışır; arıza uyarısı hangi portalın etkilendiğini söyler.
* **Konteyner sürekli yeniden başlıyor:** `docker compose logs --tail=100`; sık neden `.env` hatası veya `data/`
  yazma izni (`sudo chown -R 1000:1000 data logs`).
* **İlan.gov.tr sürekli FAIL, diğerleri OK:** bellek yetersizliği olabilir (`free -h`); Chromium için en az ~1 GB boş RAM gerekir.
* **Telegram mesajı gelmiyor:** `/api/settings` çıktısında `telegram_configured` ve `telegram_enabled` true olmalı;
  test uç noktasını çalıştırın; chat ID'nin doğru olduğunu ve bota `/start` yazdığınızı kontrol edin.
* **Disk doluyor:** log ve Docker logları sınırlıdır (10 MB × 3); `docker system prune -f` eski imajları temizler.

Bağlantılar: [[security]], [[notifications]], [[scrapers]]
