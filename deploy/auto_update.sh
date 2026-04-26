#!/bin/bash
# Bostok Agent — Otomatik güncelleme
# GitHub'da yeni commit varsa çeker ve servisi yeniden başlatır
cd /opt/bostok_agents

git fetch origin main --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Yeni güncelleme bulundu, çekiliyor..."
    git pull origin main --quiet
    source .venv/bin/activate
    pip install -r requirements.txt --quiet
    sudo systemctl restart bostok
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Servis yeniden başlatıldı."
fi
