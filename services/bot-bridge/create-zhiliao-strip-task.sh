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
    "conversationId":"bridge-zhiliao-strip-round2",
    "content":"第二轮桥接验收测试：请对以下知了标讯详情链接执行三层剥离。发送内容如下：\\n\\n温州招标监控（知了标讯）\\n[强相关 / 招标公告]\\n公告名称: 浙江公司2026年工作会议会务辅助服务采购（会议策划）公告\\n采购单位: 华润电力（温州）有限公司\\n详情链接:https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html\\n[强相关 / 招标公告]\\n公告名称: 华润置地森马实业(温州)有限公司美陈装置-温州万象城2026年10周年庆美陈制作采购事项公告\\n采购单位: 华润置地森马实业（温州）有限公司\\n详情链接:https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html\\n\\n要求：请把每个 detail 链接剥离到第三层，并返回三层结果。参考样本：第一层（detail）https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html ；第二层（content）https://www.zhiliaobiaoxun.com/content/588656357/b1 ；第三层（原始公告页）http://www.crpsz.com/zbxx/006002/006002001/20260306/DLXYGG202603060101.html 。最终请至少返回每条链接对应的第三层原始公告页链接。",
    "metadata":{
      "priority":"high",
      "purpose":"zhiliao-link-strip-round2",
      "instruction":"detail-to-content-to-origin",
      "links":[
        "https://www.zhiliaobiaoxun.com/detail/588656357b159A09310o.html",
        "https://www.zhiliaobiaoxun.com/detail/588724976b12D531074o.html"
      ]
    }
  }'
