#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/admin/.openclaw/workspace"
STATE_DIR="$WORKDIR/data/bidding"
LAST_FILE="$STATE_DIR/zhiliao_last_run.ts"
INTERVAL_DAYS=${INTERVAL_DAYS:-3}
INTERVAL_SEC=$((INTERVAL_DAYS*86400))

mkdir -p "$STATE_DIR" "/home/admin/.openclaw/logs"

NOW=$(date +%s)
LAST=0
if [ -f "$LAST_FILE" ]; then
  LAST=$(cat "$LAST_FILE" 2>/dev/null || echo 0)
fi

# If not due yet, exit quietly
if [ "$LAST" -gt 0 ] && [ $((NOW - LAST)) -lt "$INTERVAL_SEC" ]; then
  exit 0
fi

LOG="/home/admin/.openclaw/logs/zhiliao-monitor-cron.log"
{
  echo "===== $(date '+%F %T') start ====="
  bash "$WORKDIR/scripts/run_zhiliao_monitor_send.sh"
  echo "===== $(date '+%F %T') done  ====="
} >> "$LOG" 2>&1

# Mark success time only if send command succeeded
echo "$NOW" > "$LAST_FILE"
