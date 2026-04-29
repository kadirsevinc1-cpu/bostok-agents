#!/bin/bash
# auto_update.sh — Her 5 dakikada GitHub'ı kontrol et, yeni commit varsa çek ve systemd ile yeniden başlat.
# Kullanım: nohup bash scripts/auto_update.sh >> memory/autoupdate.log 2>&1 &

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [auto_update] $1"
}

cd "$PROJECT_DIR"
log "Auto-update baslatildi. Proje: $PROJECT_DIR"

while true; do
    git fetch origin main --quiet 2>/dev/null
    LOCAL=$(git rev-parse HEAD 2>/dev/null)
    REMOTE=$(git rev-parse origin/main 2>/dev/null)

    if [ -z "$LOCAL" ] || [ -z "$REMOTE" ]; then
        log "Git revizyon alinamadi, atlaniyor"
    elif [ "$LOCAL" != "$REMOTE" ]; then
        log "Yeni commit: $LOCAL -> $REMOTE"
        git pull origin main
        if [ $? -eq 0 ]; then
            log "Git pull basarili, systemd yeniden baslatiliyor..."
            sudo systemctl restart bostok.service
            log "Restart komutu gonderildi"
        else
            log "Git pull basarisiz, yeniden baslatma iptal"
        fi
    fi

    sleep 300
done
