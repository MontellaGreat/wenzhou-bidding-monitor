#!/usr/bin/env bash
set -euo pipefail
cd /home/admin/.openclaw/workspace/services/bot-bridge
if ! pgrep -f '/home/admin/.openclaw/workspace/services/bot-bridge/server-sqlite.js' >/dev/null; then
  /home/admin/.openclaw/workspace/services/bot-bridge/start-bot-bridge.sh
fi
