#!/usr/bin/env bash
set -euo pipefail
cd /home/admin/.openclaw/workspace/services/bot-bridge
source .env
curl -s http://127.0.0.1:${BRIDGE_PORT}/health
