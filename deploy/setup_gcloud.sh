#!/bin/bash
# Google Cloud VM ilk kurulum — Ubuntu 22.04 LTS
# Kullanım: bash deploy/setup_gcloud.sh
set -e

REPO="https://github.com/kadirsevinc1-cpu/bostok-agents.git"
DEST="/opt/bostok_agents"
USER=$(whoami)

echo "=== Sistem güncelleniyor ==="
sudo apt-get update -y && sudo apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    python3-pip git curl build-essential \
    libssl-dev libffi-dev

echo "=== Python sembolik link ==="
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

echo "=== Proje klasörü oluşturuluyor ==="
sudo mkdir -p $DEST
sudo chown $USER:$USER $DEST

echo "=== Repo klonlanıyor ==="
git clone $REPO $DEST
cd $DEST

echo "=== Sanal ortam + paketler ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== memory/ ve logs/ klasörleri ==="
mkdir -p memory logs output/sites output/demos

echo "=== .env dosyası oluştur ==="
cp deploy/env_template.txt .env
echo ""
echo "!!! ŞIMDI .env'i doldur: nano $DEST/.env"
echo "Sonra servisi kur:"
echo "  sudo cp $DEST/deploy/bostok.service /etc/systemd/system/bostok.service"
echo "  sudo sed -i 's/User=kadirsevinc1/User=$USER/' /etc/systemd/system/bostok.service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable bostok"
echo "  sudo systemctl start bostok"
echo "  sudo systemctl status bostok"
