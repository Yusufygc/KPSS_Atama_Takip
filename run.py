"""KPSS Atama Takip Sistemi - Uygulama Başlatıcı (Runner)."""

import os
import sys
from pathlib import Path

import uvicorn

# `python run.py --test`: gerçek Telegram/veritabanı olmadan test ortamını (.env.test) kullanır.
# Ayarlar içe aktarılmadan ÖNCE seçilmelidir.
if "--test" in sys.argv:
    sys.argv.remove("--test")
    os.environ["APP_ENV_FILE"] = ".env.test"

# Proje kök dizinini ekle
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.config import settings  # noqa: E402

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 65)
    print("🏛️  KPSS ATAMA & PERSONEL ALIM TAKİP SİSTEMİ")
    print("=" * 65)
    print(f"📡 Web Dashboard: http://127.0.0.1:{settings.APP_PORT}")
    print(f"📚 REST API Docs: http://127.0.0.1:{settings.APP_PORT}/docs")
    print(f"⚙️  Ortam: {settings.APP_ENV} | Otomatik Tarama: Her {settings.SCRAPER_INTERVAL_MINUTES} dakikada bir")
    print("=" * 65)
    print("Uygulama çalışıyor... (Durdurmak için CTRL+C tuşlarına basınız)\n")

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
