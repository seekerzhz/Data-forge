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


def _job(task_id: str, req: GenerateReq) -> None:
    TASKS[task_id] = {"status": "running", "progress": "正在抓取题目并生成数据"}
    try:
        result = service.run_mvp(req.problem, Path("workspace/tasks") / task_id, req.num_cases, req.include_samples)
        TASKS[task_id] = {
            "status": "success",
            "progress": f"完成：{result['inputs']} 个 .in，{result['outputs']} 个 .out，跳过 {result['skipped']} 个",
            "zip": result["zip_path"],
            "result": result,
        }
    except Exception as e:
        TASKS[task_id] = {"status": "failed", "progress": str(e)}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return '''<!doctype html><html><body><h3>DataForge</h3><input id="p" placeholder="P1001"/><button onclick="go()">生成并下载 ZIP</button><pre id="s">等待开始...</pre><script>
async function go(){const p=document.getElementById('p').value.trim();if(!p){return;}const r=await fetch('/generate',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({problem:p})});const j=await r.json();const id=j.task_id;const el=document.getElementById('s');const t=setInterval(async()=>{const s=await (await fetch('/status/'+id)).json();el.textContent=JSON.stringify(s,null,2);if(s.status==='success'){clearInterval(t);setTimeout(()=>window.location='/download/'+id,500);}if(s.status==='failed'){clearInterval(t);}},1200)}
</script></body></html>'''


@app.post("/generate")
def generate(req: GenerateReq, background_tasks: BackgroundTasks) -> dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "pending", "progress": "排队中"}
    background_tasks.add_task(_job, task_id, req)
    return {"task_id": task_id}


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
