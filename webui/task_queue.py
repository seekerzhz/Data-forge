from __future__ import annotations

import os
import queue
import shutil
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.service import ForgeService


@dataclass(frozen=True)
class TaskJob:
    task_id: str
    pid: str
    statement: str
    num_cases: int
    custom_solution: str | None = None


@dataclass
class TaskRecord:
    status: str
    progress: str
    percent: int = 0
    details: dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)
    zip_path: str | None = None

    def as_dict(self, *, include_internal: bool = False) -> dict[str, Any]:
        payload = {
            "status": self.status,
            "progress": self.progress,
            "percent": self.percent,
            **self.details,
        }
        if include_internal and self.zip_path:
            payload["zip_path"] = self.zip_path
        return payload


class TaskQueue:
    """Threaded background queue that tracks generation task state."""

    TERMINAL = frozenset({"done", "failed", "finished"})

    def __init__(
        self,
        workspace_root: Path = Path("workspace/tasks"),
        download_root: Path = Path("workspace/downloads"),
        workers: int = 3,
        service_factory: Callable[[], ForgeService] = ForgeService,
        max_queue_size: int | None = None,
        task_ttl_seconds: float | None = None,
    ):
        self.workspace_root = workspace_root
        self.download_root = download_root
        self.service_factory = service_factory
        self.max_queue_size = max(1, int(max_queue_size or os.getenv("DATAFORGE_MAX_QUEUE_SIZE", "50")))
        self.task_ttl_seconds = float(task_ttl_seconds or os.getenv("DATAFORGE_TASK_TTL_SECONDS", "3600"))
        self.jobs: "queue.Queue[TaskJob]" = queue.Queue(maxsize=self.max_queue_size)
        self.tasks: dict[str, TaskRecord] = {}
        self.lock = threading.Lock()
        self._stop = threading.Event()
        for _ in range(workers):
            threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self._reaper, daemon=True).start()

    def submit(self, pid: str, statement: str, num_cases: int, custom_solution: str | None = None) -> str:
        """Enqueue a new generation task and return its public task id."""
        if self.jobs.full():
            raise RuntimeError("任务队列已满，请稍后重试")

        task_id = str(uuid.uuid4())
        self._set(task_id, status="waiting", progress="等待处理", percent=4)
        try:
            self.jobs.put(
                TaskJob(
                    task_id=task_id,
                    pid=pid,
                    statement=statement,
                    num_cases=num_cases,
                    custom_solution=custom_solution,
                ),
                block=False,
            )
        except queue.Full:
            with self.lock:
                self.tasks.pop(task_id, None)
            raise RuntimeError("任务队列已满，请稍后重试")
        return task_id

    def get(self, task_id: str, *, include_internal: bool = False) -> dict[str, Any] | None:
        """Return a snapshot of one task state, or None when absent."""
        with self.lock:
            record = self.tasks.get(task_id)
            return record.as_dict(include_internal=include_internal) if record else None

    def finish(self, task_id: str) -> bool:
        """Mark a completed task as downloaded/finished."""
        with self.lock:
            record = self.tasks.get(task_id)
            if not record:
                return False
            record.status = "finished"
            record.progress = "任务已结束"
            record.percent = 100
            record.updated_at = time.time()
            return True

    def cleanup_download(self, task_id: str) -> None:
        """Remove the temporary downloaded ZIP directory for a completed task."""
        self._remove_tree(self.download_root / task_id, self.download_root)

    def _set(self, task_id: str, status: str, progress: str, percent: int, **details: Any) -> None:
        percent = max(0, min(100, int(percent)))
        zip_path = details.pop("zip_path", None)
        with self.lock:
            record = TaskRecord(status=status, progress=progress, percent=percent, details=details)
            if zip_path:
                record.zip_path = str(zip_path)
            self.tasks[task_id] = record

    def _update(
        self,
        task_id: str,
        status: str | None = None,
        progress: str | None = None,
        percent: int | None = None,
        **details: Any,
    ) -> None:
        with self.lock:
            record = self.tasks.setdefault(task_id, TaskRecord(status="waiting", progress="等待处理", percent=0))
            if status is not None:
                record.status = status
            if progress is not None:
                record.progress = progress
            if percent is not None:
                record.percent = max(0, min(100, int(percent)))
            if "zip_path" in details:
                record.zip_path = str(details.pop("zip_path"))
            record.details.update(details)
            record.updated_at = time.time()

    def _task_workspace(self, task_id: str) -> Path:
        return self.workspace_root / task_id

    def _remove_tree(self, path: Path, root: Path) -> None:
        target = path.resolve()
        allowed_root = root.resolve()
        if target == allowed_root or allowed_root not in target.parents:
            return
        shutil.rmtree(target, ignore_errors=True)

    def _clear_task_workspace(self, task_id: str) -> None:
        self._remove_tree(self._task_workspace(task_id), self.workspace_root)

    def _stage_zip_for_download(self, task_id: str, zip_path: str) -> str:
        source = Path(zip_path)
        if not source.is_file():
            raise FileNotFoundError(f"生成的 ZIP 不存在：{source}")

        download_dir = self.download_root / task_id
        self._remove_tree(download_dir, self.download_root)
        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / source.name
        shutil.move(str(source), target)
        return str(target)

    def _safe_error_message(self, exc: Exception) -> str:
        text = str(exc).strip() or exc.__class__.__name__
        if len(text) > 200:
            text = text[:200] + "…"
        lowered = text.lower()
        if any(key in lowered for key in ("api_key", "apikey", "authorization", "bearer ", ".env")):
            return "上游调用失败，请检查服务端配置"
        return text

    def _reaper(self) -> None:
        while not self._stop.wait(30):
            cutoff = time.time() - self.task_ttl_seconds
            expired: list[str] = []
            with self.lock:
                for task_id, record in list(self.tasks.items()):
                    if record.status in self.TERMINAL and record.updated_at < cutoff:
                        expired.append(task_id)
                        self.tasks.pop(task_id, None)
            for task_id in expired:
                self.cleanup_download(task_id)
                self._clear_task_workspace(task_id)

    def _worker(self) -> None:
        service: ForgeService | None = None
        while True:
            job = self.jobs.get()
            self._update(job.task_id, status="processing", progress="准备生成", percent=8)
            try:
                if service is None:
                    service = self.service_factory()

                def report(message: str, percent: int) -> None:
                    self._update(job.task_id, status="processing", progress=message, percent=percent)

                result = service.run_with_statement(
                    job.pid,
                    job.statement,
                    self._task_workspace(job.task_id),
                    job.num_cases,
                    progress=report,
                    custom_solution=job.custom_solution,
                )
                result.pop("status", None)
                zip_path = self._stage_zip_for_download(job.task_id, result.pop("zip_path"))
                self._set(
                    job.task_id,
                    status="done",
                    progress="已完成，准备下载",
                    percent=100,
                    zip_path=zip_path,
                    **result,
                )
            except Exception as exc:
                self._update(job.task_id, status="failed", progress=self._safe_error_message(exc), percent=100)
            finally:
                self._clear_task_workspace(job.task_id)
                self.jobs.task_done()
