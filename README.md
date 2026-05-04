# DataForge / Forge 升级版

DataForge 用于把洛谷题目自动转换为可导入 Hydro 的测试数据压缩包。

## 1. 总体架构设计

- `core/luogu.py`：题目抓取（支持题号和 URL），可选 Cookie，含降级策略（手工粘贴题面文本）。
- `core/llm.py` + `core/generator.py` + `core/solution.py`：调用 LLM 生成 `generator.py` 和 `solution.cpp`。
- `core/sandbox.py`：本地沙箱执行（`subprocess + resource + timeout`）。
- `core/runner.py`：编译标程并批量生成 `.out`。
- `core/hydro.py`：构造 Hydro 目录并打包 ZIP。
- `core/service.py`：MVP 编排服务（抓取 -> 生成 -> 执行 -> 打包）。
- `webapp.py`：FastAPI Web/API 层（异步任务状态查询与下载）。

## 2. 数据流

1. 用户提交 `P1001` 或 URL。
2. 抓取器解析题面与限制信息。
3. LLM 生成数据脚本和参考解。
4. 沙箱内循环执行 `generator.py --id N --output-dir testdata`。
5. 编译 `solution.cpp`，对每个 `.in` 生成 `.out`。
6. 产出 Hydro 结构：
   - `problem.yaml`
   - `problem_zh.md`
   - `testdata/config.yaml` + `*.in/*.out`
7. 输出 ZIP，供下载或 API 返回。

## 3. MVP（命令行）

> 优先路径：先完成爬虫 + LLM + 本地沙箱 + ZIP。

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

创建 `.env` 并配置 API Key 后运行：

```bash
python3 forge.py workspace/example/problem.txt --provider ark
```

## 4. Web 服务

启动：

```bash
uvicorn webapp:app --reload --port 8000
```

API：
- `POST /generate`：提交 `{ problem, num_cases, include_samples }`，返回 `task_id`
- `GET /status/{task_id}`：查询进度
- `GET /download/{task_id}`：下载 ZIP

## 5. Docker 部署建议（下一步）

推荐 `docker-compose` 拆分：
- `web`（FastAPI）
- `worker`（Celery）
- `redis`（队列）
- `sandbox-runner`（一次性容器执行 generator）

容器执行加上：`--cpus --memory --network=none --pids-limit --read-only`。

## 6. 备选方案

若洛谷页面结构变化导致爬虫失效：
- 继续接收题号用于命名；
- 用户手动粘贴题面文本；
- 使用 `fallback_from_raw` 解析最低限度字段并继续生成流程。
