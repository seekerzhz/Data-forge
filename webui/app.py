from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from core.utils import read_text
from webui.schemas import TaskReq
from webui.task_queue import TaskQueue

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def create_app(task_queue: TaskQueue | None = None) -> FastAPI:
    app = FastAPI(title="DataForge Minimal Queue")
    queue = task_queue or TaskQueue()
    app.state.task_queue = queue
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return read_text(STATIC_DIR / "index.html")

    @app.post("/tasks")
    def create_task(req: TaskReq) -> dict[str, str]:
        task_id = queue.submit(req.pid, req.statement_markdown, req.num_cases)
        return {"task_id": task_id}

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, Any]:
        task = queue.get(task_id)
        if task is None:
            raise HTTPException(404, "task not found")
        return task

    @app.post("/tasks/{task_id}/finish")
    def finish_task(task_id: str) -> dict[str, str]:
        if not queue.finish(task_id):
            raise HTTPException(404, "task not found")
        return {"ok": "true"}

    @app.get("/download/{task_id}")
    def download(task_id: str) -> FileResponse:
        task = queue.get(task_id)
        zip_path_value = task.get("zip_path") if task else None
        if not zip_path_value:
            raise HTTPException(404, "not ready")
        zip_path = Path(zip_path_value).resolve()
        if not zip_path.is_file():
            raise HTTPException(404, "file not found")
        return FileResponse(
            zip_path,
            filename=zip_path.name,
            media_type="application/zip",
            background=BackgroundTask(queue.cleanup_download, task_id),
        )

    return app
