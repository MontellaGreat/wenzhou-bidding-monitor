#!/usr/bin/env bash
set -euo pipefail

FEISHU_TARGET="${FEISHU_TARGET:-ou_1e914047483f105cfd57f14f0db20746}"
CHANNEL="${CHANNEL:-feishu}"
WORKDIR="/home/admin/.openclaw/workspace"

cd "$WORKDIR"

# Run query (prints to stdout)
OUT=$(bash "$WORKDIR/scripts/run_zhiliao_monitor.sh" 2>&1 || true)

TS=$(date '+%F %T')
MSG="【温州招标监控（知了标讯）】${TS}\n\n${OUT}"

# Truncate to reduce risk of provider limits
MAX_CHARS=${MAX_CHARS:-18000}
if [ ${#MSG} -gt $MAX_CHARS ]; then
  MSG="${MSG:0:$MAX_CHARS}\n\n...(truncated)"
fi

openclaw message send \
  --channel "$CHANNEL" \
  --target "$FEISHU_TARGET" \
  --message "$MSG"
