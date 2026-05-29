from __future__ import annotations

import queue
import threading
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


@dataclass
class TaskRecord:
    status: str
    progress: str
    percent: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "progress": self.progress, "percent": self.percent, **self.details}


class TaskQueue:
    def __init__(
        self,
        workspace_root: Path = Path("workspace/tasks"),
        workers: int = 3,
        service_factory: Callable[[], ForgeService] = ForgeService,
    ):
        self.workspace_root = workspace_root
        self.service_factory = service_factory
        self.jobs: "queue.Queue[TaskJob]" = queue.Queue()
        self.tasks: dict[str, TaskRecord] = {}
        self.lock = threading.Lock()
        for _ in range(workers):
            threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, pid: str, statement: str, num_cases: int) -> str:
        task_id = str(uuid.uuid4())
        self._set(task_id, status="waiting", progress="等待处理", percent=4)
        self.jobs.put(TaskJob(task_id=task_id, pid=pid, statement=statement, num_cases=num_cases))
        return task_id

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self.lock:
            record = self.tasks.get(task_id)
            return record.as_dict() if record else None

    def finish(self, task_id: str) -> bool:
        with self.lock:
            record = self.tasks.get(task_id)
            if not record:
                return False
            record.status = "finished"
            record.progress = "任务已结束"
            record.percent = 100
            return True

    def _set(self, task_id: str, status: str, progress: str, percent: int, **details: Any) -> None:
        percent = max(0, min(100, int(percent)))
        with self.lock:
            self.tasks[task_id] = TaskRecord(status=status, progress=progress, percent=percent, details=details)

    def _update(self, task_id: str, status: str | None = None, progress: str | None = None, percent: int | None = None, **details: Any) -> None:
        with self.lock:
            record = self.tasks.setdefault(task_id, TaskRecord(status="waiting", progress="等待处理", percent=0))
            if status is not None:
                record.status = status
            if progress is not None:
                record.progress = progress
            if percent is not None:
                record.percent = max(0, min(100, int(percent)))
            record.details.update(details)

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
                    self.workspace_root / job.task_id,
                    job.num_cases,
                    progress=report,
                )
                result.pop("status", None)
                self._set(job.task_id, status="done", progress="已完成，准备下载", percent=100, **result)
            except Exception as exc:
                self._update(job.task_id, status="failed", progress=str(exc), percent=100)
            finally:
                self.jobs.task_done()
