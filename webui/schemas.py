from __future__ import annotations

from pydantic import BaseModel, Field


class TaskReq(BaseModel):
    pid: str = ""
    statement_markdown: str = Field(min_length=1)
    num_cases: int = Field(default=20, ge=1)
