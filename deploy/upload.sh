#!/bin/bash
# Windows'tan sunucuya dosya gönder (Git Bash veya WSL ile çalıştır)
# Kullanım: bash deploy/upload.sh SUNUCU_IP KULLANICI_ADI
# Örnek:    bash deploy/upload.sh 34.123.45.67 kadir

SERVER_IP=${1:?"Kullanım: $0 SUNUCU_IP KULLANICI"}
USER=${2:-"$(whoami)"}
DEST="/opt/bostok_agents"

echo "=== $USER@$SERVER_IP:$DEST adresine gönderiliyor ==="

rsync -avz --progress \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='memory/*.json' \
  --exclude='memory/*.log' \
  --exclude='memory/seen_reply_uids.txt' \
  --exclude='.env' \
  --exclude='output/' \
  ./ "$USER@$SERVER_IP:$DEST/"

echo "=== Gönderim tamamlandı ==="
echo "Şimdi SSH ile bağlan ve install_deps.sh'ı çalıştır:"
echo "  ssh $USER@$SERVER_IP"
echo "  cd $DEST && bash deploy/install_deps.sh"
