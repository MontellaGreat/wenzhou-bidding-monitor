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
    "conversationId":"bridge-zhiliao-strip-final-retry",
    "content":"执行测试任务，不要回复“已收到任务”。请直接处理以下 2 条链接，并返回每条链接的三层结果，尤其是第三层原始公告页链接。\\n\\n1) https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html\\n2) https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html\\n\\n返回格式要求：\\n链接1：\\n- 第一层(detail)：...\\n- 第二层(content)：...\\n- 第三层(原始公告页)：...\\n\\n链接2：\\n- 第一层(detail)：...\\n- 第二层(content)：...\\n- 第三层(原始公告页)：...\\n\\n参考样本：detail → content → 原始公告页。验收标准：必须返回第三层原始公告页链接。",
    "metadata":{
      "priority":"high",
      "purpose":"zhiliao-link-strip-final-retry",
      "instruction":"return-third-layer-links-only",
      "retryOf":"task_0e30d9c9f511fc59",
      "links":[
        "https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html",
        "https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html"
      ]
    }
  }'
