from __future__ import annotations

import hashlib
import re
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

    @staticmethod
    def parse_statement(problem_id: str, statement_markdown: str) -> ProblemMeta:
        title_match = re.search(r"^#\s*(.+)$", statement_markdown, flags=re.MULTILINE)
        title = title_match.group(1).strip() if title_match else problem_id
        pid_match = re.search(r"(P\d+)", title, flags=re.I)
        pid = (problem_id or "").strip() or (pid_match.group(1).upper() if pid_match else "P0000")

        def sec(name: str) -> str:
            m = re.search(rf"##\s*{re.escape(name)}\s*(.*?)(?=\n##\s|\Z)", statement_markdown, flags=re.S)
            return m.group(1).strip() if m else ""

        description = sec("题目描述") or sec("Description")
        input_spec = sec("输入格式") or sec("Input")
        output_spec = sec("输出格式") or sec("Output")
        sample_pairs = []
        pattern = re.compile(r"###\s*输入\s*#?\d+\s*```\s*(.*?)\s*```\s*###\s*输出\s*#?\d+\s*```\s*(.*?)\s*```", re.S)
        for m in pattern.finditer(statement_markdown):
            from core.models import SampleCase
            sample_pairs.append(SampleCase(m.group(1).strip(), m.group(2).strip()))

        return ProblemMeta(
            pid=pid,
            title=title,
            time_limit="1s",
            memory_limit="128MB",
            description=description,
            input_spec=input_spec,
            output_spec=output_spec,
            statement_markdown=statement_markdown,
            samples=sample_pairs,
        )

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
        input_files = [p for p in problem_dir.rglob("*.in") if p.is_file() and "build" not in p.parts and "source" not in p.parts]
        if not input_files:
            return 0
        for idx, src in enumerate(sorted(set(input_files)), 1):
            dst = data_dir / f"{idx}.in"
            if src.resolve() != dst.resolve():
                shutil.copyfile(src, dst)
        return len(set(input_files))

    @staticmethod
    def _preview_outputs(data_dir: Path, limit: int = 3) -> list[dict[str, str]]:
        return [
            {"file": out_file.name, "preview": out_file.read_text(encoding="utf-8", errors="ignore").strip()[:300]}
            for out_file in sorted(data_dir.glob("*.out"))[:limit]
        ]

    def run_with_meta(self, meta: ProblemMeta, workspace: Path, num_cases: int = 15, include_samples: bool = True) -> dict:
        problem_dir = workspace / meta.pid
        source_dir = problem_dir / "source"
        data_dir = problem_dir / "testdata"
        build_dir = problem_dir / "build"
        for d in (source_dir, data_dir, build_dir):
            d.mkdir(parents=True, exist_ok=True)

        text = meta.statement_markdown.strip() or f"# {meta.title}\n\n## 题目描述\n\n{meta.description}"
        write_text(problem_dir / "problem_zh.md", text + "\n")
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
        safe_title = re.sub(r"[^\w\-\u4e00-\u9fff]+", "-", meta.title).strip("-")[:50]
        zip_path = build_dir / f"{meta.pid}-{safe_title}-{cache_key}.zip"
        build_hydro_package(meta, data_dir, zip_path, solution_path=source_dir / "solution.cpp")
        return {"zip_path": str(zip_path), "pid": meta.pid, "title": meta.title, "inputs": in_count, "outputs": len(outputs), "skipped": len(skipped), "output_preview": self._preview_outputs(data_dir)}

    def run_mvp(self, problem: str, workspace: Path, num_cases: int = 15, include_samples: bool = True) -> dict:
        return self.run_with_meta(self.get_problem(problem), workspace, num_cases, include_samples)
