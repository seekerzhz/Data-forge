from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SampleCase:
    input_data: str
    output_data: str


@dataclass
class ProblemMeta:
    pid: str
    title: str
    time_limit: str
    memory_limit: str
    description: str
    input_spec: str
    output_spec: str
    statement_markdown: str = ""
    tags: list[str] = field(default_factory=list)
    difficulty: str = "unknown"
    samples: list[SampleCase] = field(default_factory=list)
