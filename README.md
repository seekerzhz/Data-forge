# DataForge

DataForge 是一个轻量 Web 工具，用于把竞赛题面 Markdown 转换为可下载的 Hydro 风格数据包。它通过后台队列调用 LLM 生成测试数据生成器和标准解，再在受限沙箱中生成输入输出并打包 ZIP。

## 项目结构

```text
.
├── core/                     # 核心流水线模块
│   ├── generator.py          # 调用 LLM 生成 Python 数据生成器
│   ├── llm.py                # OpenAI / Ark / OpenAI-Compatible 客户端适配
│   ├── models.py             # 题目元数据模型
│   ├── naming.py             # 用户输入与文件名安全净化
│   ├── runner.py             # 编译标准解并批量生成输出
│   ├── sandbox.py            # 受限资源环境中运行生成器
│   ├── service.py            # 题面润色、解析、生成、打包总编排
│   └── solution.py           # 调用 LLM 生成 C++17 标准解
├── prompts/                  # LLM prompt 模板
├── webui/
│   ├── app.py                # FastAPI 路由与静态资源挂载
│   ├── schemas.py            # 请求参数校验
│   ├── task_queue.py         # 后台任务队列与集中任务状态
│   └── static/
│       ├── index.html        # 页面模板
│       ├── styles.css        # 页面样式（不含鼠标光点/水波纹跟随效果）
│       ├── fonts/            # 可放置授权字体文件
│       └── js/
│           ├── api.js        # 后端 API 服务封装
│           ├── app.js        # 前端事件编排入口
│           ├── store.js      # 前端集中状态和轮询定时器管理
│           └── ui.js         # DOM 渲染、表单读取和可访问性绑定
├── webapp.py                 # uvicorn 入口
├── requirements.txt          # Python 依赖
└── setup.sh                  # 虚拟环境和 .env 模板初始化脚本
```

运行期产物会写入 `workspace/tasks/`，该目录已被 `.gitignore` 忽略。每个任务位于独立的 task id 目录下，内部问题目录和 ZIP 文件会优先使用题目名称；任务成功或失败结束后会清空对应的 `workspace/tasks/<task_id>/`。

## 如何运行

### 1. 准备环境

要求：

- Python 3.10+
- Linux / macOS（沙箱使用 Unix `resource` 限制）
- `g++`（用于编译 C++17 标准解）
- 可用的 Ark、OpenAI 或 OpenAI-Compatible API Key

安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

也可以执行：

```bash
./setup.sh
```

### 2. 配置环境变量

在项目根目录创建 `.env`：

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

# OpenAI-Compatible
# OPENAI_COMPAT_API_KEY=your-compat-key
# OPENAI_COMPAT_BASE_URL=https://api.deepseek.com/v1
# OPENAI_COMPAT_MODEL=deepseek-chat
```

### 3. 启动 Web 服务

```bash
uvicorn webapp:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开 `http://127.0.0.1:8000`。

## 主要数据流

```text
浏览器表单
  -> webui/static/js/ui.js 读取并校验输入
  -> webui/static/js/api.js POST /tasks
  -> webui.task_queue.TaskQueue 创建 waiting 状态并入队
  -> 后台 worker 懒加载 core.service.ForgeService
  -> ForgeService 润色题面、解析元数据、生成 generator.py / solution.cpp
  -> core.sandbox 在受限环境运行 generator.py 生成 .in
  -> core.runner 编译 solution.cpp 并为每个 .in 生成 .out
  -> core.service 打包 Hydro ZIP
  -> webui.task_queue 将 ZIP 移到 workspace/downloads/<task_id>/ 并清空 workspace/tasks/<task_id>/
  -> 前端轮询 GET /tasks/{task_id} 渲染进度
  -> done 后隐藏 iframe 请求 /download/{task_id}
  -> GET /download/{task_id} 响应完成后清理临时下载 ZIP
  -> POST /tasks/{task_id}/finish 标记任务 finished
```

前端采用单向数据流：用户事件由 `js/app.js` 接收，调用 `js/api.js` 或更新 `js/store.js`，最后通过 `js/ui.js` 统一渲染 DOM。后端的任务队列通过 `service_factory` 注入核心服务，便于替换或测试。

## API 简表

### `POST /tasks`

提交单个任务。`num_cases` 必须是 `1..100` 的整数。

```json
{
  "pid": "P1001",
  "statement_markdown": "# P1001 A+B Problem\n\n## 题目描述\n...",
  "num_cases": 20
}
```

### `GET /tasks/{task_id}`

查询任务状态。

```json
{
  "status": "processing",
  "progress": "生成测试数据 6/20",
  "percent": 55
}
```

### `GET /download/{task_id}`

下载生成好的 ZIP。任务尚未完成或文件不存在时返回 `404`。

### `POST /tasks/{task_id}/finish`

下载触发后将任务标记为 `finished`。

## 安全与边界处理

- 前后端均限制 `num_cases <= 100`，避免单次请求过度消耗资源。
- 用户输入的 `pid` 和题目标题在用于 workspace 目录名、ZIP 名称前会经过 `core.naming` 净化；文件名优先使用题目名称，仅在需要时加题号前缀，不再追加哈希。
- 每个任务结束后会删除对应的 `workspace/tasks/<task_id>/` 运行目录；成功任务的 ZIP 会临时移动到 `workspace/downloads/<task_id>/`，下载响应结束后自动清理。
- 生成器在 `core.sandbox` 中运行，限制 CPU、内存和输出文件大小。
- 前端不使用 `innerHTML` 渲染用户输入，状态文本通过 `textContent` 更新。
- 页面已删除鼠标移动光点和水波纹跟随效果，仅保留任务进度条动效。

## 字体说明

如需内置“汉仪文黑-85W / HYWenHei”风格字体，请将已授权字体文件放入：

- `webui/static/fonts/HYWenHei-85W.woff2`（推荐）
- `webui/static/fonts/HYWenHei-85W.ttf`

仓库不直接包含商业字体二进制文件；未放置字体时浏览器会回退到系统中文字体。
