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
    "conversationId":"bridge-bidding-verification-round2",
    "content":"第二轮桥接验收测试：请对以下招投标监控结果做验证剥离。说明：当前数据源文件未提供可直接点击的公告URL，请基于项目标题、项目ID、发布时间、采购单位进行验证与三层剥离，并输出：1）项目识别层；2）验证层（可验证字段、缺失字段、风险点）；3）执行层（建议如何补齐详情链接/原文链接）。\\n\\n[项目1] 标题：浙江信诚项目管理有限公司关于温州市龙湾区第一人民医院零星修缮工程中标(成交)结果公告；项目ID：314885211；发布时间：2026-03-07 17:15:33；采购单位：温州市龙湾区第一人民医院。\\n[项目2] 标题：温州历程招标有限公司关于温州市公安局交通管理支队2026年交管支队工会会员疗休养项目中标(成交)结果公告；项目ID：314870378；发布时间：2026-03-07 11:00:52；采购单位：温州市公安局交通管理支队。\\n[项目3] 标题：温州市钰铖工程咨询有限公司关于2026年城乡道路设施提升工程LED、灯箱广告整治、人行道清障执法服务中标(成交)结果公告；项目ID：313649769；发布时间：2026-02-13 12:45:59；采购单位：平阳县横阳控股有限公司。",
    "metadata":{
      "priority":"high",
      "purpose":"bridge-acceptance-test-round2",
      "instruction":"验证剥离",
      "sourceDataset":[
        {"id":"314885211","publishTime":"2026-03-07 17:15:33","buyer":"温州市龙湾区第一人民医院"},
        {"id":"314870378","publishTime":"2026-03-07 11:00:52","buyer":"温州市公安局交通管理支队"},
        {"id":"313649769","publishTime":"2026-02-13 12:45:59","buyer":"平阳县横阳控股有限公司"}
      ]
    }
  }'
