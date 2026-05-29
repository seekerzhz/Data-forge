# DataForge（精简并发版）

DataForge 是一个最小可用的 Web 工具，用于把题面 Markdown 转成可下载的 Hydro 风格数据包：

- 前端持续提交题面，不阻塞后续输入；
- 后端使用 LLM 润色题面、生成数据生成器与标准解；
- 后台并发运行任务，实时返回阶段进度；
- 任务完成后自动打包 ZIP 并触发下载。

---

## 1. 项目结构

```text
.
├── core/                 # 题面解析、LLM 调用、生成器/标准解构建、沙箱运行、打包流水线
├── prompts/              # LLM prompt 模板
├── webui/                # FastAPI 路由、任务队列、前端静态资源
│   ├── static/
│   │   ├── app.js        # 前端任务提交、轮询、进度条与下载逻辑
│   │   ├── styles.css    # iOS 扁平风格与字体栈
│   │   └── fonts/        # 可放置授权的内置字体文件
│   ├── app.py            # Web 路由与静态资源挂载
│   ├── schemas.py        # 请求模型
│   └── task_queue.py     # 后台队列、任务状态与进度数据流
├── webapp.py             # uvicorn 兼容入口
├── requirements.txt
└── setup.sh
```

数据流：

```text
浏览器表单
  -> POST /tasks
  -> TaskQueue 写入 waiting 状态并入队
  -> worker 调用 ForgeService.run_with_statement(progress=...)
  -> ForgeService 在每个阶段回调进度
  -> GET /tasks/{task_id} 返回 status/progress/percent
  -> 前端更新状态文字与扁平进度条
  -> done 后 GET /download/{task_id} 自动下载
```

---

## 2. 环境准备

- Python 3.10+
- Linux / macOS（`resource` 沙箱依赖 Unix）
- 可用的 LLM API Key（Ark / OpenAI / OpenAI-Compatible）

安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

也可以运行：

```bash
./setup.sh
```

---

## 3. 环境变量配置

请在项目根目录创建 `.env` 文件，或运行 `./setup.sh` 生成模板：

```env
# Provider: ark / openai / openai_compatible
LLM_PROVIDER=ark

# Ark
ARK_API_KEY=your-ark-key
ARK_MODEL=doubao-seed-1-6-250615
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# OpenAI
# OPENAI_API_KEY=your-openai-key
# OPENAI_MODEL=gpt-4o-mini

# OpenAI-Compatible（支持 DeepSeek / 通义千问 / 智谱 / Groq 等）
# OPENAI_COMPAT_API_KEY=your-compat-key
# OPENAI_COMPAT_BASE_URL=https://api.deepseek.com/v1
# OPENAI_COMPAT_MODEL=deepseek-chat
```

说明：

- 启动 Web 首页不再立即初始化 LLM；真正提交任务后，后台 worker 才会创建 `ForgeService`。
- `.env` 已加入 `.gitignore`，不会被提交到仓库。

常见 `OPENAI_COMPAT_MODEL` 示例：

- DeepSeek：`deepseek-chat`、`deepseek-reasoner`
- 阿里通义千问：`qwen-plus`、`qwen-turbo`
- 智谱：`glm-4-plus`、`glm-4-flash`
- Groq（常见开源模型）：`llama-3.3-70b-versatile`、`mixtral-8x7b-32768`

---

## 4. 启动服务

```bash
uvicorn webapp:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开：

- `http://127.0.0.1:8000`

---

## 5. 前端与字体

页面遵循 iOS 7–9 扁平风格：纯白背景、极浅灰区块、1px 分割线、无阴影/毛玻璃/渐变。

字体策略：

1. 如果需要内置“汉仪文黑-85W / HYWenHei”风格字体，请把已授权的字体文件放到：
   - `webui/static/fonts/HYWenHei-85W.woff2`（推荐）
   - 或 `webui/static/fonts/HYWenHei-85W.ttf`
2. `webui/static/styles.css` 已声明 `@font-face`，会优先使用上述内置文件。
3. 如果没有放置字体文件，浏览器会自动回退到本机安装的 HYWenHei、`PingFang SC`、SF Pro、系统 UI 字体。

仓库不直接附带汉仪字体二进制文件，因为该字体通常需要单独授权后才能再分发。

---

## 6. 使用方式（持续提交，不阻塞）

页面支持：

1. 点击“新的题面”；
2. 粘贴题面并点“提交本题面”；
3. 任务进入后台队列，卡片显示状态文字和进度条；
4. 页面会立刻追加一张新的输入卡片，可继续粘贴下一题；
5. 每个任务完成后自动下载 ZIP；
6. 下载触发后任务状态变为 `finished`。

任务状态：

- `waiting`：排队中
- `processing`：处理中
- `done`：完成并准备自动下载
- `finished`：下载已触发，任务结束
- `failed`：失败

---

## 7. API 接口

### 提交单任务

`POST /tasks`

```json
{
  "pid": "P1001",
  "statement_markdown": "# P1001 A+B Problem\n\n## 题目描述\n...",
  "num_cases": 20
}
```

### 查询状态

`GET /tasks/{task_id}`

返回示例：

```json
{
  "status": "processing",
  "progress": "生成测试数据 6/20",
  "percent": 55
}
```

### 标记下载完成

`POST /tasks/{task_id}/finish`

### 下载结果

`GET /download/{task_id}`

---

## 8. 输出目录结构

每个任务在：

```text
workspace/tasks/<task_id>/
└── <pid 或 no_pid>/
    ├── source/
    │   ├── generator.py
    │   └── solution.cpp
    ├── testdata/
    │   ├── *.in
    │   └── *.out
    └── build/
        └── <zip-file>.zip
```

---

## 9. 常见问题

### 1) 提交后报缺少 API Key

确认 `.env` 在项目根目录，且 key 名称正确（`ARK_API_KEY`、`OPENAI_API_KEY` 或 `OPENAI_COMPAT_API_KEY`）。

### 2) 任务失败：未找到 `.in`

通常是 LLM 生成器脚本没有按预期产出输入文件，建议减小题目复杂度或增加题面约束描述。

### 3) 为什么下载没有弹窗

浏览器可能拦截自动下载。可在日志中复制 `/download/{task_id}` 手动打开。
