# 招投标监控低成本版接入记录

## 时间
2026-03-09 15:58

## 调整内容
- 用户要求将知了标讯查询成本控制在固定次数
- 已确定最终查询结构：
  - 1 次主检索：`v2.api.subject.matter.bid.get`
  - 6 次详情补全：`v2.api.uk.bid.get`
  - 总计：7 次
- 已移除正文兜底接口：`v1.api.content.bid.get`
- 缺失字段统一输出为 `null`

## 新增脚本
- `scripts/run_zhiliao_monitor.sh`
  - 固化 `ZLBX_APP_ID`
  - 固化 `ZLBX_APP_SECRET`
  - 固化 `ZLBX_TOKEN`
  - 固化 `ZLBX_DETAIL_LIMIT=6`
  - 调用：`python3 scripts/wenzhou_bidding_zhiliao.py`

## 定时任务变更
- 任务：`温州招投标监控（每3天）`
- Job ID：`425f196a-7d1a-4326-bc32-b13b8f0432cd`
- 原 systemEvent：
  - `cd ~/.openclaw/workspace && python3 scripts/wenzhou_bidding_direct.py`
- 新 systemEvent：
  - `bash ~/.openclaw/workspace/scripts/run_zhiliao_monitor.sh`

## 当前策略
- 不再为地址/预算/联系方式做正文兜底补全
- 结果字段已足够，优先控制成本
- 后续如继续优化，只做排序和发送链路，不增加额外接口层级
