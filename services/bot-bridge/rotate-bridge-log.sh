#!/usr/bin/env bash
set -euo pipefail
LOG_FILE="/home/admin/.openclaw/workspace/services/bot-bridge/bridge.log"
MAX_SIZE=$((20 * 1024 * 1024))
if [ -f "$LOG_FILE" ]; then
  SIZE=$(wc -c < "$LOG_FILE")
  if [ "$SIZE" -gt "$MAX_SIZE" ]; then
    TS=$(date +%F-%H%M%S)
    mv "$LOG_FILE" "${LOG_FILE}.${TS}"
    touch "$LOG_FILE"
  fi
fi
find /home/admin/.openclaw/workspace/services/bot-bridge -maxdepth 1 -type f -name 'bridge.log.*' -mtime +7 -delete
