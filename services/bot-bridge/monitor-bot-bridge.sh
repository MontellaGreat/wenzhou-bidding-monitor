#!/usr/bin/env bash
set -euo pipefail
OUT_LOG="/home/admin/.openclaw/workspace/services/bot-bridge/monitor.log"
TS=$(date '+%F %T')
ACTIVE=$(systemctl is-active bot-bridge 2>/dev/null || true)
HEALTH=$(curl -fsS http://127.0.0.1:8787/health 2>/dev/null || true)
if [ "$ACTIVE" != "active" ] || ! echo "$HEALTH" | grep -q '"ok": true'; then
  echo "[$TS] unhealthy detected: active=$ACTIVE health=$(echo "$HEALTH" | tr '\n' ' ')" >> "$OUT_LOG"
  sudo systemctl restart bot-bridge >> "$OUT_LOG" 2>&1 || true
  sleep 2
  ACTIVE2=$(systemctl is-active bot-bridge 2>/dev/null || true)
  HEALTH2=$(curl -fsS http://127.0.0.1:8787/health 2>/dev/null || true)
  echo "[$TS] after restart: active=$ACTIVE2 health=$(echo "$HEALTH2" | tr '\n' ' ')" >> "$OUT_LOG"
fi
