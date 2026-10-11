# KPSS Puan Türleri ve Filtreleme Stratejisi (KPSS Scoring)

Bu doküman, sistemin ilanları kullanıcının KPSS puan profiline göre nasıl sınıflandıracağını ve önceliklendireceğini açıklar.

## 1. Kullanıcı Puan Profili

* **Öncelikli Puan:** **KPSS P3 (Lisans Genel)**
* **Aktif Takip Edilen Puanlar:** **KPSS P1 ve KPSS P2 (Genel Yetenek / Genel Kültür Ağırlıklı)**

## 2. Puan Türlerinin Anlamı ve Kadro Tipleri

### A. KPSS P3 (Lisans B Grubu ve Sözleşmeli Personel) - ⭐ Yüksek Öncelik
* **Kapsam:** Tüm lisans mezunlarının genel atamaları, 4/B sözleşmeli personel alımları, belediye memurlukları, bakanlıkların merkez ve taşra teşkilatları.
* **Tipik Unvanlar:**
  * Mühendis (Bilgisayar, Elektrik-Elektronik, Endüstri, Makine, İnşaat vb.)
  * Programcı, Çözümleyici, Sistem Yöneticisi
  * Büro Personeli, Veri Hazırlama ve Kontrol İşletmeni (VHKİ)
  * Zabıta Memuru, İtfaiye Eri (Belediyeler)
  * Kütüphaneci, Sosyolog, Psikolog
* **İlan Eşleşme İpuçları:** "P3", "KPSS P3", "KPSSP3", "Lisans Düzeyi KPSS", "B Grubu", "4/B Sözleşmeli".

### B. KPSS P1 ve P2 (A Grubu Kariyer Meslekleri) - 🎯 Hedefli Öncelik
* **Kapsam:** Bakanlıklar, Kurullar (SPK, BDDK, Rekabet Kurumu, RTÜK), Başkanlıklar (Savunma Sanayii, İletişim, Strateji ve Bütçe) ve Kalkınma Ajansları.
* **Tipik Unvanlar:**
  * Uzman Yardımcısı (Örn: Savunma Sanayii Uzman Yrd., İletişim Uzman Yrd., Gelir Uzman Yrd.)
  * Müfettiş Yardımcısı, Denetçi Yardımcısı
  * Meslek Personeli (BDDK, SPK)
  * Kalkınma Ajansı Uzman Personeli
* **İlan Eşleşme İpuçları:** "P1", "P2", "KPSS P1", "KPSSP1", "KPSS P2", "KPSSP2", "A Grubu", "Yarışma Sınavı", "Giriş Sınavı".

## 3. Otomatik Sınıflandırma ve Puanlama Algoritması

İlan metni (Başlık + Açıklama + PDF/Detay Metni) analiz edilir:

1. **Doğrudan Puan Eşleşmesi (Explicit Match):**
   * Metinde açıkça `KPSSP3` veya `P3` geçiyorsa -> **Tag: [P3 - Lisans]**, Öncelik: 100
   * Metinde `KPSSP1` veya `P1` geçiyorsa -> **Tag: [P1 - Kariyer]**, Öncelik: 80
   * Metinde `KPSSP2` veya `P2` geçiyorsa -> **Tag: [P2 - Kariyer]**, Öncelik: 80
2. **Unvan / Anahtar Kelime Çıkarımı (Implicit Match):**
   * Eğer puan türü metinde açıkça yazılmamışsa ancak "Mühendis", "Büro Personeli", "Zabıta" gibi lisans unvanları geçiyorsa varsayılan P3 olarak etiketlenir.
   * "Uzman Yardımcısı", "Müfettiş Yardımcısı" gibi kariyer unvanları geçiyorsa P1/P2/P3 ortak potansiyel olarak işaretlenir.
   * Anahtar kelimeler kelime başında aranır (`4/B` ifadesi `2024/B` içinde eşleşmez); sonek serbesttir (Mühendis -> Mühendisliği).
   * **Hariç tutulanlar:** Öğretim üyesi/görevlisi, araştırma görevlisi, doçent/profesör gibi akademik kadrolar ile sürekli/geçici işçi alımları örtük olarak P1/P2/P3 sayılmaz (açık `KPSS P3` yazısı varsa yine geçerlidir).
   * Açık yazım biçimleri: `KPSS P3`, `KPSSP3`, `KPSS-P3`, `KPSS (P3)`, `KPSS P-3`, `P-3`, `P3 puan`.
   * Kurallar değiştiğinde `SCORING_VERSION` (`connection.py`) artırılır; mevcut kayıtlar açılışta bir kez yeniden puanlanır.
3. **Kullanıcı Bildirim Filtresi:**
   * Kullanıcı ayarlarından "Sadece P3", "Sadece P1/P2", "Tümü" veya özel anahtar kelimeler seçilebilir.
   * Varsayılan mod: P3, P1 ve P2 ile uyumlu tüm ilanlar anında Telegram'a bildirilir.

Bağlantılar: [[rules]], [[architecture]], [[scrapers]]
