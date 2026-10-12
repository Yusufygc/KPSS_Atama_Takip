"""KPSS Atama Takip - konsolsuz (pythonw) Windows başlatıcısı.

Görev Zamanlayıcı bunu `venv\\Scripts\\pythonw.exe` ile çalıştırır: konsol penceresi ve görev çubuğu simgesi
açılmaz. Çıktı `logs/service.log` dosyasına yazılır. Elle: `venv\\Scripts\\pythonw.exe scripts\\windows\\service.pyw`
"""

import os
import runpy
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT = 8000
MAX_LOG_BYTES = 5 * 1024 * 1024

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


def _already_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", PORT)) == 0


def main() -> None:
    # Bu makinede zaten çalışıyorsa (örn. baslat.bat ile) ikinci kopya açma
    if _already_running():
        return

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "service.log"
    if log_path.exists() and log_path.stat().st_size > MAX_LOG_BYTES:
        log_path.unlink()

    # pythonw'de stdout/stderr/stdin yoktur; uvicorn ve print çağrıları için dosyaya yönlendirilir
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stdout = log_file
    sys.stderr = log_file
    sys.stdin = open(os.devnull, encoding="utf-8")  # noqa: SIM115

    # .env değerlerini ezer: yalnızca bu bilgisayardan erişim, otomatik yeniden yükleme kapalı
    os.environ["APP_HOST"] = "127.0.0.1"
    os.environ["APP_DEBUG"] = "false"
    os.environ["PYTHONUTF8"] = "1"

    runpy.run_path(str(ROOT / "run.py"), run_name="__main__")


main()
