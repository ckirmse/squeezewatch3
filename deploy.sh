#!/bin/bash
set -e

REMOTE=mario
REMOTE_DIR=sqz3
LOG_DIR=/tmp/mario-logs
RUN_SECONDS=30

echo "=== Syncing files to $REMOTE:$REMOTE_DIR/ ==="
rsync -av --exclude='log.txt' --exclude='error.txt' --exclude='debug.txt' \
          --exclude='NUVO Protocol.pdf' --exclude='CLAUDE.md' --exclude='todo' \
          --exclude='/home.py' \
          /Users/ckirmse/squeezewatch3/ "$REMOTE:$REMOTE_DIR/"

echo ""
echo "=== Killing any existing squeezewatch on $REMOTE ==="
ssh "$REMOTE" "pkill -f squeezewatch.py 2>/dev/null" || true
