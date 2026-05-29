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
    num_cases: int = 20


def worker() -> None:
    while True:
        task_id, pid, statement, num_cases = JOB_QUEUE.get()
        TASKS[task_id] = {"status": "processing", "progress": "处理中"}
        try:
            result = service.run_with_statement(pid, statement, Path("workspace/tasks") / task_id, num_cases)
            result.pop("status", None)
            TASKS[task_id] = {"status": "done", "progress": "已完成，准备下载", **result}
        except Exception as e:
            TASKS[task_id] = {"status": "failed", "progress": str(e)}
        finally:
            JOB_QUEUE.task_done()


for _ in range(WORKERS):
    threading.Thread(target=worker, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DataForge Queue</title>
  <style>
    :root {
      --background: #FFFFFF;
      --section: #F8F8FC;
      --line: #E9E9EF;
      --text: #111111;
      --secondary: #8E8E93;
      --blue: #007AFF;
      --blue-hover: #006FE6;
      --danger: #FF3B30;
      --font-display: "HYWenHei 85W", "Hanyi WenHei 85W", "汉仪文黑-85W", "HYWenHei-85W", "PingFang SC", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI", Roboto, sans-serif;
      --font-text: "HYWenHei 85W", "Hanyi WenHei 85W", "汉仪文黑-85W", "HYWenHei-85W", "PingFang SC", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI", Roboto, sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    html {
      background: var(--background);
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--background);
      color: var(--text);
      font-family: var(--font-text);
      font-size: 16px;
      font-weight: 400;
      letter-spacing: -0.01em;
      line-height: 1.4;
    }

    button,
    input,
    textarea {
      font: inherit;
      letter-spacing: inherit;
    }

    .app {
      width: 100%;
      max-width: 600px;
      margin: 0 auto;
      padding: 32px 16px 48px;
    }

    .header {
      padding: 0 0 24px;
      border-bottom: 1px solid var(--line);
    }

    h1 {
      margin: 0;
      font-family: var(--font-display);
      font-size: 30px;
      font-weight: 620;
      letter-spacing: -0.02em;
      line-height: 1.12;
    }

    .subtitle {
      margin: 8px 0 0;
      color: var(--secondary);
      font-size: 15px;
    }

    .toolbar {
      display: flex;
      gap: 10px;
      margin-top: 20px;
    }

    .list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding-top: 16px;
    }

    .card {
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #FFFFFF;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--section);
    }

    .card-title {
      margin: 0;
      font-family: var(--font-display);
      font-size: 17px;
      font-weight: 600;
      letter-spacing: -0.02em;
    }

    .status {
      color: var(--secondary);
      font-size: 13px;
      white-space: nowrap;
      transition: color 180ms ease, opacity 180ms ease;
    }

    .status.is-waiting,
    .status.is-processing {
      color: var(--blue);
    }

    .status.is-done,
    .status.is-finished {
      color: #34C759;
    }

    .status.is-failed {
      color: var(--danger);
    }

    .card-body {
      display: grid;
      gap: 12px;
      padding: 16px;
    }

    .field-row {
      display: grid;
      grid-template-columns: 1fr 112px;
      gap: 10px;
    }

    .field {
      display: grid;
      gap: 6px;
    }

    label {
      color: var(--secondary);
      font-size: 13px;
    }

    input,
    textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #FFFFFF;
      color: var(--text);
      outline: none;
      transition: border-color 180ms ease, background-color 180ms ease, color 180ms ease, opacity 180ms ease;
    }

    input {
      height: 42px;
      padding: 0 12px;
    }

    textarea {
      min-height: 220px;
      resize: vertical;
      padding: 11px 12px;
      line-height: 1.4;
    }

    input::placeholder,
    textarea::placeholder {
      color: rgba(142, 142, 147, 0.72);
    }

    input:focus,
    textarea:focus {
      border-color: var(--blue);
    }

    .actions {
      display: flex;
      gap: 10px;
      padding-top: 2px;
    }

    .button {
      min-height: 42px;
      border: 0;
      border-radius: 10px;
      padding: 0 16px;
      background: var(--blue);
      color: #FFFFFF;
      cursor: pointer;
      font-weight: 500;
      transition: background-color 180ms ease, color 180ms ease, opacity 180ms ease;
    }

    .button:hover {
      background: var(--blue-hover);
    }

    .button:disabled {
      cursor: default;
      opacity: 0.5;
    }

    .button.secondary {
      border: 1px solid var(--line);
      background: #FFFFFF;
      color: var(--blue);
    }

    .button.secondary:hover {
      background: var(--section);
    }

    @media (max-width: 520px) {
      .app {
        padding-top: 24px;
      }

      .toolbar,
      .actions,
      .field-row {
        grid-template-columns: 1fr;
        flex-direction: column;
      }

      .button {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <main class="app">
    <header class="header">
      <h1>题面持续提交</h1>
      <p class="subtitle">并发后台处理，提交后会自动添加新的输入卡片。</p>
      <div class="toolbar">
        <button class="button" type="button" onclick="addItem()">添加题面</button>
      </div>
    </header>
    <section id="list" class="list" aria-label="题面提交列表"></section>
  </main>

  <script>
let idx=0;

function setStatus(d, text, state='idle'){
  const status=d.querySelector('.status');
  status.textContent=text;
  status.className='status is-'+state;
}

function addItem(){
  idx++; const id='item'+idx;
  const d=document.createElement('article');
  d.id=id;
  d.className='card';
  d.innerHTML=`<div class="card-header">
    <h2 class="card-title">题面 #${idx}</h2>
    <span class="status is-idle">waiting-edit</span>
  </div>
  <div class="card-body">
    <div class="field-row">
      <div class="field">
        <label for="${id}-pid">题号</label>
        <input id="${id}-pid" class="pid" placeholder="可空">
      </div>
      <div class="field">
        <label for="${id}-cases">数据组数</label>
        <input id="${id}-cases" class="num_cases" type="number" min="1" value="20" title="数据组数">
      </div>
    </div>
    <div class="field">
      <label for="${id}-md">题面 Markdown</label>
      <textarea id="${id}-md" class="md" rows="10" placeholder="粘贴题面"></textarea>
    </div>
    <div class="actions">
      <button class="button submit" type="button">提交本题面</button>
      <button class="button secondary clear" type="button">清除</button>
    </div>
  </div>`;
  document.getElementById('list').appendChild(d);
  d.querySelector('.submit').onclick=()=>submitOne(d);
  d.querySelector('.clear').onclick=()=>clearItem(d);
}
addItem();

function clearItem(d){
  d.querySelector('.pid').value='';
  d.querySelector('.num_cases').value='20';
  d.querySelector('.md').value='';
  setStatus(d, 'waiting-edit', 'idle');
}

async function submitOne(d){
  const pid=d.querySelector('.pid').value;
  const numCases=Number(d.querySelector('.num_cases').value || 20);
  const md=d.querySelector('.md').value;
  if(!md.trim()){alert('题面不能为空');return;}
  if(!Number.isInteger(numCases) || numCases<=0){alert('数据组数必须是正整数');return;}
  setStatus(d, 'waiting', 'waiting');
  d.querySelector('.submit').disabled=true;
  const r=await fetch('/tasks',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({pid:pid,statement_markdown:md,num_cases:numCases})});
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
    setStatus(d, s.status+' '+(s.progress||''), s.status);
    if(s.status==='done'){
      clearInterval(timer);
      autoDownload(taskId);
      setStatus(d, 'finished', 'finished');
      // 下载触发后任务结束
      await fetch('/tasks/'+taskId+'/finish',{method:'POST'});
    }
    if(s.status==='failed'){
      clearInterval(timer);
      d.querySelector('.submit').disabled=false;
    }
  },1200);
}
  </script>
</body>
</html>"""

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
