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
    "conversationId":"bridge-zhiliao-retest",
    "content":"再次测试：请直接处理以下 2 条 detail 链接，并返回每条链接对应的三层结果，重点是第三层原始公告页链接。不要回复已收到。\\n1) https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html\\n2) https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html",
    "metadata":{
      "priority":"high",
      "purpose":"zhiliao-retest",
      "instruction":"return-third-layer-links",
      "links":[
        "https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html",
        "https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html"
      ]
    }
  }'
