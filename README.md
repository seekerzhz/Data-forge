# DataForge（Luogu -> Hydro）

这是一个“输入洛谷题号，自动生成 Hydro 可导入 ZIP”的工具。

## 你能得到什么

- 输入 `P1001` 或洛谷题目链接。
- 自动抓题面（优先拿 Markdown）。
- 自动用 LLM 生成 `generator.py` + `solution.cpp`。
- 在本地受限沙箱中执行数据生成。
- 自动生成 `.in/.out`，并打包成 Hydro 格式 ZIP。
- Web 页面可查看任务状态与输出预览，结束后自动下载 ZIP。

---

## 1. 快速开始（最短路径）

### 1) 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 配置 LLM Key（`.env`）

```env
ARK_API_KEY=your-key
ARK_MODEL=doubao-seed-1-6-250615
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 可选 OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
```

### 3) 启动 Web

```bash
uvicorn webapp:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开 `http://127.0.0.1:8000`，输入题号后点击“生成并下载 ZIP”。

---

## 2. 目录结构（重点）

每个任务都会创建独立目录，按题号归档：

```text
workspace/tasks/<task_id>/<pid>/
├── source/
│   ├── generator.py
│   └── solution.cpp
├── testdata/
│   ├── 1.in
│   ├── 1.out
│   ├── 2.in
│   ├── 2.out
│   └── ...
└── build/
    └── <pid>_<hash>.zip
```

> `testdata` 下会强制整理并包含所有 `.in/.out`（若生成器在子目录产出，也会收集后整理）。

---

## 3. Web/API 使用

- `POST /generate`
  - body: `{ "problem": "P1001", "num_cases": 15, "include_samples": true }`
  - return: `{ "task_id": "..." }`
- `GET /status/{task_id}`
  - 返回 `pending/running/success/failed`
  - 成功时会返回：
    - 生成了多少 `.in`
    - 生成了多少 `.out`
    - 跳过了多少超时点
    - 前几个 `.out` 的预览文本
- `GET /download/{task_id}`
  - 下载 ZIP

---

## 4. 常见问题

### Q1：为什么没有 `.out`？

现在流程会：
1. 收集 `testdata` 内所有 `.in`；
2. 标准化成 `1.in, 2.in...`；
3. 编译 `solution.cpp` 并逐个生成 `.out`；
4. 状态接口直接返回统计数。

如果仍为 0，通常是生成器脚本没有产出任何 `.in`，会直接报错提示。

### Q2：洛谷爬虫失效怎么办？

可走降级路径：手动粘贴题面文本（后端 `fallback_from_raw`），仍可继续生成与打包。

---

## 5. 当前实现边界

- 沙箱是本地 `subprocess + resource + timeout`，适合 MVP。
- 生产建议改为 Docker 一次性容器隔离（CPU/内存/网络/只读根目录限制）。
