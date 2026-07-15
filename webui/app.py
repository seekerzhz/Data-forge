from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from core.utils import read_text
from webui.schemas import TaskReq
from webui.security import RateLimiter, api_token, public_task_view, require_auth_enabled, verify_api_token
from webui.task_queue import TaskQueue

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def create_app(task_queue: TaskQueue | None = None) -> FastAPI:
    app = FastAPI(title="DataForge Minimal Queue")
    queue = task_queue or TaskQueue()
    limiter = RateLimiter()
    app.state.task_queue = queue
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def guarded(request: Request, _: None = Depends(verify_api_token)) -> None:
        limiter.check(request)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return read_text(STATIC_DIR / "index.html")

    @app.get("/api/meta")
    def api_meta() -> dict[str, Any]:
        return {
            "auth_required": require_auth_enabled(),
            "bind_hint": os.getenv("DATAFORGE_HOST", "127.0.0.1"),
        }

    @app.post("/tasks")
    def create_task(req: TaskReq, request: Request, _: None = Depends(guarded)) -> dict[str, str]:
        try:
            task_id = queue.submit(req.pid, req.statement_markdown, req.num_cases, req.custom_solution)
        except RuntimeError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        return {"task_id": task_id}

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str, request: Request, _: None = Depends(guarded)) -> dict[str, Any]:
        task = queue.get(task_id)
        if task is None:
            raise HTTPException(404, "task not found")
        return public_task_view(task)

    @app.get("/tasks/{task_id}/events")
    async def task_events(
        task_id: str,
        request: Request,
        token: str | None = None,
        authorization: str | None = Header(default=None),
        x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    ) -> StreamingResponse:
        # EventSource cannot set custom headers reliably; allow ?token= as well.
        verify_api_token(authorization=authorization, x_api_token=x_api_token, token=token)
        limiter.check(request)

        async def event_stream():
            last = None
            while True:
                if await request.is_disconnected():
                    break
                task = queue.get(task_id)
                if task is None:
                    payload = json.dumps({"status": "failed", "progress": "task not found", "percent": 100})
                    yield f"event: status\ndata: {payload}\n\n"
                    break
                view = public_task_view(task)
                encoded = json.dumps(view, ensure_ascii=False)
                if encoded != last:
                    yield f"event: status\ndata: {encoded}\n\n"
                    last = encoded
                if view.get("status") in TaskQueue.TERMINAL:
                    break
                await asyncio.sleep(0.8)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/tasks/{task_id}/finish")
    def finish_task(task_id: str, request: Request, _: None = Depends(guarded)) -> dict[str, str]:
        if not queue.finish(task_id):
            raise HTTPException(404, "task not found")
        return {"ok": "true"}

    @app.get("/download/{task_id}")
    def download(
        task_id: str,
        request: Request,
        token: str | None = None,
        authorization: str | None = Header(default=None),
        x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    ) -> FileResponse:
        verify_api_token(authorization=authorization, x_api_token=x_api_token, token=token)
        limiter.check(request)

        task = queue.get(task_id, include_internal=True)
        zip_path_value = task.get("zip_path") if task else None
        if not zip_path_value:
            raise HTTPException(404, "not ready")
        zip_path = Path(zip_path_value).resolve()
        download_root = queue.download_root.resolve()
        if download_root not in zip_path.parents or not zip_path.is_file():
            raise HTTPException(404, "file not found")
        return FileResponse(
            zip_path,
            filename=zip_path.name,
            media_type="application/zip",
            background=BackgroundTask(queue.cleanup_download, task_id),
        )

    if not api_token():
        print("[DataForge][WARN] DATAFORGE_API_TOKEN 未设置；仅建议绑定 127.0.0.1")

    return app
