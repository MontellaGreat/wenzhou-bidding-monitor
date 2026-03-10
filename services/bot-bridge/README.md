# Bot Bridge Service

一个用于 **OpenClaw / 机器人之间任务中转** 的轻量桥接服务，支持：
- 任务入队
- 按 target 拉取 pending 任务
- 回写处理结果
- SQLite 持久化
- systemd 托管
- 日志轮转
- 健康检查与自动重启

> 当前仓库里保留的是一份“可交接、可复用”的桥接实现说明。
> 本地实例后续可删除，但代码与文档会保留在 GitHub 方便复用。

---

## 目录结构

```bash
services/bot-bridge/
├── .env                         # 本地环境变量（不应提交真实密钥）
├── README.md                    # 本说明
├── package.json
├── server.js                    # JSON 文件版
├── server-sqlite.js             # SQLite 持久化版（推荐）
├── start-bot-bridge.sh          # 启动脚本
├── check-bot-bridge.sh          # 基础检查脚本
├── monitor-bot-bridge.sh        # 定时健康检查 + 异常自动重启
├── rotate-bridge-log.sh         # 日志轮转脚本
├── create-test-task.sh          # 基础测试任务
├── create-acceptance-test-task.sh
├── create-bidding-verification-task.sh
├── create-zhiliao-strip-task.sh
├── create-zhiliao-strip-retry-task.sh
├── create-zhiliao-final-retry-task.sh
├── create-zhiliao-retest-task.sh
└── data/
    ├── bridge.sqlite            # SQLite 数据库
    └── tasks.json               # JSON 版数据文件
```

---

## 版本说明

### 1）`server.js`
- JSON 文件存储版
- 适合最小化试验
- 不适合长期稳定使用

### 2）`server-sqlite.js`
- SQLite 持久化版
- 支持更稳定的数据落盘
- **推荐正式使用**

---

## 环境变量

示例 `.env`：

```bash
BRIDGE_PORT=8787
BRIDGE_TOKEN=replace-with-your-token
```

启动前加载：

```bash
cd ~/.openclaw/workspace/services/bot-bridge
source .env
```

---

## 启动方式

### 手动启动

```bash
cd ~/.openclaw/workspace/services/bot-bridge
source .env
node server-sqlite.js
```

或：

```bash
cd ~/.openclaw/workspace/services/bot-bridge
source .env
npm start
```

### 启动脚本

```bash
bash ~/.openclaw/workspace/services/bot-bridge/start-bot-bridge.sh
```

---

## systemd 托管

本地部署时使用了如下 unit：

```ini
[Unit]
Description=OpenClaw Bot Bridge Service (SQLite)
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/.openclaw/workspace/services/bot-bridge
EnvironmentFile=/home/admin/.openclaw/workspace/services/bot-bridge/.env
ExecStart=/usr/bin/node /home/admin/.openclaw/workspace/services/bot-bridge/server-sqlite.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

常用命令：

```bash
sudo systemctl daemon-reload
sudo systemctl enable bot-bridge
sudo systemctl start bot-bridge
sudo systemctl status bot-bridge
sudo systemctl restart bot-bridge
sudo systemctl stop bot-bridge
```

---

## 健康检查

```bash
curl http://127.0.0.1:${BRIDGE_PORT}/health
```

正常返回示例：

```json
{"ok":true}
```

---

## 鉴权

所有业务接口都需要：

```http
Authorization: Bearer ${BRIDGE_TOKEN}
```

---

## API 说明

### 1）创建任务

```bash
curl -X POST http://127.0.0.1:${BRIDGE_PORT}/tasks \
  -H "Authorization: Bearer ${BRIDGE_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "source":"openclaw-feishu",
    "target":"other-bot",
    "type":"message",
    "content":"请处理这条消息",
    "conversationId":"group-001",
    "metadata":{"priority":"normal"}
  }'
```

### 2）拉取待处理任务

```bash
curl "http://127.0.0.1:${BRIDGE_PORT}/tasks?target=other-bot&status=pending" \
  -H "Authorization: Bearer ${BRIDGE_TOKEN}"
```

### 3）查询单个任务

```bash
curl http://127.0.0.1:${BRIDGE_PORT}/tasks/task_xxx \
  -H "Authorization: Bearer ${BRIDGE_TOKEN}"
```

### 4）回写处理结果

```bash
curl -X POST http://127.0.0.1:${BRIDGE_PORT}/tasks/task_xxx/result \
  -H "Authorization: Bearer ${BRIDGE_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "status":"done",
    "result":"这是另一个机器人处理后的结果"
  }'
```

失败时也应回写：

```bash
curl -X POST http://127.0.0.1:${BRIDGE_PORT}/tasks/task_xxx/result \
  -H "Authorization: Bearer ${BRIDGE_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "status":"error",
    "result":"处理失败",
    "error":"失败原因"
  }'
```

---

## 数据文件

### SQLite 版

```bash
~/.openclaw/workspace/services/bot-bridge/data/bridge.sqlite
```

### JSON 版

```bash
~/.openclaw/workspace/services/bot-bridge/data/tasks.json
```

---

## 日志轮转

脚本：

```bash
services/bot-bridge/rotate-bridge-log.sh
```

本地策略：
- 日志大于 20MB 时切档
- 删除 7 天前旧日志

示例 cron：

```bash
*/30 * * * * /home/admin/.openclaw/workspace/services/bot-bridge/rotate-bridge-log.sh
```

---

## 自动监控与自修复

脚本：

```bash
services/bot-bridge/monitor-bot-bridge.sh
```

功能：
- 每 5 分钟检查一次 systemd 状态
- 调用 `/health` 做存活校验
- 异常时自动 `systemctl restart bot-bridge`
- 写入监控日志

示例 cron：

```bash
*/5 * * * * /home/admin/.openclaw/workspace/services/bot-bridge/monitor-bot-bridge.sh
```

---

## Worker 接入说明

当前桥接是 **pull 模式**，不是 push 模式。

也就是说，对端 worker 必须主动轮询：

```bash
GET /tasks?target=other-bot&status=pending
```

处理后再回写：

```bash
POST /tasks/{task_id}/result
```

如果不轮询，就会出现：
- 任务已入桥接
- 对端没有任何反应
- 任务一直停在 `pending`

### 推荐 worker 逻辑

```python
while True:
    tasks = fetch_pending_tasks(target="other-bot")
    if not tasks:
        sleep(5)
        continue

    for task in tasks:
        try:
            result = process_task(task["content"])
            post_result(task["id"], {"status": "done", "result": result})
        except Exception as e:
            post_result(task["id"], {"status": "error", "result": "处理失败", "error": str(e)})
```

---

## 本次实战里踩过的坑

### 1）内网地址不能直接做公网桥接入口
曾误用内网 IP，后续确认应使用公网地址访问。

### 2）对端 worker 只“签收”不“处理”
对端多次只回：
- 已收到任务
- 内容长度 xxx

说明它只是收件，不是真正执行任务内容。

### 3）对端 OpenClaw CLI 调用方式不兼容
曾出现：
- `openclaw run` 不存在
- `openclaw sessions spawn --runtime ...` 报 unknown option

这说明不同环境下 CLI 版本/参数并不一致，worker 不能想当然写死命令。

---

## 适用场景

适合：
- 两个 OpenClaw / Bot 之间做异步任务中转
- 需要一边投递、一边消费、一边回写结果
- 想做“人工监督 + 机器人执行”的中转层

不适合：
- 追求强实时 push 回调
- 高吞吐消息队列场景
- 长期复杂工作流编排（建议上更专业的队列/任务系统）

---

## 归档说明

当前这套桥接服务代码已整理入仓库，方便后续：
- 查阅
- 复用
- 二次改造
- 重新部署

如果本机实例后续删除，不影响 GitHub 中的归档版本。
