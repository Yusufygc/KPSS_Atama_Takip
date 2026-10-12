# KPSS Atama ve İlan Takip Sistemi - Bilgi Haritası (Wiki Index)

Hoş geldiniz. Bu dizin, KPSS Atama Takip Projesi'nin mimarisini, veri kaynaklarını, KPSS puan stratejilerini ve operasyonel kurallarını belgeleyen bilgi tabanıdır (LLM Wiki).

## 🗺️ Sayfa Haritası ve Kategoriler

### 1. Mimari & Tasarım Prensipleri
* [[architecture]]: Sistemin katmanlı mimarisi (Clean Architecture), tasarım desenleri (Adapter, Factory, Repository), asenkron işlem modeli ve veri akışı.
* [[rules]]: Proje anayasası, clean code prensipleri (SOLID, KISS, DRY), merkezi sabitler/ikonlar kuralı, loglama ve hata yönetimi standartları.

### 2. KPSS Stratejisi & Puan Türleri
* [[kpss_scoring]]: P3 (Öncelikli B Grubu / Lisans kadroları), P1 ve P2 (A Grubu / Kariyer / Uzman Yardımcılığı) puan türleri, eşleştirme algoritması ve anahtar kelime filtreleme mantığı.

### 3. Kazıma (Scraper) Motoru & Veri Kaynakları
* [[scrapers]]: Desteklenen 6 kamu portalının (Kariyer Kapısı, Resmi Gazete, Kamu İlan SBB, Yerel Yönetimler GM, İŞKUR, İlan.gov.tr) teknik protokolleri, kazıma yöntemleri ve hata kurtarma mekanizmaları.

### 4. Bildirim & Entegrasyon Katmanı
* [[notifications]]: Telegram Bot entegrasyonu, bildirim şablonları, mükerrer önleme (deduplication) mekanizması ve webhook/polling yapısı.

### 5. Güvenlik
* [[security]]: API anahtarı, XSS/SSRF korumaları, TLS, CORS, güvenlik başlıkları ve kapsayıcı sertleştirmesi.

### 6. Dağıtım
* [[deploy-oracle]]: Oracle Cloud Always Free üzerinde 7/24 çalıştırma, Telegram kurulumu, yedek ve sorun giderme.

### 7. Kayıt Defteri & Günlük
* [[log]]: Proje üzerinde gerçekleştirilen tüm önemli kararlar, mimari güncellemeler ve veri ekleme kayıtları.
