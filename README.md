# DataForge（精简并发版）

一个最小可用的 Web 工具：
- 你粘贴题面 Markdown；
- 后端用 LLM 优化题面格式；
- 后台并发生成测试数据与标准解输出；
- 自动打包 ZIP 并触发下载。

---

## 1. 环境准备

- Python 3.10+
- Linux / macOS（`resource` 沙箱依赖 Unix）
- 可用的 LLM API Key（Ark / OpenAI / OpenAI-Compatible）

安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn webapp:app --host 0.0.0.0 --port 8000 --reload
```

---

## 2. 环境变量配置（必须）

请在项目根目录创建 `.env` 文件：

```env
# 可选 1：Ark
ARK_API_KEY=your-ark-key
ARK_MODEL=doubao-seed-1-6-250615
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 可选 2：OpenAI
# OPENAI_API_KEY=your-openai-key
# OPENAI_MODEL=gpt-4o-mini

# 可选 3：OpenAI-Compatible（支持 DeepSeek / 通义千问 / 智谱 / Groq 等）
# OPENAI_COMPAT_API_KEY=your-compat-key
# OPENAI_COMPAT_BASE_URL=https://api.deepseek.com/v1
# OPENAI_COMPAT_MODEL=deepseek-chat

# 统一 provider 开关（推荐）
# LLM_PROVIDER=openai_compatible
```

说明：
- 代码会自动读取 `.env`。
- `.env` 已加入 `.gitignore`，不会被提交到仓库。.

Provider 选择方式（推荐在 `.env` 里设置，不用改代码）：
- `ark`：火山引擎 Ark（默认）
- `openai`：OpenAI 官方
- `openai_compatible`：任意兼容 OpenAI Chat Completions 协议的服务

也就是说：修改 `.env` 中的 `LLM_PROVIDER` 即可切换 provider；不需要手动改 `LLMConfig` 代码。

常见模型示例（`OPENAI_COMPAT_MODEL` 可直接填写）：
- DeepSeek：`deepseek-chat`、`deepseek-reasoner`
- 阿里通义千问：`qwen-plus`、`qwen-turbo`
- 智谱：`glm-4-plus`、`glm-4-flash`
- Groq（常见开源模型）：`llama-3.3-70b-versatile`、`mixtral-8x7b-32768`

---

## 3. 启动服务

```bash
uvicorn webapp:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开：
- `http://127.0.0.1:8000`

---

## 4. 使用方式（持续提交，不阻塞）

页面支持：
1. 点击“添加题面”；
2. 粘贴题面并点“提交本题面”；
3. 立刻继续粘贴下一题（无需等待上一题完成）；
4. 每个任务完成后自动下载 ZIP；
5. 下载触发后任务状态变为 `finished`。

任务状态：
- `waiting`：排队中
- `processing`：处理中
- `done`：完成并准备自动下载
- `finished`：下载已触发，任务结束
- `failed`：失败

---

## 5. API 接口

### 提交单任务
`POST /tasks`

```json
{
  "pid": "P1001",
  "statement_markdown": "# P1001 A+B Problem\n\n## 题目描述\n...",
  "num_cases": 20
}
```

说明：前端页面默认会提交 `num_cases=20`，也可以手动改成你想要的组数。

### 查询状态
`GET /tasks/{task_id}`

### 下载结果
`GET /download/{task_id}`

---

## 6. 输出目录结构

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

## 7. 常见问题

### 1) 启动后报缺少 API Key
确认 `.env` 在项目根目录，且 key 名称正确（`ARK_API_KEY` 或 `OPENAI_API_KEY`）。

### 2) 任务失败：未找到 `.in`
通常是 LLM 生成器脚本没有按预期产出输入文件，建议减小题目复杂度或增加题面约束描述。

### 3) 为什么下载没有弹窗
浏览器可能拦截自动下载。可在日志中复制 `/download/{task_id}` 手动打开。
