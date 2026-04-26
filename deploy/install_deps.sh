#!/bin/bash
# Bağımlılık kurulumu — /opt/bostok_agents içinde çalıştır
set -e
cd /opt/bostok_agents

echo "=== Sanal ortam oluşturuluyor ==="
python3 -m venv .venv
source .venv/bin/activate

echo "=== Paketler kuruluyor ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== memory/ klasörü oluşturuluyor ==="
mkdir -p memory

echo "=== .env dosyası kontrol ediliyor ==="
if [ ! -f .env ]; then
    echo "!!! .env dosyası YOK — deploy/env_template.txt'i kopyalayıp doldurun:"
    echo "    cp deploy/env_template.txt .env && nano .env"
    exit 1
fi

echo "=== Kurulum tamam! Servisi başlatmak için: ==="
echo "    sudo cp deploy/bostok.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable bostok"
echo "    sudo systemctl start bostok"
