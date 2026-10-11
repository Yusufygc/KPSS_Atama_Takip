# Bildirim ve Dağıtım Mekanizması (Notifications)

Bu doküman, yeni ilanların kullanıcıya Telegram üzerinden nasıl ulaştırılacağını, mükerrer önleme stratejisini ve bildirim formatlarını açıklar.

## 1. Telegram Bot Entegrasyonu

* **Protokol:** Telegram Bot API (`https://api.telegram.org/bot<TOKEN>/sendMessage`)
* **Konfigürasyon:** `.env` üzerinden `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID`.
* **HTML Mesaj Modu:** `parse_mode="HTML"` kullanılarak zengin ve tıklanabilir bildirimler.

## 2. Mükerrer Bildirim Önleme (Deduplication)

Her ilan sisteme girdiğinde benzersiz bir parmak izi (hash) üretilir:
`hash_id = SHA256(f"{source}_{title}_{url}_{deadline}")`

* Veritabanında `is_notified = 0` olan ilanlar tespit edilir.
* Telegram'a başarılı gönderim yapıldıktan sonra `is_notified = 1` ve `notified_at = UTC_NOW` olarak işaretlenir.
* Bir ilan daha önce gönderildiyse asla tekrar iletilmez.

## 3. Bildirim Şablonu

```
🔔 <b>YENİ KPSS ATAMA İLANI</b>

🏛 <b>Kurum:</b> Gelir İdaresi Başkanlığı
📌 <b>Pozisyon:</b> 860 Gelir Uzman Yardımcısı
🎯 <b>Puan Türü:</b> [P1 / P2 - Kariyer] (Öncelikli)
📅 <b>Son Başvuru:</b> 22.10.2026
🌐 <b>Kaynak:</b> Kamu İlan (SBB)

🔗 <a href="...">İlan Detayını Görüntüle ve Başvur</a>
```

## 4. İki Yönlü Etkileşim (İsteğe Bağlı)
* `/start` - Botu başlatma ve chat id alma.
* `/sonilanlar` - Son eklenen 5 ilanı listeleme.
* `/tara` - Anlık olarak tarayıcı motorunu çalıştırma.
* `/puan p3` - Sadece P3 ilanlarını filtreleme.

## Gönderim Akışı ve Sınırlar
* **Ayrı aşama:** İlanlar önce kaydedilir, bildirimler tarama sonunda `AnnouncementService._notify_pending` ile gönderilir.
* **İlk çalıştırma tabanı:** Boş veritabanında bulunan mevcut ilanlar sessizce "bildirildi" işaretlenir (`NOTIFY_ON_FIRST_RUN=true` ile kapatılabilir).
* **Döngü başı sınır:** En fazla `TELEGRAM_MAX_PER_CYCLE` (varsayılan 15) ilan öncelik sırasıyla (P3 > P1/P2 > genel) tek tek gönderilir; fazlası **tek özet mesajıyla** bildirilir.
* **Hız sınırı:** Mesajlar arası `TELEGRAM_SEND_INTERVAL_SECONDS` bekleme. HTTP 429'da `retry_after` kadar (en çok 30 sn) beklenip bir kez yeniden denenir.
* **Yeniden deneme:** Gönderilemeyen ilanlar bildirilmemiş kalır ve `TELEGRAM_RETRY_WINDOW_HOURS` (24 saat) içinde sonraki taramalarda tekrar denenir; daha eski kayıtlar yeniden gönderilmez.
* **Hata durumu:** Art arda 2 hata olursa o taramadaki kalan gönderimler bırakılır (Telegram kapalıyken uzun beklemeyi önler).
* **HTML ayrıştırma hatası** (400 "can't parse entities") durumunda mesaj etiketsiz düz metinle yeniden gönderilir; mesajlar 4096 karakterle sınırlanır.

Bağlantılar: [[rules]], [[architecture]], [[kpss_scoring]]
