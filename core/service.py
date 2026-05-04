from __future__ import annotations

import hashlib
import shutil
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

    @staticmethod
    def _collect_and_flatten_inputs(problem_dir: Path, data_dir: Path) -> int:
        input_files = [
            p for p in problem_dir.rglob("*.in")
            if p.is_file() and "build" not in p.parts and "source" not in p.parts
        ]
        if not input_files:
            return 0
        seen = set()
        unique_files = []
        for f in sorted(input_files):
            key = str(f.resolve())
            if key not in seen:
                seen.add(key)
                unique_files.append(f)
        for idx, src in enumerate(unique_files, 1):
            dst = data_dir / f"{idx}.in"
            if src.resolve() != dst.resolve():
                shutil.copyfile(src, dst)
        return len(unique_files)

    @staticmethod
    def _preview_outputs(data_dir: Path, limit: int = 3) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for out_file in sorted(data_dir.glob("*.out"))[:limit]:
            content = out_file.read_text(encoding="utf-8", errors="ignore").strip()
            items.append({"file": out_file.name, "preview": content[:300]})
        return items

    def run_mvp(self, problem: str, workspace: Path, num_cases: int = 15, include_samples: bool = True) -> dict:
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

        in_count = self._collect_and_flatten_inputs(problem_dir, data_dir)
        if in_count == 0:
            raise RuntimeError("未找到任何 .in 文件：请检查生成器是否写入了非 .in 后缀或写到了受限目录")

        runner = PipelineRunner(data_dir)
        runner.compile_solution(str((source_dir / "solution.cpp").resolve()), "solution")
        outputs, skipped = runner.produce_outputs("./solution")

        cache_key = hashlib.md5(f"{meta.pid}-{num_cases}-{include_samples}".encode()).hexdigest()[:12]
        zip_path = build_dir / f"{meta.pid}_{cache_key}.zip"
        build_hydro_package(meta, data_dir, zip_path)
        return {
            "zip_path": str(zip_path),
            "pid": meta.pid,
            "title": meta.title,
            "inputs": in_count,
            "outputs": len(outputs),
            "skipped": len(skipped),
            "output_preview": self._preview_outputs(data_dir),
        }
