"""KPSS Atama Takip - Test veritabanını örnek ilanlarla oluşturur.

Kullanım:
    python scripts/seed_test_db.py                  # data/test/kpss_test.db (varsa üzerine eklemez, atlar)
    python scripts/seed_test_db.py --reset          # dosyayı silip yeniden oluşturur
    python scripts/seed_test_db.py --db yol/dosya.db

Test ortamı (.env.test) kullanılır: Telegram kapalıdır ve gerçek veritabanı (kpss_atama.db) yazılamaz.
Tarihler bugüne göre üretildiği için süresi dolmuş / yaklaşan / uzak ilanlar her zaman örneklenir.
"""

import argparse
import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ["APP_ENV_FILE"] = ".env.test"  # ayarlar içe aktarılmadan önce seçilmeli

from app.config import LIVE_DATABASE_FILENAME, settings  # noqa: E402
from app.core.dates import today_in_turkey  # noqa: E402
from app.domain.schemas import AnnouncementCreate  # noqa: E402
from app.infrastructure.database.connection import init_database  # noqa: E402
from app.infrastructure.database.repository import AnnouncementRepository  # noqa: E402
from app.services.announcement_service import AnnouncementService  # noqa: E402

DEFAULT_DB = BASE_DIR / "data" / "test" / "kpss_test.db"

# (kaynak anahtarı, kaynak adı, başlık, kurum, pozisyon, son tarih (bugünden gün farkı veya hazır metin), bildirildi mi)
SAMPLES = [
    ("kariyer_kapisi", "Kariyer Kapısı (CBİKO)", "TÜRK PATENT VE MARKA KURUMU - SÖZLEŞMELİ BİLİŞİM PERSONELİ SINAV DUYURUSU (2026)", "TÜRK PATENT VE MARKA KURUMU", None, 10, False),
    ("kariyer_kapisi", "Kariyer Kapısı (CBİKO)", "BANKACILIK DÜZENLEME VE DENETLEME KURUMU - 15 SÖZLEŞMELİ BİLİŞİM PERSONELİ", "BANKACILIK DÜZENLEME VE DENETLEME KURUMU", None, 3, False),
    ("kariyer_kapisi", "Kariyer Kapısı (CBİKO)", "SAVUNMA SANAYİİ BAŞKANLIĞI - 22 SAVUNMA SANAYİİ UZMAN YARDIMCISI", "SAVUNMA SANAYİİ BAŞKANLIĞI", None, 0, True),
    ("kariyer_kapisi", "Kariyer Kapısı (CBİKO)", "ÇALIŞMA VE SOSYAL GÜVENLİK BAKANLIĞI - 5 YAZILIM MÜHENDİSİ", "ÇALIŞMA VE SOSYAL GÜVENLİK BAKANLIĞI", None, 21, True),
    ("kariyer_kapisi", "Kariyer Kapısı (CBİKO)", "SAĞLIK BAKANLIĞI - SİBER GÜVENLİK UZMANI ALIMI", "SAĞLIK BAKANLIĞI", None, -2, True),
    ("kamu_ilan_sbb", "Kamu İlan (SBB)", "ELEŞKİRT BELEDİYE BAŞKANLIĞI - 1 ÇÖZÜMLEYİCİ ALACAK", "ELEŞKİRT BELEDİYE BAŞKANLIĞI", "1 ÇÖZÜMLEYİCİ ALACAK", "12 Ekim - 26 Ekim", False),
    ("kamu_ilan_sbb", "Kamu İlan (SBB)", "ISPARTA SARIİDRİS BELEDİYE BAŞKANLIĞI - 5 ZABITA MEMURU ALIMI", "ISPARTA SARIİDRİS BELEDİYE BAŞKANLIĞI", "5 ZABITA MEMURU ALIMI", "7 Ekim - 22 Ekim", False),
    ("kamu_ilan_sbb", "Kamu İlan (SBB)", "ATATÜRK ÜNİVERSİTESİ - 7 SÖZLEŞMELİ PERSONEL ALIMI", "ATATÜRK ÜNİVERSİTESİ", "7 SÖZLEŞMELİ PERSONEL ALIMI", "1 Ekim - 8 Ekim", True),
    ("kamu_ilan_sbb", "Kamu İlan (SBB)", "ANKARA ÜNİVERSİTESİ - ÖĞRETİM ÜYESİ ALIM İLANI", "ANKARA ÜNİVERSİTESİ", "ÖĞRETİM ÜYESİ", "15 Ekim - 30 Ekim", True),
    ("iskur", "İŞKUR Kamu İlanları", "Özel Güvenlik Görevlisi (Silahsız) - T.C.MARMARA ÜNİVERSİTESİ REK.İDARİ MALİ İŞLER DAİRE BAŞK.", "T.C.MARMARA ÜNİVERSİTESİ REK.İDARİ MALİ İŞLER DAİRE BAŞK.", "Özel Güvenlik Görevlisi (Silahsız)", 4, False),
    ("iskur", "İŞKUR Kamu İlanları", "Büro İşçisi - KARAYOLLARI 12.BÖLGE MUHASEBE MÜDÜRLÜĞÜ", "KARAYOLLARI 12.BÖLGE MUHASEBE MÜDÜRLÜĞÜ", "Büro İşçisi", 4, True),
    ("iskur", "İŞKUR Kamu İlanları", "Araç Sürücüsü - TCK 123 ŞUBE ŞEFLİĞİ AĞRI", "TCK 123 ŞUBE ŞEFLİĞİ AĞRI", "Araç Sürücüsü", 2, True),
    ("yerel_yonetimler", "Yerel Yönetimler GM", "ISPARTA İLİ SARIİDRİS BELEDİYE BAŞKANLIĞINA KPSS-P3 PUANIYLA MÜHENDİS ALIMI İLANI", "ISPARTA SARIİDRİS BELEDİYE BAŞKANLIĞI", None, None, False),
    ("yerel_yonetimler", "Yerel Yönetimler GM", "İZMİR İLİ BORNOVA BELEDİYE BAŞKANLIĞI 4/B SÖZLEŞMELİ BİLGİSAYAR MÜHENDİSİ ALIMI", "BORNOVA BELEDİYE BAŞKANLIĞI", None, None, True),
    ("resmi_gazete", "T.C. Resmî Gazete", "İçişleri Bakanlığı Emniyet Genel Müdürlüğünden:", "İçişleri Bakanlığı Emniyet Genel Müdürlüğü", None, None, True),
    ("resmi_gazete", "T.C. Resmî Gazete", "Hitit Üniversitesi Rektörlüğünden:", "Hitit Üniversitesi Rektörlüğü", None, None, True),
    ("resmi_gazete", "T.C. Resmî Gazete", "Nevşehir İli Ortahisar Belediye Başkanlığından:", "Nevşehir İli Ortahisar Belediye Başkanlığı", None, None, False),
    ("ilan_gov_tr", "İlan.gov.tr (BİK)", "Trakya Üniversitesi Rektörlüğü Sözleşmeli Bilişim Personeli Alım İlanı", "Trakya Üniversitesi Rektörlüğü", None, None, False),
]


def build_dtos() -> list[AnnouncementCreate]:
    today = today_in_turkey()
    dtos = []
    for index, (key, name, title, institution, position, deadline, _notified) in enumerate(SAMPLES):
        if isinstance(deadline, int):
            deadline_text = (today + timedelta(days=deadline)).strftime("%d.%m.%Y")
        else:
            deadline_text = deadline
        is_pdf_source = key == "resmi_gazete"
        url = (
            f"https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/{today:%Y}/{today:%m}/{today:%Y%m%d}-4-{index + 1}.pdf"
            if is_pdf_source
            else f"https://example.test/{key}/ilan-{index + 1}"
        )
        dtos.append(
            AnnouncementCreate(
                source_key=key,
                source_name=name,
                title=title,
                institution=institution,
                position=position,
                url=url,
                pdf_url=url if is_pdf_source else None,
                publish_date=today.isoformat() if is_pdf_source else None,
                deadline_date=deadline_text,
                raw_content=f"{title} {position or ''}",
                stable_url=key != "kamu_ilan_sbb",
            )
        )
    return dtos


async def seed(db_path: Path, reset: bool) -> int:
    if db_path.name == LIVE_DATABASE_FILENAME:
        raise SystemExit(f"Güvenlik: '{LIVE_DATABASE_FILENAME}' gerçek veritabanıdır, test verisi yazılamaz.")
    if reset and db_path.exists():
        db_path.unlink()
        for suffix in ("-wal", "-shm"):
            db_path.with_name(db_path.name + suffix).unlink(missing_ok=True)

    await init_database(db_path)
    repository = AnnouncementRepository(db_path)
    if await repository.count_all() > 0:
        print(f"Veritabanı zaten dolu, atlandı: {db_path} (yeniden oluşturmak için --reset)")
        return 0

    service = AnnouncementService(repository=repository)  # yalnızca _build_entity için kullanılır
    entities = [service._build_entity(dto) for dto in build_dtos()]
    inserted = await repository.insert_new(entities)

    notified_ids = [e.id for e, sample in zip(inserted, SAMPLES, strict=True) if sample[6]]
    await repository.mark_as_notified(notified_ids)
    return len(inserted)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test veritabanını örnek ilanlarla oluşturur.")
    parser.add_argument("--db", type=Path, default=None, help="Hedef veritabanı dosyası")
    parser.add_argument("--reset", action="store_true", help="Varsa dosyayı silip yeniden oluştur")
    args = parser.parse_args()

    db_path = (args.db or (BASE_DIR / settings.DATABASE_PATH)).resolve()
    count = asyncio.run(seed(db_path, args.reset))
    if count:
        print(f"{count} örnek ilan eklendi: {db_path}")
        print("Başlatmak için: python run.py --test   (veya baslat-test.bat)")


if __name__ == "__main__":
    main()
