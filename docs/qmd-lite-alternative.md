# QMD 轻量替代方案

由于当前服务器内存不足，QMD 无法稳定安装。先落一个轻量替代组合，覆盖大部分常用需求。

## 组成

### 1. `scripts/qmd-lite-search.py`
本地全文检索器，适合搜索：
- MEMORY.md
- memory/YYYY-MM-DD.md
- docs/
- scripts/
- 其他文本文件

示例：
```bash
python3 scripts/qmd-lite-search.py "宣传部 温州 视频"
python3 scripts/qmd-lite-search.py "森空岛 自动签到" --top 10
```

### 2. `summarize`
用于长内容摘要：
```bash
export PATH="/home/admin/.npm-global/bin:$PATH"
summarize "https://example.com/article" --length short
summarize "/path/to/file.pdf" --length short
```

### 3. 文件化记忆
配合以下文件使用：
- `MEMORY.md`：长期记忆
- `SESSION-STATE.md`：当前任务状态
- `memory/YYYY-MM-DD.md`：每日原始记录
- `.learnings/`：错误与经验

## 建议工作流

### 搜索历史项目/偏好
```bash
python3 scripts/qmd-lite-search.py "关键词"
```

### 长文先摘要
```bash
summarize "URL或文件" --length short
```

### 高价值信息再写入记忆
- 长期偏好 → `MEMORY.md`
- 当前任务 → `SESSION-STATE.md`
- 每日记录 → `memory/YYYY-MM-DD.md`
- 错误/教训 → `.learnings/`

## 优势
- 不需要 4G+ 内存
- 不需要编译 `node-llama-cpp`
- 可立即使用
- 足够覆盖大多数“找记忆 / 找文档 / 找历史决策”的需求

## 局限
- 没有真正的向量语义搜索
- 没有 BM25 + rerank 那么高级
- 但胜在轻、稳、立刻能跑
