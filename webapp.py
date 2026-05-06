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
WORKERS = 3


class TaskReq(BaseModel):
    pid: str = ""
    statement_markdown: str
    num_cases: int = 15


def worker() -> None:
    while True:
        task_id, pid, statement, num_cases = JOB_QUEUE.get()
        TASKS[task_id] = {"status": "processing", "progress": "处理中"}
        try:
            result = service.run_with_statement(pid, statement, Path("workspace/tasks") / task_id, num_cases)
            TASKS[task_id] = {"status": "done", "progress": "已完成，准备下载", **result}
        except Exception as e:
            TASKS[task_id] = {"status": "failed", "progress": str(e)}
        finally:
            JOB_QUEUE.task_done()


for _ in range(WORKERS):
    threading.Thread(target=worker, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><html><body><h3>题面持续提交（并发后台处理）</h3>
<button onclick='addItem()'>添加题面</button>
<div id='list'></div>
<script>
let idx=0;
function addItem(){
  idx++; const id='item'+idx;
  const d=document.createElement('div');
  d.id=id;
  d.innerHTML=`<hr><input class='pid' placeholder='题号可空'>
  <button class='submit'>提交本题面</button>
  <span class='status'>waiting-edit</span><br>
  <textarea class='md' rows='10' cols='90' placeholder='粘贴题面'></textarea>`;
  document.getElementById('list').appendChild(d);
  d.querySelector('.submit').onclick=()=>submitOne(d);
}
addItem();

async function submitOne(d){
  const pid=d.querySelector('.pid').value;
  const md=d.querySelector('.md').value;
  if(!md.trim()){alert('题面不能为空');return;}
  d.querySelector('.status').textContent='waiting';
  const r=await fetch('/tasks',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({pid:pid,statement_markdown:md})});
  const j=await r.json();
  d.dataset.taskId=j.task_id;
  poll(d, j.task_id);
  // 立刻给用户新输入框继续粘贴，不阻塞
  addItem();
}

function autoDownload(taskId){
  const iframe=document.createElement('iframe');
  iframe.style.display='none';
  iframe.src='/download/'+taskId;
  document.body.appendChild(iframe);
}

function poll(d, taskId){
  const timer=setInterval(async()=>{
    const s=await (await fetch('/tasks/'+taskId)).json();
    d.querySelector('.status').textContent=s.status+' '+(s.progress||'');
    if(s.status==='done'){
      clearInterval(timer);
      autoDownload(taskId);
      d.querySelector('.status').textContent='finished';
      // 下载触发后任务结束
      await fetch('/tasks/'+taskId+'/finish',{method:'POST'});
    }
    if(s.status==='failed') clearInterval(timer);
  },1200);
}
</script></body></html>"""


@app.post('/tasks')
def create_task(req: TaskReq) -> dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "waiting", "progress": "等待"}
    JOB_QUEUE.put((task_id, req.pid, req.statement_markdown, req.num_cases))
    return {"task_id": task_id}


@app.get('/tasks/{task_id}')
def get_task(task_id: str) -> dict[str, Any]:
    if task_id not in TASKS:
        raise HTTPException(404, 'task not found')
    return TASKS[task_id]


@app.post('/tasks/{task_id}/finish')
def finish_task(task_id: str) -> dict[str, str]:
    t = TASKS.get(task_id)
    if not t:
        raise HTTPException(404, 'task not found')
    t['status'] = 'finished'
    t['progress'] = '任务已结束'
    return {"ok": "true"}


@app.get('/download/{task_id}')
def download(task_id: str) -> FileResponse:
    t = TASKS.get(task_id)
    if not t or t.get('zip_path') is None:
        raise HTTPException(404, 'not ready')
    return FileResponse(t['zip_path'], filename=Path(t['zip_path']).name, media_type='application/zip')
