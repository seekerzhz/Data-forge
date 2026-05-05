from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from core.service import ForgeService

app = FastAPI(title="DataForge Upgrade")
service = ForgeService()
TASKS: dict[str, dict[str, Any]] = {}


class GenerateReq(BaseModel):
    problem: str
    num_cases: int = 15
    include_samples: bool = True


class StatementReq(BaseModel):
    pid: str
    statement_markdown: str
    num_cases: int = 15
    include_samples: bool = True


class BatchStatementReq(BaseModel):
    tasks: list[StatementReq]


def _run_by_problem(task_id: str, req: GenerateReq) -> None:
    TASKS[task_id] = {"status": "running", "progress": "正在抓取题目并生成数据"}
    try:
        result = service.run_mvp(req.problem, Path("workspace/tasks") / task_id, req.num_cases, req.include_samples)
        TASKS[task_id] = {"status": "success", "progress": f"完成：{result['inputs']} 个 .in，{result['outputs']} 个 .out", "zip": result["zip_path"], "result": result}
    except Exception as e:
        TASKS[task_id] = {"status": "failed", "progress": str(e)}


def _run_by_statement(task_id: str, req: StatementReq) -> None:
    TASKS[task_id] = {"status": "running", "progress": "正在使用题面生成数据"}
    try:
        meta = service.parse_statement(req.pid, req.statement_markdown)
        result = service.run_with_meta(meta, Path("workspace/tasks") / task_id, req.num_cases, req.include_samples)
        TASKS[task_id] = {"status": "success", "progress": f"完成：{result['inputs']} 个 .in，{result['outputs']} 个 .out", "zip": result["zip_path"], "result": result}
    except Exception as e:
        TASKS[task_id] = {"status": "failed", "progress": str(e)}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><html><body><h3>DataForge - 手动题面模式</h3>
<p>题号</p><input id='pid' value='P1001'/><p>题面 Markdown</p><textarea id='md' rows='14' cols='100'></textarea><br/>
<button onclick='go()'>提交任务</button><pre id='s'></pre>
<script>
async function go(){
 const pid=document.getElementById('pid').value.trim(); const md=document.getElementById('md').value;
 const r=await fetch('/generate_statement',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({pid:pid,statement_markdown:md})});
 const j=await r.json(); const id=j.task_id; const el=document.getElementById('s');
 const t=setInterval(async()=>{const s=await (await fetch('/status/'+id)).json(); el.textContent=JSON.stringify(s,null,2); if(s.status==='success'){clearInterval(t); window.location='/download/'+id;} if(s.status==='failed'){clearInterval(t);}},1200);
}
</script></body></html>"""


@app.post("/generate")
def generate(req: GenerateReq, background_tasks: BackgroundTasks) -> dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "pending", "progress": "排队中"}
    background_tasks.add_task(_run_by_problem, task_id, req)
    return {"task_id": task_id}


@app.post("/generate_statement")
def generate_statement(req: StatementReq, background_tasks: BackgroundTasks) -> dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "pending", "progress": "排队中"}
    background_tasks.add_task(_run_by_statement, task_id, req)
    return {"task_id": task_id}


@app.post("/generate_batch")
def generate_batch(req: BatchStatementReq, background_tasks: BackgroundTasks) -> dict[str, list[str]]:
    task_ids: list[str] = []
    for item in req.tasks:
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {"status": "pending", "progress": "排队中"}
        background_tasks.add_task(_run_by_statement, task_id, item)
        task_ids.append(task_id)
    return {"task_ids": task_ids}


@app.get("/status/{task_id}")
def status(task_id: str) -> dict[str, Any]:
    if task_id not in TASKS:
        raise HTTPException(404, "task not found")
    return TASKS[task_id]


@app.get("/download/{task_id}")
def download(task_id: str) -> FileResponse:
    task = TASKS.get(task_id)
    if not task or task.get("status") != "success":
        raise HTTPException(404, "file not ready")
    return FileResponse(task["zip"], filename=Path(task["zip"]).name, media_type="application/zip")
