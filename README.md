# DataForge / Forge 升级版

DataForge 用于把洛谷题目自动转换为可导入 Hydro 的测试数据压缩包。

## 1. 总体架构设计

- `core/luogu.py`：题目抓取（支持题号和 URL），可选 Cookie，优先提取洛谷页面 JSON 中的 Markdown 题面。
- `core/llm.py` + `core/generator.py` + `core/solution.py`：调用 LLM 生成 `generator.py` 和 `solution.cpp`。
- `core/sandbox.py`：本地沙箱执行（`subprocess + resource + timeout`）。
- `core/runner.py`：编译标程并批量生成 `.out`。
- `core/hydro.py`：构造 Hydro 目录并打包 ZIP。
- `core/service.py`：MVP 编排服务（抓取 -> 生成 -> 执行 -> 打包）。
- `webapp.py`：FastAPI Web/API 层（异步任务状态查询，完成后自动下载 ZIP）。

## 2. Workspace 组织

每次任务都会为题目创建独立目录，避免文件混杂：

```text
workspace/tasks/<task_id>/<pid>/
├── source/      # generator.py, solution.cpp
├── testdata/    # *.in, *.out, config.yaml
└── build/       # 生成的 zip 包
```

## 3. 数据流

1. 用户提交 `P1001` 或 URL。
2. 抓取器解析题面与限制信息（优先 Markdown）。
3. LLM 生成数据脚本和参考解。
4. 沙箱内循环执行 `generator.py --id N --output-dir testdata`。
5. 编译 `solution.cpp`，对每个 `.in` 生成 `.out`。
6. 产出 Hydro 结构：
   - `problem.yaml`
   - `problem_zh.md`
   - `testdata/config.yaml` + `*.in/*.out`
7. 输出 ZIP 并在 Web 完成后自动触发下载。

## 4. MVP（命令行）

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 5. Web 服务

```bash
uvicorn webapp:app --reload --port 8000
```

API：
- `POST /generate`：提交 `{ problem, num_cases, include_samples }`，返回 `task_id`
- `GET /status/{task_id}`：查询进度
- `GET /download/{task_id}`：下载 ZIP

## 6. 备选方案

若洛谷页面结构变化导致爬虫失效：
- 用户手动粘贴题面文本；
- 使用 `fallback_from_raw` 解析最低限度字段继续流程。
