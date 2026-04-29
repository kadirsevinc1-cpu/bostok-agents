#!/bin/bash
# start.sh — Bostok Agent Köyü'nü başlat (main.py + auto_update)
# Kullanım: bash scripts/start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

mkdir -p memory

# Virtualenv varsa aktive et
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtualenv aktif: venv"
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Virtualenv aktif: .venv"
fi

# Zaten calısıyor mu?
PID_FILE="memory/main.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Sistem zaten calisiyor (PID: $OLD_PID)"
        echo "Durdurmak icin: bash scripts/stop.sh"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# auto_update zaten calısıyor mu?
if pgrep -f "auto_update.sh" > /dev/null; then
    echo "auto_update.sh zaten calisiyor, yeniden baslatiliyor..."
    pkill -f "auto_update.sh"
    sleep 1
fi

# main.py'yi başlat
nohup python main.py >> memory/bostok.log 2>&1 &
MAIN_PID=$!
echo "$MAIN_PID" > "$PID_FILE"
echo "main.py baslatildi (PID: $MAIN_PID)"

# auto_update.sh'ı başlat
nohup bash scripts/auto_update.sh >> memory/autoupdate.log 2>&1 &
UPDATE_PID=$!
echo "auto_update baslatildi (PID: $UPDATE_PID)"

echo ""
echo "Sistem aktif!"
echo "Log izlemek icin: tail -f memory/bostok.log"
echo "Durdurmak icin:   bash scripts/stop.sh"
