# DataForge（精简版）

仅保留三件事：
1. 用户提供题面 markdown。
2. 后端先调用 LLM 优化题面结构。
3. 后台队列生成数据并打包 ZIP。

## 启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn webapp:app --host 0.0.0.0 --port 8000 --reload
```

打开 `http://127.0.0.1:8000`，可连续添加多个题面并一次提交。

## 状态

- `waiting`：等待
- `processing`：处理中
- `done`：已完成
- `failed`：失败

## 接口

- `POST /tasks`：提交单题面
- `POST /tasks/batch`：批量提交题面
- `GET /tasks/{task_id}`：查询状态
- `GET /download/{task_id}`：下载 ZIP
