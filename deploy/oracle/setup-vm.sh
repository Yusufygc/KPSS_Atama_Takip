#!/usr/bin/env bash
# KPSS Atama Takip - Oracle Cloud (Always Free) Ubuntu VM ilk kurulum betiği.
#
# Ubuntu 22.04/24.04 (ARM64 "Ampere A1" veya AMD) üzerinde, VM'e SSH ile bağlandıktan sonra çalıştırılır:
#     bash deploy/oracle/setup-vm.sh
#
# Yaptıkları: Docker + Compose kurar, düşük RAM için swap ekler, veri dizinlerini hazırlar.
# Yapmadıkları: .env dosyasını SİZ oluşturursunuz (token/anahtarlar betiğe yazılmaz).
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Bu betiği root olarak değil, normal kullanıcınızla (ubuntu) çalıştırın; gerektiğinde sudo ister." >&2
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo ">> Proje dizini: $PROJECT_DIR"

echo ">> Paketler güncelleniyor ve Docker kuruluyor..."
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-v2 curl ca-certificates
sudo systemctl enable --now docker       # VM yeniden başlayınca Docker (ve restart: unless-stopped konteyner) otomatik açılır
sudo usermod -aG docker "$USER" || true

# Chromium (İlan.gov.tr) ve Python birlikte 1 GB RAM'de zorlanır; 2 GB swap güvenlik ağıdır.
if ! swapon --show | grep -q '/swapfile'; then
  echo ">> 2 GB swap oluşturuluyor..."
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo ">> Veri dizinleri hazırlanıyor (konteyner kullanıcısı uid 1000)..."
mkdir -p "$PROJECT_DIR/data/backups" "$PROJECT_DIR/logs"
sudo chown -R 1000:1000 "$PROJECT_DIR/data" "$PROJECT_DIR/logs"

if [ ! -f "$PROJECT_DIR/.env" ]; then
  cp "$PROJECT_DIR/deploy/oracle/env.production.example" "$PROJECT_DIR/.env"
  chmod 600 "$PROJECT_DIR/.env"
  echo ">> .env oluşturuldu (örnekten). ŞİMDİ düzenleyin:  nano $PROJECT_DIR/.env"
fi

cat <<EOF

Kurulum tamam. Sıradaki adımlar (docs/wiki/deploy-oracle.md ile aynı):
  1) Oturumu yenileyin ki docker grubu geçerli olsun:  exit  (ve tekrar SSH ile bağlanın)
  2) .env dosyasını doldurun (TELEGRAM_*, API_KEY):      nano $PROJECT_DIR/.env
  3) Portal erişimini DENEYİN (başlatmadan önce):         cd $PROJECT_DIR && docker compose build && docker compose run --rm kpss-tracker python scripts/check_portals.py
  4) Hepsi OK ise başlatın:                               docker compose up -d
  5) Telegram bağlantısını sınayın (bkz. rehber "Telegram testi").
EOF
