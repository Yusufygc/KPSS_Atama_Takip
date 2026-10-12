"""KPSS Atama Takip - Portal erişim kontrolü (kurulumdan önce / sorun gidermede çalıştırılır).

Her portal için tek bir tarama yapıp sonucu özetler. Veritabanına YAZMAZ ve Telegram'a MESAJ GÖNDERMEZ;
yalnızca kazıyıcıları çalıştırır. Özellikle Türkiye dışındaki sunucularda (örn. Oracle Cloud Frankfurt)
kamu portallarının erişimi engelleyip engellemediğini kurulumdan ÖNCE anlamak için kullanılır.

Kullanım:
    python scripts/check_portals.py
    docker compose run --rm kpss-tracker python scripts/check_portals.py

Çıkış kodu: 0 = tüm portallar çalıştı, 1 = en az biri başarısız.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import httpx  # noqa: E402

from app.scrapers.orchestrator import ScraperOrchestrator  # noqa: E402

BLOCK_HINTS = ("403", "406", "429", "engellen", "Forbidden", "timed out", "zaman aşımı", "SSL", "certificate")
EGRESS_IP_URL = "https://api.ipify.org"


async def detect_egress_ip() -> str:
    """Sunucunun internete çıkış IP'sini (en iyi çaba ile) döner."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            return (await client.get(EGRESS_IP_URL)).text.strip()
    except Exception:  # noqa: BLE001 - yalnızca bilgi amaçlı
        return "bilinmiyor"


async def main(as_json: bool) -> int:
    started = time.perf_counter()
    ip_task = asyncio.create_task(detect_egress_ip())
    results = await ScraperOrchestrator().run_all()
    egress_ip = await ip_task

    rows = []
    for portal_key, items, status in results:
        rows.append(
            {
                "portal": str(getattr(portal_key, "value", portal_key)),
                "ok": status.status == "success" and len(items) > 0,
                "status": status.status,
                "found": len(items),
                "ms": round(status.duration_ms),
                "error": status.error_message,
            }
        )

    failed = [r for r in rows if not r["ok"]]
    if as_json:
        print(json.dumps({"egress_ip": egress_ip, "results": rows}, ensure_ascii=False, indent=2))
        return 1 if failed else 0

    print(f"Çıkış IP: {egress_ip}   |   toplam süre: {time.perf_counter() - started:.1f} sn\n")
    print(f"{'PORTAL':<20}{'DURUM':<10}{'İLAN':>6}{'SÜRE':>9}   HATA")
    for r in rows:
        mark = "OK  " if r["ok"] else "FAIL"
        print(f"{r['portal']:<20}{mark:<10}{r['found']:>6}{r['ms']:>7}ms   {(r['error'] or '')[:70]}")

    if failed:
        print(f"\n{len(failed)} portal başarısız.")
        if any(any(h.lower() in (r["error"] or "").lower() for h in BLOCK_HINTS) for r in failed):
            print(
                "İpucu: hata mesajları erişim engeline işaret ediyor olabilir. Bazı kamu siteleri yurt dışı veya "
                "veri merkezi IP'lerini engeller; sunucunuzu Türkiye'den erişilebilen bir konuma taşımayı veya "
                "Türkiye çıkışlı bir proxy kullanmayı düşünün (docs/wiki/deploy-oracle.md > Sorun Giderme)."
            )
        return 1
    print("\nTüm portallar erişilebilir.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main("--json" in sys.argv)))
