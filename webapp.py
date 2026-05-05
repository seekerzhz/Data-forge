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
    pid: str = ""
    statement_markdown: str
    num_cases: int = 15
    include_samples: bool = True


class BatchStatementReq(BaseModel):
    tasks: list[StatementReq]


def _finish(task_id: str, result: dict) -> None:
    TASKS[task_id] = {"status": "success", "progress": f"完成：{result['inputs']} 个 .in，{result['outputs']} 个 .out", "zip": result["zip_path"], "result": result}


def _run_by_problem(task_id: str, req: GenerateReq) -> None:
    TASKS[task_id] = {"status": "running", "progress": "正在抓取题目并生成数据"}
    try:
        _finish(task_id, service.run_mvp(req.problem, Path("workspace/tasks") / task_id, req.num_cases, req.include_samples))
    except Exception as e:
        TASKS[task_id] = {"status": "failed", "progress": str(e)}


def _run_by_statement(task_id: str, req: StatementReq) -> None:
    TASKS[task_id] = {"status": "running", "progress": "正在使用题面生成数据"}
    try:
        meta = service.parse_statement(req.pid, req.statement_markdown)
        _finish(task_id, service.run_with_meta(meta, Path("workspace/tasks") / task_id, req.num_cases, req.include_samples))
    except Exception as e:
        TASKS[task_id] = {"status": "failed", "progress": str(e)}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><html><body><h3>DataForge - 批量粘贴题面</h3>
<button onclick='addRow()'>新增题面</button> <button onclick='submitBatch()'>批量提交</button>
<div id='rows'></div><pre id='s'></pre>
<script>
function addRow(){const box=document.createElement('div'); box.innerHTML=`<hr><input placeholder='题号(可空)' class='pid'/><br><textarea class='md' rows='10' cols='100' placeholder='粘贴完整markdown题面'></textarea>`; document.getElementById('rows').appendChild(box);}
addRow();
async function submitBatch(){
 const items=[...document.querySelectorAll('#rows > div')].map(d=>({pid:d.querySelector('.pid').value,statement_markdown:d.querySelector('.md').value})).filter(x=>x.statement_markdown.trim());
 const r=await fetch('/generate_batch',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({tasks:items})});
 const j=await r.json(); const ids=j.task_ids; const el=document.getElementById('s'); el.textContent='已提交: '+ids.join(', ');
 for(const id of ids){const t=setInterval(async()=>{const s=await (await fetch('/status/'+id)).json(); el.textContent += '\n'+id+': '+s.status+' '+s.progress; if(s.status==='success'){clearInterval(t); el.textContent += '\n下载: /download/'+id;} if(s.status==='failed'){clearInterval(t);}},1500);}
}
</script></body></html>"""


@app.post('/generate')
def generate(req: GenerateReq, background_tasks: BackgroundTasks) -> dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "pending", "progress": "排队中"}
    background_tasks.add_task(_run_by_problem, task_id, req)
    return {"task_id": task_id}


@app.post('/generate_statement')
def generate_statement(req: StatementReq, background_tasks: BackgroundTasks) -> dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "pending", "progress": "排队中"}
    background_tasks.add_task(_run_by_statement, task_id, req)
    return {"task_id": task_id}


@app.post('/generate_batch')
def generate_batch(req: BatchStatementReq, background_tasks: BackgroundTasks) -> dict[str, list[str]]:
    ids = []
    for item in req.tasks:
        tid = str(uuid.uuid4())
        TASKS[tid] = {"status": "pending", "progress": "排队中"}
        background_tasks.add_task(_run_by_statement, tid, item)
        ids.append(tid)
    return {"task_ids": ids}


@app.get('/status/{task_id}')
def status(task_id: str) -> dict[str, Any]:
    if task_id not in TASKS:
        raise HTTPException(404, 'task not found')
    return TASKS[task_id]


@app.get('/download/{task_id}')
def download(task_id: str) -> FileResponse:
    t = TASKS.get(task_id)
    if not t or t.get('status') != 'success':
        raise HTTPException(404, 'file not ready')
    return FileResponse(t['zip'], filename=Path(t['zip']).name, media_type='application/zip')
