"""KPSS Atama Takip - Merkezi Metin ve Şablon Tanımları."""

from enum import Enum


class PortalStrings:
    """Kamu kurum ve ilan portallarının standart adları."""

    KARIYER_KAPISI = "Kariyer Kapısı (CBİKO)"
    RESMI_GAZETE = "T.C. Resmî Gazete"
    KAMU_ILAN_SBB = "Kamu İlan (SBB)"
    YEREL_YONETIMLER = "Yerel Yönetimler GM"
    ISKUR = "İŞKUR Kamu İlanları"
    ILAN_GOV_TR = "İlan.gov.tr (BİK)"


class PortalKeys(str, Enum):
    """Portalların benzersiz sistem anahtarları."""

    KARIYER_KAPISI = "kariyer_kapisi"
    RESMI_GAZETE = "resmi_gazete"
    KAMU_ILAN_SBB = "kamu_ilan_sbb"
    YEREL_YONETIMLER = "yerel_yonetimler"
    ISKUR = "iskur"
    ILAN_GOV_TR = "ilan_gov_tr"


class MessageStrings:
    """Uygulama içi durum ve bilgi mesajları."""

    SCRAPER_STARTING = "{portal} taraması başlatılıyor..."
    SCRAPER_FINISHED = "{portal} taraması tamamlandı. Bulunan: {found}, Yeni Eklenen: {new}"
    SCRAPER_FAILED = "{portal} taramasında hata meydana geldi: {error}"
    ALL_SCRAPERS_COMPLETED = "Tüm kazıyıcılar çalıştırıldı. Toplam yeni ilan: {total_new}"
    NO_NEW_ANNOUNCEMENTS = "Yeni bir atama ilanı bulunamadı."
    ANNOUNCEMENT_SAVED = "Yeni ilan kaydedildi: [{portal}] {title}"
    NOTIFICATION_SENT = "Telegram bildirimi iletildi: {title}"
    TELEGRAM_DISABLED = "Telegram bildirimleri pasif durumda veya token girilmemiş."
    NOTIFY_BASELINE = "İlk çalıştırma: {count} mevcut ilan bildirim gönderilmeden işaretlendi."
    NOTIFY_SUMMARY = "Bildirim: {sent} ilan tek tek, {summarized} ilan özet olarak iletildi."
    NOTIFY_ABORTED = "Telegram art arda hata verdi, kalan bildirimler sonraki taramaya bırakıldı."


class ErrorStrings:
    """Merkezi hata mesajları ve açıklamaları."""

    NETWORK_TIMEOUT = "Bağlantı zaman aşımına uğradı ({url})."
    NETWORK_STATUS_ERROR = "Sunucu beklenmeyen bir durum kodu döndürdü ({status_code}): {url}"
    PARSING_FAILED = "HTML/JSON içeriği ayrıştırılamadı ({source}): {details}"
    RATE_LIMIT_EXCEEDED = "Hedef sunucu istek limitine takıldı (Rate Limit): {source}"
    DATABASE_ERROR = "Veritabanı işlemi başarısız: {details}"
    DUPLICATE_RECORD = "İlan veritabanında zaten mevcut: {hash_id}"
    NOTIFICATION_FAILED = "Telegram bildirimi gönderilemedi: {details}"
    VALIDATION_ERROR = "Veri doğrulama hatası: {field} - {issue}"
    API_KEY_INVALID = "Geçersiz veya eksik API anahtarı."
    API_KEY_NOT_CONFIGURED = "Prodüksiyonda API_KEY tanımlanmadan yönetim uç noktaları kullanılamaz."
    SCRAPE_ALREADY_RUNNING = "Bir tarama zaten çalışıyor, lütfen bitmesini bekleyin."
    DOCUMENT_HOST_NOT_ALLOWED = "Belge adresi izin verilen kaynaklar arasında değil."
    DOCUMENT_TOO_LARGE = "İlan belgesi izin verilen boyut sınırını aşıyor."
    BROWSER_NOT_FOUND = "Headless tarayıcı (Chrome/Edge/Chromium) bulunamadı."
    BROWSER_TIMEOUT = "Headless tarayıcı zaman aşımına uğradı."
    BROWSER_START_FAILED = "Headless tarayıcı başlatılamadı"


class NotificationStrings:
    """Telegram bildirim şablonları."""

    HEADER = "🔔 <b>YENİ KPSS ATAMA İLANI</b>"
    INSTITUTION = "🏛 <b>Kurum:</b> {institution}"
    POSITION = "📌 <b>Pozisyon:</b> {position}"
    SCORE_TYPE = "🎯 <b>Puan Türü:</b> {score_type}"
    DEADLINE = "📅 <b>Son Başvuru:</b> {deadline}"
    SOURCE = "🌐 <b>Kaynak:</b> {source}"
    LINK = '🔗 <a href="{url}">İlanı Görüntüle ve Başvur</a>'
    PDF_LINK = '📄 <a href="{pdf_url}">Resmî Gazete / İlan PDF</a>'
    SBB_PORTAL_LINE = "🏛️ <b>Resmi Portal:</b> https://kamuilan.sbb.gov.tr/"
    SBB_PORTAL_NOTE = (
        "<i>ℹ️ Not: SBB doğrudan dış bağlantı erişimini engellemektedir. "
        "İlan PDF belgesine web dashboard üzerinden veya SBB ana sayfasından erişebilirsiniz.</i>"
    )
    TEST_MESSAGE = (
        "🔔 <b>KPSS Atama Takip Sistemi</b>\n\n"
        "✅ Telegram bildirim bağlantısı başarıyla kuruldu!\n"
        "Yeni bir atama veya personel alım ilanı yayınlandığında anında buradan haberdar edileceksiniz."
    )
    SUMMARY = (
        "📬 <b>{count} ilan daha eklendi.</b>\n"
        "Hepsini web panelinden inceleyebilirsiniz (öncelikli ilanlar yukarıda gönderildi)."
    )
