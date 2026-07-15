from __future__ import annotations

import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request


def api_token() -> str:
    """Shared API token from env; empty means auth is disabled (local-only deployments)."""
    return os.getenv("DATAFORGE_API_TOKEN", "").strip()


def require_auth_enabled() -> bool:
    return bool(api_token())


def verify_api_token(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    token: str | None = None,
) -> None:
    """Reject requests when DATAFORGE_API_TOKEN is set and credentials do not match."""
    expected = api_token()
    if not expected:
        return

    provided = (x_api_token or "").strip()
    if not provided and authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            provided = value.strip()
    if not provided and token:
        provided = token.strip()

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


class RateLimiter:
    """Simple per-IP sliding-window rate limiter."""

    def __init__(self, limit_per_minute: int | None = None):
        self.limit = max(1, int(limit_per_minute or os.getenv("DATAFORGE_RATE_LIMIT_PER_MINUTE", "30")))
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = 60.0
        with self._lock:
            bucket = self._hits[client]
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                raise HTTPException(status_code=429, detail="rate limit exceeded")
            bucket.append(now)


def public_task_view(task: dict) -> dict:
    """Strip internal fields such as zip_path from API payloads."""
    allow = {"status", "progress", "percent", "inputs", "outputs", "skipped"}
    return {key: value for key, value in task.items() if key in allow}
