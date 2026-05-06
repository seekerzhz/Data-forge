from __future__ import annotations

import queue
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from core.service import ForgeService

app = FastAPI(title="DataForge Minimal Queue")
service = ForgeService()
TASKS: dict[str, dict[str, Any]] = {}
JOB_QUEUE: "queue.Queue[tuple[str, str, str, int]]" = queue.Queue()


class TaskReq(BaseModel):
    pid: str = ""
    statement_markdown: str
    num_cases: int = 15


class BatchReq(BaseModel):
    tasks: list[TaskReq]


def worker() -> None:
    while True:
        task_id, pid, statement, num_cases = JOB_QUEUE.get()
        TASKS[task_id] = {"status": "processing", "progress": "处理中"}
        try:
            result = service.run_with_statement(pid, statement, Path("workspace/tasks") / task_id, num_cases)
            TASKS[task_id] = {"status": "done", "progress": "已完成", **result}
        except Exception as e:
            TASKS[task_id] = {"status": "failed", "progress": str(e)}
        finally:
            JOB_QUEUE.task_done()


threading.Thread(target=worker, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><html><body><h3>题面批量提交</h3>
<button onclick='addItem()'>添加题面</button><button onclick='submitAll()'>提交全部</button>
<div id='list'></div><pre id='log'></pre>
<script>
function addItem(){const d=document.createElement('div');d.innerHTML=`<hr><input class='pid' placeholder='题号可空'><br><textarea class='md' rows='10' cols='90' placeholder='粘贴题面'></textarea>`;document.getElementById('list').appendChild(d)}
addItem();
async function submitAll(){
 const tasks=[...document.querySelectorAll('#list > div')].map(d=>({pid:d.querySelector('.pid').value,statement_markdown:d.querySelector('.md').value})).filter(x=>x.statement_markdown.trim());
 const res=await fetch('/tasks/batch',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({tasks})});
 const data=await res.json(); const log=document.getElementById('log'); log.textContent='已提交: '+data.task_ids.join(', ');
 for(const id of data.task_ids){const t=setInterval(async()=>{const s=await (await fetch('/tasks/'+id)).json();log.textContent += '\\n'+id+' => '+s.status; if(s.status==='done'){clearInterval(t);log.textContent += ' 下载:/download/'+id;} if(s.status==='failed'){clearInterval(t);}},1500)}
}
</script></body></html>"""


@app.post('/tasks')
def create_task(req: TaskReq) -> dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "waiting", "progress": "等待"}
    JOB_QUEUE.put((task_id, req.pid, req.statement_markdown, req.num_cases))
    return {"task_id": task_id}


@app.post('/tasks/batch')
def create_batch(req: BatchReq) -> dict[str, list[str]]:
    ids = []
    for task in req.tasks:
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {"status": "waiting", "progress": "等待"}
        JOB_QUEUE.put((task_id, task.pid, task.statement_markdown, task.num_cases))
        ids.append(task_id)
    return {"task_ids": ids}


@app.get('/tasks/{task_id}')
def get_task(task_id: str) -> dict[str, Any]:
    if task_id not in TASKS:
        raise HTTPException(404, 'task not found')
    return TASKS[task_id]


@app.get('/download/{task_id}')
def download(task_id: str) -> FileResponse:
    t = TASKS.get(task_id)
    if not t or t.get('status') != 'done':
        raise HTTPException(404, 'not ready')
    return FileResponse(t['zip_path'], filename=Path(t['zip_path']).name, media_type='application/zip')
