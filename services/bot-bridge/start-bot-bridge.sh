#!/usr/bin/env bash
set -euo pipefail
cd /home/admin/.openclaw/workspace/services/bot-bridge
if pgrep -f '/home/admin/.openclaw/workspace/services/bot-bridge/server-sqlite.js' >/dev/null; then
  exit 0
fi
export $(grep -v '^#' .env | xargs)
nohup /usr/bin/node /home/admin/.openclaw/workspace/services/bot-bridge/server-sqlite.js >> /home/admin/.openclaw/workspace/services/bot-bridge/bridge.log 2>&1 &
