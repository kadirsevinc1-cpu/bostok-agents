#!/bin/bash
# auto_update.sh — Her 5 dakikada GitHub'ı kontrol et, yeni commit varsa çek ve yeniden başlat.
# Kullanım: nohup bash scripts/auto_update.sh >> memory/autoupdate.log 2>&1 &

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/memory/main.pid"
LOG_FILE="$PROJECT_DIR/memory/bostok.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [auto_update] $1"
}

_use_systemd() {
    systemctl is-active bostok.service --quiet 2>/dev/null && return 0
    systemctl is-enabled bostok.service --quiet 2>/dev/null && return 0
    return 1
}

restart_main() {
    if _use_systemd; then
        log "Systemd servisi yeniden baslatiliyor..."
        sudo systemctl restart bostok.service
    else
        if [ -f "$PID_FILE" ]; then
            OLD_PID=$(cat "$PID_FILE")
            if kill -0 "$OLD_PID" 2>/dev/null; then
                log "Eski surec durduruluyor (PID: $OLD_PID)..."
                kill -TERM "$OLD_PID"
                for i in $(seq 1 15); do
                    sleep 1
                    kill -0 "$OLD_PID" 2>/dev/null || break
                done
                kill -0 "$OLD_PID" 2>/dev/null && kill -KILL "$OLD_PID" 2>/dev/null
            fi
            rm -f "$PID_FILE"
        fi
        sleep 2
        cd "$PROJECT_DIR"
        [ -f ".venv/bin/activate" ] && source .venv/bin/activate
        nohup python main.py >> "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        log "main.py baslatildi (PID: $(cat $PID_FILE))"
    fi
}

cd "$PROJECT_DIR"
log "Auto-update baslatildi. Proje: $PROJECT_DIR"

while true; do
    # GitHub'dan yeni commit var mı?
    git fetch origin main --quiet 2>/dev/null
    LOCAL=$(git rev-parse HEAD 2>/dev/null)
    REMOTE=$(git rev-parse origin/main 2>/dev/null)

    if [ -z "$LOCAL" ] || [ -z "$REMOTE" ]; then
        log "Git revizyon alinamadi, atlaniyor"
    elif [ "$LOCAL" != "$REMOTE" ]; then
        log "Yeni commit tespit edildi: $LOCAL -> $REMOTE"
        git pull origin main
        PULL_STATUS=$?
        if [ "$PULL_STATUS" -eq 0 ]; then
            log "Git pull basarili, sistem yeniden baslatiliyor..."
            restart_main
        else
            log "Git pull basarisiz (exit: $PULL_STATUS), yeniden baslatma iptal"
        fi
    fi

    # main.py sureci olmusse yeniden basalt (systemd yoksa)
    if ! _use_systemd; then
        if [ -f "$PID_FILE" ]; then
            CURRENT_PID=$(cat "$PID_FILE")
            if ! kill -0 "$CURRENT_PID" 2>/dev/null; then
                log "main.py sureci olmus (PID: $CURRENT_PID), yeniden baslatiliyor..."
                rm -f "$PID_FILE"
                restart_main
            fi
        else
            log "PID dosyasi yok, main.py baslatiliyor..."
            restart_main
        fi
    fi

    sleep 300  # 5 dakika bekle
done
