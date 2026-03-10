#!/usr/bin/env bash
set -euo pipefail
cd /home/admin/.openclaw/workspace/services/bot-bridge
source .env
curl -s -X POST http://127.0.0.1:${BRIDGE_PORT}/tasks \
  -H "Authorization: Bearer ${BRIDGE_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "source":"openclaw-feishu",
    "target":"other-bot",
    "type":"message",
    "content":"知了剥链验收测试：请对以下内容执行三层剥离，并按层次返回结果。原文：请你对这段话做信息剥离、意图剥离、执行剥离，输出三层结构化结果。",
    "conversationId":"bridge-acceptance-test",
    "metadata":{"priority":"high","purpose":"acceptance-test","instruction":"三层剥离"}
  }'
