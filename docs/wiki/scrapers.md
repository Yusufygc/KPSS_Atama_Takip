# Kazıma Motoru ve Veri Kaynakları (Scrapers)

Bu doküman, sistemin veri topladığı 6 resmi kamu kaynağının teknik bağlantı parametrelerini, veri modellerini ve adaptör mantıklarını açıklar.

## 1. Desteklenen Portallar ve Teknik Protokoller

### 1. Kariyer Kapısı (`KariyerKapisiScraper`)
* **Kaynak:** T.C. Cumhurbaşkanlığı İnsan Kaynakları Ofisi (CBİKO)
* **Adres:** `https://kariyerkapisi.gov.tr/isealim`
* **Protokol:** Doğrudan REST JSON API (`POST https://api.kariyerkapisi.gov.tr/api/ilan/GetIseAlimPage`)
* **İstek Gövdesi:** `{"krM_ID": 0, "searchText": "", "il": "0", "ilanTuru": "0"}`
* **Veri:** Kurum Adı (`kurumAdi`), Birim Adı (`birimAdi`), İlan Başlığı (`ilanBaslik`), Bitiş Tarihi (`bitTarih`), Doğrudan Başvuru Linki (`basvuruLinki`), Guid.
* **Hız/Yük:** Yüksek hızlı, 0 HTML ayrıştırma maliyeti.

### 2. Resmi Gazete (`ResmiGazeteScraper`)
* **Kaynak:** T.C. Cumhurbaşkanlığı İdari İşler Başkanlığı
* **Adres:** `https://www.resmigazete.gov.tr/`
* **Protokol:** Deterministik Günlük Arşiv URL'si: `https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/{YIL}/{AY}/{YYYYAAGG}-4.htm`
* **İçerik:** Çeşitli İlanlar (Bölüm 4), tüm Bakanlık ve Üniversite personel alım ve sınav ilanlarını barındırır.
* **Veri:** Kurum adı, ilan konusu, ilgili PDF bağlantısı.

### 3. Kamu İlan SBB (`KamuIlanSbbScraper`)
* **Kaynak:** T.C. Cumhurbaşkanlığı Strateji ve Bütçe Başkanlığı
* **Adres:** `https://kamuilan.sbb.gov.tr/ilan_menu.aspx`
* **Protokol:** HTTP GET + BeautifulSoup (`span.black`, `span.patrol`, `span.h5date` etiketleri)
* **Karakter Kodlaması:** `utf-8` (Response `decode("utf-8", errors="replace")`)
* **Hotlink Koruması & Detay Sayfası:** `ilanDetay.aspx?kod=...` sayfası bir HTML sayfası değil, doğrudan ilgili ilanın resmi başvuru kılavuzu PDF belgesidir (`application/pdf`). Microsoft IIS sunucusu `Referer` başlığı doğrulaması yapar; `Referer: https://kamuilan.sbb.gov.tr/` başlığı bulunmayan harici yönlendirmelere 404 (Aradığınız sayfa bulunamadı) yanıtı döner.
* **Çözüm:** Sistemimiz `GET /api/announcements/{id}/document` asenkron proxy uç noktası üzerinden `Referer: https://kamuilan.sbb.gov.tr/` ile PDF belgesini indirip yerel `data/documents/` dizinine önbelleğe alır ve tarayıcıya kesintisiz akıtır. İstemciye doğrudan PDF görüntüleme ve SBB portalı ana sayfa linki sunulur.

### 4. Yerel Yönetimler GM (`YerelYonetimlerScraper`)
* **Kaynak:** Çevre, Şehircilik ve İklim Değişikliği Bakanlığı Yerel Yönetimler Genel Müdürlüğü
* **Adres:** `https://yerelyonetimler.csb.gov.tr/duyurular`
* **Protokol:** HTTP GET + BeautifulSoup
* **Kapsam:** Belediyelerin ilk defa atanmak üzere memur, zabıta memuru, itfaiye eri, mühendis alım ilanları.
* **Veri:** Tarih, belediye adı, alım unvanı, duyuru detay URL'si.

### 5. İŞKUR E-Şube (`IskurScraper`)
* **Kaynak:** Türkiye İş Kurumu
* **Adres:** `https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx`
* **Protokol:** Oturumlu (Session) HTTP POST + ViewState & EventValidation
* **Parametreler:** `ctl04$IsyeriTuruRadios=kamuRadio`, `__EVENTTARGET=ctl04$ctlAcikIsPageCommand$CommandItem_Search`
* **Veri:** Kamu işyeri adı, meslek unvanı, il/ilçe, açık pozisyon sayısı, son başvuru tarihi.

### 6. İlan.gov.tr (`IlanGovTrScraper`)
* **Kaynak:** Basın İlan Kurumu
* **Adres:** `https://www.ilan.gov.tr/ilan/tum-ilanlar/personel-alimi?ats=5`
* **Protokol:** Headless Browser (Chrome/Playwright) DOM Extraction
* **Veri:** İlan başlığı, kurum adı, kategori (Kamu-Akademik Personel), ilan URL'si.

## 2. Hata Toleransı ve İzolasyon

Her scraper adaptörü kendi try-catch bloğu içinde çalışır. Eğer bir site geçici olarak yanıt vermezse:
1. `ScraperException` fırlatılır ve loglanır.
2. Diğer 5 sitenin taraması ve veri akışı kesintiye uğramaz.
3. Hata durumu merkezi sağlık durumuna (Healthcheck DTO) yansıtılır.

Bağlantılar: [[rules]], [[architecture]], [[log]]


## Güncel Kazıma Notları (2026-10-12)
* **Kariyer Kapısı:** Detay bağlantısı `https://kariyerkapisi.gov.tr/IlanDetay?i=<guid>` biçimindedir. `/isealim/IlanDetay` portalın WAF'ında 406 ile engellenir.
* **İŞKUR:** Sonuç tablosu sabit kimlik son ekli span'lerden okunur (`ctlIsverenDL`, `ctlCalismaYeriDL`, `ctlSonBasvuruTarihi`, `Label9`). Sayfalama `btnNext` postback'iyle tüm sayfalar için yapılır; her ilan `AcikIsIlanDetay.aspx?uiID=<no>&isyeriTuru=Kamu` ile benzersiz URL alır.
* **Kamu İlan (SBB):** `ilanDetay.aspx?kod=` değeri her istekte değişen şifreli bir değerdir (eski değerler çalışmaya devam eder). Bu yüzden ilan kimliği URL'den değil `başlık + son tarih`ten üretilir (`stable_url=False`).
* **İlan.gov.tr:** Chrome/Edge/Chromium bulunamazsa kazıyıcı hata durumuna geçer (sessiz boş liste dönmez). Yol `BROWSER_EXECUTABLE_PATH` ile verilebilir.
