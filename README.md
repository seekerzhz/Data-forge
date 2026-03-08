# DataForge / Forge

## 中文介绍

DataForge 是一个面向算法竞赛出题/验题场景的自动化工具：你只需要提供题面，它就能自动生成数据脚本 `generate.py`、生成或使用你自己的 `solution.cpp`，并批量产出 `*.in/*.out`。

### 核心功能
- 从 `.env` 读取 API 与模型配置（默认使用 Ark）。
- 支持两种 LLM Provider：`ark` / `openai`。
- 默认生成 50 组数据，可通过参数自定义数量。
- 数据按强度分层：小数据 / 特殊数据 / 随机数据 / 极限数据。
- 支持跳过解法生成，直接使用你自己写的 `solution.cpp`。
- 对每个测试点设置运行超时（默认 5 秒），超时后自动跳过并提示。

### 快速开始
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

创建 `.env`（示例）：
```env
ARK_API_KEY=your-ark-api-key
ARK_MODEL=doubao-seed-1-6-250615
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# optional
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
```

运行（默认 50 组）：
```bash
python3 forge.py workspace/example/problem.txt --provider ark
```

自定义数据数量（例如 80 组）：
```bash
python3 forge.py workspace/example/problem.txt --provider ark --num-cases 80
```

使用你自己的解法：
```bash
python3 forge.py workspace/example/problem.txt \
  --provider ark \
  --no-generate-solution \
  --solution-path /path/to/solution.cpp
```

只生成代码不执行：
```bash
python3 forge.py workspace/example/problem.txt --skip-run
```

---

## English Overview

DataForge is an automation tool for competitive programming test preparation.
Given only a problem statement, it can generate `generate.py`, generate (or reuse) `solution.cpp`, and produce batches of `*.in/*.out` files.

### Features
- Reads API keys and models from `.env` (Ark is default).
- Supports `ark` and `openai` providers.
- Generates 50 test cases by default, customizable via CLI.
- Uses layered data intensity: small / special / random / near-limit stress cases.
- Can skip solution generation and use your own `solution.cpp`.
- Per-test timeout (default: 5s), long-running cases are skipped with warning.

### Usage
```bash
python3 forge.py workspace/example/problem.txt --provider ark --num-cases 50
```

Use your own solution:
```bash
python3 forge.py workspace/example/problem.txt \
  --provider ark \
  --no-generate-solution \
  --solution-path /path/to/solution.cpp
```
