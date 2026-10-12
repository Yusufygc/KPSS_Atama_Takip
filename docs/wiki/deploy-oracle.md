# Oracle Cloud (Always Free) Üzerinde Sürekli Çalıştırma

Bu rehber uygulamayı bir Oracle Cloud "Always Free" sanal makinesinde 7/24 çalıştırır ve yeni ilan çıktığında
Telegram'a bildirim gönderir. Uygulama internete yalnızca **dışarı** bağlanır (portallar + Telegram); sunucuda
dışarıya açık bir port gerekmez.

> **UYARI (2026-10-12 ölçümü): yurt dışı veri merkezleri iki ana kaynağa erişemiyor.**
> Herkese açık bir ağ denetleme servisiyle (check-host.net) portallar Frankfurt, Amsterdam, Zürih, Milano, Londra ve ABD veri merkezlerinden denendi:
>
> | Portal | Türkiye (İstanbul) | Yurt dışı veri merkezleri |
> |---|---|---|
> | Kamu İlan (SBB) | HTTP 200 | **403 Forbidden** (denenen tüm ülkelerde) |
> | Kariyer Kapısı API | ulaşılabiliyor | **bağlantı zaman aşımı** (tüm ülkelerde) |
> | İŞKUR, İlan.gov.tr, Resmî Gazete | 200 | 200 |
> | Yerel Yönetimler | 200 | karışık (çoğunda 200) |
>
> Yani Oracle'ın ücretsiz bölgelerinde (hepsi yurt dışı) en çok ilanı veren SBB ve Kariyer Kapısı çalışmaz. Oracle ancak Türkiye çıkışlı bir proxy ile kullanılabilir.
> Türkiye IP'li bir ortam (ev bilgisayarı/mini PC veya Türkiye'deki bir VPS) önerilir. Aşağıdaki adımlar (Docker + `setup-vm.sh` + `check_portals.py`) herhangi bir Ubuntu/Debian makinede de aynen geçerlidir.

## 0. Başlamadan Önce Bilmeniz Gerekenler

| Konu | Açıklama |
|---|---|
| **Coğrafi engel riski (en önemlisi)** | Oracle'ın ücretsiz bölgelerinde Türkiye yok (en yakınlar Frankfurt, Amsterdam, Zürih, Milano). Bazı Türk kamu siteleri yurt dışı veya veri merkezi IP'lerini engelleyebilir (Kariyer Kapısı zaten WAF ile 406 verebiliyor). Bu yüzden **önce `check_portals.py` ile deneyin** (adım 6). 6 portalın hepsi OK ise devam edin; değilse "Sorun Giderme"ye bakın. |
| **Boşta kalan makine geri alınabilir** | Oracle, uzun süre çok düşük CPU/ağ kullanan Always Free makineleri geri alabileceğini belgelerinde belirtir. Bu uygulama çoğu zaman boştur. Hesabı **Pay As You Go'ya yükseltmek** (Always Free limitleri içinde kaldıkça ücret çıkmaz) bu riski ortadan kaldırır; güncel koşulları Oracle'ın "Always Free Resources" belgesinden doğrulayın. |
| **Mimari** | Önerilen makine ARM tabanlı `VM.Standard.A1.Flex` (Ubuntu aarch64). Temel imaj (`python:3.12-slim`) ve Debian `chromium` paketi ARM64'ü destekler, ancak imajı yalnızca x86-64 üzerinde derleyip denedik; ARM'daki ilk `docker compose build` ve `check_portals.py` çıktısı bunun doğrulamasıdır. Sorun çıkarsa AMD (`VM.Standard.E2.1.Micro`) makine de çalışır (daha az RAM). |
| **RAM** | İlan.gov.tr için Chromium çalışır. A1'de 2 OCPU / 12 GB fazlasıyla yeterli. 1 GB'lık AMD makinede swap şarttır (betik ekler) ama sıkışabilir. |

## 1. Hesap ve Sanal Makine

1. <https://cloud.oracle.com> üzerinde hesap açın (kredi kartı doğrulaması ister). **Home Region** seçimi kalıcıdır; Avrupa'dan (Frankfurt / Amsterdam) birini seçin.
2. *Compute > Instances > Create instance*:
   * **Image:** Canonical Ubuntu 24.04 (veya 22.04)
   * **Shape:** Ampere → `VM.Standard.A1.Flex`, 2 OCPU / 12 GB RAM (Always Free sınırı toplam 4 OCPU / 24 GB)
   * **Networking:** yeni VCN, *Assign a public IPv4 address* açık
   * **SSH keys:** kendi anahtarınızı yükleyin veya Oracle'ın ürettiğini indirip saklayın
   * **Boot volume:** 50 GB yeterli
3. "Out of capacity for shape" hatası alırsanız birkaç saat sonra tekrar deneyin veya başka bir Availability Domain seçin.
4. **Güvenlik listesi (Security List):** varsayılan (yalnızca 22/SSH gelen) kalsın. Telegram/portal bağlantıları dışarı doğrudur, port açmanız gerekmez.

## 2. Kodu Sunucuya Aktarma

Proje şu an yalnızca yerel git deposunda. İki yol:

**A) Özel (private) GitHub deposu (güncellemeler için önerilir)**
```bash
# Yerelde, GitHub'da özel bir depo oluşturduktan sonra:
git remote add origin https://github.com/<kullanici>/<depo>.git
git push -u origin master
# Sunucuda:
git clone https://github.com/<kullanici>/<depo>.git kpss && cd kpss
```

**B) Arşiv ile doğrudan kopyalama (hesap gerekmez)**
```powershell
# Yerelde (PowerShell), proje klasöründe:
git archive --format=tar.gz -o kpss.tar.gz master
scp -i <anahtar.pem> kpss.tar.gz ubuntu@<SUNUCU_IP>:~
# Sunucuda:
mkdir -p kpss && tar xzf kpss.tar.gz -C kpss && cd kpss
```
`.env` ve `data/` git'e dahil değildir; arşive girmez.

## 3. İlk Kurulum

```bash
bash deploy/oracle/setup-vm.sh
exit            # docker grubunun geçerli olması için çıkıp tekrar SSH ile bağlanın
```
Betik Docker'ı kurar, açılışta otomatik başlatır, 2 GB swap ekler ve `.env` dosyasını örnekten oluşturur.

## 4. Telegram Botu

1. Telegram'da **@BotFather** > `/newbot` > bot adı ve kullanıcı adı verin > **token**'ı kopyalayın.
2. Yeni botunuza mesaj atın (`/start`).
3. Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` açın; `"chat":{"id": 123456789 ...}` değeri **chat ID**'dir.
4. Grup/kanal kullanacaksanız botu ekleyip aynı yöntemle (negatif) chat ID'yi alın.

## 5. `.env` Dosyası

```bash
nano .env
```
Doldurmanız gerekenler: `API_KEY` (üretmek için `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
Diğer ayarlar `env.production.example` içinde açıklamalıdır. **Önemli:** `NOTIFY_ON_FIRST_RUN=false` kalsın; boş veritabanındaki ilk taramada bulunan yüzlerce mevcut ilan için mesaj gönderilmez, yalnızca bundan sonra çıkan ilanlar bildirilir.

## 6. Portal Erişim Testi (başlatmadan önce)

```bash
docker compose build
docker compose run --rm kpss-tracker python scripts/check_portals.py
```
Örnek çıktı: her portal için `OK`/`FAIL`, ilan sayısı, süre ve sunucunun çıkış IP'si. Betik veritabanına yazmaz ve Telegram'a mesaj göndermez.
Hepsi `OK` değilse devam etmeden "Sorun Giderme" bölümüne bakın.

## 7. Başlatma

```bash
docker compose up -d
docker compose ps                      # STATUS: Up ... (healthy)
docker compose logs -f --tail=50       # canlı log (Ctrl+C ile çık)
```
Uygulama VM yeniden başlasa bile kendiliği yeniden açılır (`restart: unless-stopped` + Docker servisi etkin).
Açılıştan 20 saniye sonra ilk tarama yapılır, sonra her 15 dakikada bir.

### Telegram testi
```bash
curl -s -X POST -H "X-API-Key: <API_KEY>" http://127.0.0.1:8000/api/settings/telegram/test
# {"success":true,...}  ve Telegram'da "bağlantı kuruldu" mesajı gelmelidir
```

## 8. Web Arayüzüne Erişim (isteğe bağlı)

Servis yalnızca sunucuda `127.0.0.1:8000`'de dinler (güvenli varsayılan). Kendi bilgisayarınızdan **SSH tüneli** ile açın:
```bash
ssh -i <anahtar.pem> -L 8000:127.0.0.1:8000 ubuntu@<SUNUCU_IP>
# sonra tarayıcıda http://127.0.0.1:8000
```
"Şimdi Tara" gibi yönetim işlemleri API anahtarınızı sorar. Herkese açık HTTPS yayını istemiyorsanız başka bir şey yapmanız gerekmez;
bildirimler web arayüzünden bağımsız çalışır.

## 9. İşletme

| İş | Komut |
|---|---|
| Durum | `docker compose ps` |
| Log | `docker compose logs --tail=100` ve `logs/app.log` |
| Yeniden başlat | `docker compose restart` |
| Güncelle | yeni kodu aktarın (git pull veya yeni arşiv) sonra `docker compose up -d --build` |
| Durdur | `docker compose down` (veri `data/` içinde korunur) |

**Yedekler:** her gün 04:00'te (TRT) `data/backups/kpss_backup_*.db` dosyası oluşur, en yeni 7 tane saklanır (SQLite online yedek: uygulama çalışırken tutarlıdır). Bilgisayarınıza çekmek için:
```bash
scp -i <anahtar.pem> ubuntu@<SUNUCU_IP>:~/kpss/data/backups/kpss_backup_*.db ./yedekler/
```
**Geri yükleme:** `docker compose down`, yedeği `data/kpss_atama.db` olarak kopyalayın (`sudo chown 1000:1000 data/kpss_atama.db`; varsa `data/kpss_atama.db-wal` ve `-shm` dosyalarını silin), `docker compose up -d`.

**Arıza uyarısı:** bir portal art arda 3 taramada (≈45 dk) veri veremezse Telegram'a **tek** uyarı gelir, düzelince **tek** "yeniden çalışıyor" mesajı gelir. Böylece sessizce yeni ilan kaçırmazsınız.

### Mevcut veritabanını taşıma (isteğe bağlı)
Yerelde biriken ilanları sunucuya almak isterseniz (uygulama kapalıyken):
```bash
docker compose down
scp -i <anahtar.pem> data/kpss_atama.db ubuntu@<SUNUCU_IP>:~/kpss/data/
sudo chown 1000:1000 ~/kpss/data/kpss_atama.db && docker compose up -d
```
Eski kayıtlar için bildirim gitmez (yalnızca son 24 saatte eklenmiş ve bildirilmemiş kayıtlar yeniden denenir).

## 10. Sorun Giderme

* **`check_portals.py` bazı portallarda FAIL (403/406/zaman aşımı):** sunucu IP'si engelleniyor olabilir. Seçenekler:
  1. Başka bir Oracle bölgesi/VM denemek (IP bloğu değişir; ama hepsi yurt dışı olacaktır).
  2. Türkiye çıkışlı bir proxy kullanmak: portal istekleri (httpx) `HTTPS_PROXY` ortam değişkenini kullanır; Telegram'ın proxy'den geçmemesi için `NO_PROXY=api.telegram.org` ekleyin. Chromium (yalnızca İlan.gov.tr) bu değişkeni kullanmaz, o portal için ayrıca `--proxy-server` ayarı gerekir (kod değişikliği).
  3. Uygulamayı Türkiye'deki bir VPS'te veya evdeki bir cihazda (Raspberry Pi vb.) çalıştırmak.
  Engelli portal dışındakiler normal çalışır; arıza uyarısı hangi portalın etkilendiğini söyler.
* **Konteyner sürekli yeniden başlıyor:** `docker compose logs --tail=100`; sık neden `.env` hatası veya `data/` yazma izni (`sudo chown -R 1000:1000 data logs`).
* **İlan.gov.tr sürekli FAIL, diğerleri OK:** bellek yetersizliği olabilir (`free -h`); A1 makinede nadirdir. Geçici çözüm: portalı kullanmayın (kayıt defterinden çıkarmak için bir kod değişikliği gerekir, bize bildirin).
* **Telegram mesajı gelmiyor:** `/api/settings` çıktısında `telegram_configured` ve `telegram_enabled` true olmalı; test uç noktasını çalıştırın; chat ID'nin doğru olduğunu ve bota `/start` yazdığınızı kontrol edin.
* **Disk doluyor:** log ve Docker logları sınırlıdır (10 MB × 3); `docker system prune -f` eski imajları temizler.

Bağlantılar: [[security]], [[notifications]], [[scrapers]]
