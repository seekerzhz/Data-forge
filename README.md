# DataForge（手动题面优先）

为避免爬虫不稳定，推荐直接由用户提供完整题面 Markdown（洛谷复制出来的标准格式）。系统直接把它作为 `problem_zh.md` 基础内容。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn webapp:app --host 0.0.0.0 --port 8000 --reload
```

打开 `http://127.0.0.1:8000`：
- 填写题号（如 `P1007`）
- 粘贴完整题面 Markdown
- 提交任务并等待自动下载 ZIP

## API

### 1) 单题（手动题面，推荐）
`POST /generate_statement`

```json
{
  "pid": "P1007",
  "statement_markdown": "# P1007 ...",
  "num_cases": 20,
  "include_samples": true
}
```

### 2) 多题批量入队
`POST /generate_batch`

```json
{
  "tasks": [
    {"pid": "P1007", "statement_markdown": "# P1007 ..."},
    {"pid": "P1001", "statement_markdown": "# P1001 ..."}
  ]
}
```

返回 `task_ids`，逐个查询 `GET /status/{task_id}`，成功后 `GET /download/{task_id}`。

## 说明

- 系统支持后台队列式处理（任务状态：`pending/running/success/failed`）。
- 仍保留 `POST /generate`（按题号抓取）供兼容，但不推荐作为主流程。
