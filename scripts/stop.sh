#!/bin/bash
# stop.sh — Bostok Agent Köyü'nü durdur
# Kullanım: bash scripts/stop.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# auto_update.sh'ı durdur
if pgrep -f "auto_update.sh" > /dev/null; then
    pkill -f "auto_update.sh"
    echo "auto_update durduruldu"
else
    echo "auto_update zaten durmus"
fi

# main.py'yi durdur
PID_FILE="memory/main.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill -TERM "$PID"
        echo "main.py durduruldu (PID: $PID)"
        # 10 saniye bekle
        for i in $(seq 1 10); do
            sleep 1
            kill -0 "$PID" 2>/dev/null || break
        done
        kill -0 "$PID" 2>/dev/null && kill -KILL "$PID" && echo "Zorla kapatildi"
    else
        echo "main.py zaten durmus (PID: $PID)"
    fi
    rm -f "$PID_FILE"
else
    # PID dosyası yoksa isim ile bul
    pkill -f "python main.py" && echo "main.py durduruldu" || echo "main.py calismiyordu"
fi

echo "Sistem durduruldu."
