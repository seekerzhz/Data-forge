# DataForge

DataForge 是一个轻量 Web 工具，用于把竞赛题面 Markdown 转换为可下载的 Hydro 风格数据包。它通过后台队列调用 LLM 生成测试数据生成器和标准解，再在受限沙箱中生成输入输出并打包 ZIP。

## 项目结构

```text
.
├── core/                     # 核心流水线模块
│   ├── generator.py          # 调用 LLM 生成 Python 数据生成器
│   ├── llm.py                # OpenAI / Ark / OpenAI-Compatible 客户端适配（含重试）
│   ├── models.py             # 题目元数据模型
│   ├── naming.py             # 用户输入与文件名安全净化
│   ├── runner.py             # 编译标准解并在沙箱中批量生成输出
│   ├── sandbox.py            # bubblewrap / rlimit 受限执行
│   ├── service.py            # 题面润色、解析、并行造数据、打包总编排
│   └── solution.py           # 调用 LLM 生成 C++17 标准解
├── prompts/                  # LLM prompt 模板
├── webui/
│   ├── app.py                # FastAPI 路由、鉴权、限流、SSE
│   ├── schemas.py            # 请求参数校验（含长度上限）
│   ├── security.py           # API Token 与限流
│   ├── task_queue.py         # 后台任务队列、TTL 清理、集中任务状态
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── js/
├── webapp.py                 # uvicorn 入口
├── requirements.txt          # 锁定版本的 Python 依赖
└── setup.sh / restart.sh     # 初始化与本机启动脚本
```

运行期产物写入 `workspace/tasks/` 与 `workspace/downloads/`（已 gitignore）。终态任务会按 `DATAFORGE_TASK_TTL_SECONDS` 自动清理。

## 如何运行

### 1. 准备环境

要求：

- Python 3.10+
- Linux（推荐安装 `bubblewrap` / `bwrap`）
- `g++`（用于编译 C++17 标准解）
- 可用的 DeepSeek、Ark、OpenAI 或 OpenAI-Compatible API Key

```bash
./setup.sh
# 或
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env`（`setup.sh` 可生成模板）：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_MODEL=deepseek-v4-pro

# 安全与性能（建议）
DATAFORGE_HOST=127.0.0.1
DATAFORGE_PORT=8000
DATAFORGE_API_TOKEN=please-change-me
DATAFORGE_RATE_LIMIT_PER_MINUTE=30
DATAFORGE_MAX_QUEUE_SIZE=50
DATAFORGE_TASK_TTL_SECONDS=3600
DATAFORGE_CASE_WORKERS=4
DATAFORGE_SANDBOX=auto
LLM_MAX_RETRIES=3
```

- 默认绑定 **127.0.0.1**，避免公网裸曝。
- 设置 `DATAFORGE_API_TOKEN` 后，API / 下载 / SSE 需要 Token；页面顶部可填写并保存在浏览器本地。
- `DATAFORGE_SANDBOX=auto` 时优先使用 `bwrap`（断网、可写目录仅限任务 workspace），否则回退到 rlimit。

### 3. 启动 Web 服务

```bash
source .venv/bin/activate
uvicorn webapp:app --host "${DATAFORGE_HOST:-127.0.0.1}" --port "${DATAFORGE_PORT:-8000}"
# 或
./restart.sh
```

浏览器打开 `http://127.0.0.1:8000`。

若必须对公网开放，请务必设置强 `DATAFORGE_API_TOKEN`，并用反向代理 / 防火墙限制来源；不要直接 `0.0.0.0` 裸绑。

## 主要数据流

```text
浏览器表单
  -> POST /tasks（鉴权 + 限流）
  -> TaskQueue 入队
  -> ForgeService：润色 / 解析 / 生成器 / 标准解
  -> 并行沙箱执行 generator.py --id N --output-dir testdata
  -> 沙箱运行 solution 生成 .out
  -> 打包 ZIP -> workspace/downloads/<task_id>/
  -> 前端 SSE `/tasks/{id}/events`（失败则指数退避轮询）
  -> GET /download/{task_id}
```

## API 简表

### `POST /tasks`

`num_cases`：`1..100`。`statement_markdown` 最长 100000 字符；`custom_solution` 最长 200000 字符。

### `GET /tasks/{task_id}` / `GET /tasks/{task_id}/events`

查询进度。公开字段仅含 `status` / `progress` / `percent` 及统计信息，不含内部路径。

### `GET /download/{task_id}`

下载 ZIP。iframe 下载可通过 `?token=` 传凭证。

### `POST /tasks/{task_id}/finish`

下载后标记 `finished`。
