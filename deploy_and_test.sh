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
sleep 1

echo ""
echo "=== Running squeezewatch for ${RUN_SECONDS}s on $REMOTE ==="
ssh "$REMOTE" "cd $REMOTE_DIR && python3 squeezewatch.py &>/dev/null & echo \$!; sleep $RUN_SECONDS; pkill -f squeezewatch.py 2>/dev/null || true"

echo ""
echo "=== Copying logs from $REMOTE ==="
mkdir -p "$LOG_DIR"
rsync -av "$REMOTE:$REMOTE_DIR/log.txt" "$REMOTE:$REMOTE_DIR/error.txt" "$REMOTE:$REMOTE_DIR/debug.txt" "$LOG_DIR/" 2>/dev/null || true

echo ""
echo "=== Logs saved to $LOG_DIR ==="
echo ""
echo "--- log.txt ---"
cat "$LOG_DIR/log.txt" 2>/dev/null || echo "(empty)"
echo ""
echo "--- error.txt ---"
cat "$LOG_DIR/error.txt" 2>/dev/null || echo "(empty)"
echo ""
echo "--- debug.txt (last 50 lines) ---"
tail -50 "$LOG_DIR/debug.txt" 2>/dev/null || echo "(empty)"
