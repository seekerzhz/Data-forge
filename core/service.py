from __future__ import annotations

import hashlib
from pathlib import Path

from core.generator import GeneratorBuilder
from core.hydro import build_hydro_package
from core.llm import LLMClient, LLMConfig
from core.luogu import LuoguClient, fallback_from_raw
from core.models import ProblemMeta
from core.runner import PipelineRunner
from core.sandbox import run_generator_in_sandbox
from core.solution import SolutionBuilder
from core.utils import write_text


class ForgeService:
    def __init__(self, provider: str = "ark", model: str | None = None, temperature: float = 0.1):
        self.llm = LLMClient(LLMConfig(provider=provider, model=model, temperature=temperature))
        self.generator_builder = GeneratorBuilder(self.llm, Path("prompts/generator.txt"))
        self.solution_builder = SolutionBuilder(self.llm, Path("prompts/solution.txt"))
        self.luogu = LuoguClient(cookie=None)

    def get_problem(self, problem: str, raw_text: str | None = None, title: str | None = None) -> ProblemMeta:
        try:
            return self.luogu.fetch(problem)
        except Exception:
            if not raw_text:
                raise
            pid = self.luogu.normalize_pid(problem)
            return fallback_from_raw(pid, title or pid, raw_text)

    def run_mvp(self, problem: str, workspace: Path, num_cases: int = 15, include_samples: bool = True) -> Path:
        meta = self.get_problem(problem)
        problem_dir = workspace / meta.pid
        source_dir = problem_dir / "source"
        data_dir = problem_dir / "testdata"
        build_dir = problem_dir / "build"
        for d in (source_dir, data_dir, build_dir):
            d.mkdir(parents=True, exist_ok=True)

        text = meta.statement_markdown.strip() or (
            f"{meta.title}\n\n{meta.description}\n\n输入:\n{meta.input_spec}\n\n输出:\n{meta.output_spec}"
        )
        script = self.generator_builder.build(text, num_cases, 2, 2, max(1, num_cases // 2), max(1, num_cases // 3))
        write_text(source_dir / "generator.py", script)
        write_text(source_dir / "solution.cpp", self.solution_builder.build(text))

        for i in range(1, num_cases + 1):
            run_generator_in_sandbox(problem_dir, "source/generator.py", i)

        runner = PipelineRunner(data_dir)
        runner.compile_solution(str((source_dir / "solution.cpp").resolve()), "solution")
        runner.produce_outputs("./solution")

        cache_key = hashlib.md5(f"{meta.pid}-{num_cases}-{include_samples}".encode()).hexdigest()[:12]
        zip_path = build_dir / f"{meta.pid}_{cache_key}.zip"
        return build_hydro_package(meta, data_dir, zip_path)
