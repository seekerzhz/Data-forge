from __future__ import annotations

from pydantic import BaseModel, Field


class TaskReq(BaseModel):
    pid: str = Field(default="", max_length=64)
    statement_markdown: str = Field(min_length=1, max_length=100_000)
    num_cases: int = Field(default=20, ge=1, le=100)
    custom_solution: str | None = Field(default=None, max_length=200_000)
