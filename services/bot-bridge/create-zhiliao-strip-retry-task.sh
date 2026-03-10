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
    "conversationId":"bridge-zhiliao-strip-retry",
    "content":"纠偏重试任务：请重新处理，不要只回复“已收到任务”或“收到内容长度”。本次要求是实际完成链接剥离并返回结果。\\n\\n请处理以下 2 条知了标讯 detail 链接：\\n1. https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html\\n2. https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html\\n\\n处理要求：对每条链接执行三层剥离，并按以下格式返回：\\n- 第一层（detail）：原始 detail 链接\\n- 第二层（content）：对应 content 链接\\n- 第三层（原始公告页）：最终原文公告页链接\\n\\n注意：本次验收以“返回第三层原始公告页链接”为准，不接受仅确认收到任务。\\n\\n参考样本：\\n第一层（detail）https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html\\n第二层（content）https://www.zhiliaobiaoxun.com/content/588656357/b1\\n第三层（原始公告页）http://www.crpsz.com/zbxx/006002/006002001/20260306/DLXYGG202603060101.html",
    "metadata":{
      "priority":"high",
      "purpose":"zhiliao-link-strip-retry",
      "instruction":"must-return-third-layer-links",
      "retryOf":"task_94bc657015685f0b",
      "links":[
        "https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html",
        "https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html"
      ]
    }
  }'
