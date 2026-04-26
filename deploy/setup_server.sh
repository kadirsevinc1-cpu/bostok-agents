#!/bin/bash
# Bostok Agent Köyü — Sunucu kurulum scripti
# Ubuntu 22.04 LTS için
set -e

echo "=== Sistem güncelleniyor ==="
sudo apt-get update -y && sudo apt-get upgrade -y

echo "=== Python 3.12 kuruluyor ==="
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev \
    python3-pip git curl build-essential

echo "=== Python sembolik link ==="
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
python3 --version

echo "=== Proje klasörü oluşturuluyor ==="
sudo mkdir -p /opt/bostok_agents
sudo chown $USER:$USER /opt/bostok_agents

echo "=== Repo klonlanıyor ==="
# GitHub repon varsa: git clone https://github.com/KULLANICI/bostok_agents.git /opt/bostok_agents
# Yoksa: scp ile dosyaları gönder (bkz. deploy/upload.sh)
echo ">>> Repo klonlama adımını manuel tamamla (README'ye bak) <<<"

echo "=== Kurulum tamamlandı, sonraki adım: install_deps.sh ==="
