from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from core.generator import GeneratorBuilder
from core.hydro import build_hydro_package
from core.llm import LLMClient, LLMConfig
from core.models import ProblemMeta, SampleCase
from core.runner import PipelineRunner
from core.sandbox import run_generator_in_sandbox
from core.solution import SolutionBuilder
from core.utils import read_text, write_text


class ForgeService:
    def __init__(self, provider: str = "ark", model: str | None = None, temperature: float = 0.1):
        self.llm = LLMClient(LLMConfig(provider=provider, model=model, temperature=temperature))
        self.generator_builder = GeneratorBuilder(self.llm, Path("prompts/generator.txt"))
        self.solution_builder = SolutionBuilder(self.llm, Path("prompts/solution.txt"))
        self.statement_system_prompt = read_text(Path("prompts/statement_polish.txt"))

    def polish_statement(self, raw_markdown: str) -> str:
        polished = self.llm.chat(self.statement_system_prompt, raw_markdown).strip()
        return polished if polished else raw_markdown

    @staticmethod
    def parse_statement(problem_id: str, statement_markdown: str) -> ProblemMeta:
        title_match = re.search(r"^#\s*(.+)$", statement_markdown, flags=re.MULTILINE)
        title = title_match.group(1).strip() if title_match else (problem_id or "Untitled Problem")
        pid_match = re.search(r"(P\d+)", title, flags=re.I)
        pid = (problem_id or "").strip() or (pid_match.group(1).upper() if pid_match else "")

        def sec(name: str) -> str:
            m = re.search(rf"##\s*{re.escape(name)}\s*(.*?)(?=\n##\s|\Z)", statement_markdown, flags=re.S)
            return m.group(1).strip() if m else ""

        description = sec("题目描述")
        input_spec = sec("输入格式")
        output_spec = sec("输出格式")
        samples: list[SampleCase] = []
        in_m = re.search(r"##\s*样例输入\s*```plaintext\s*(.*?)\s*```", statement_markdown, flags=re.S)
        out_m = re.search(r"##\s*样例输出\s*```plaintext\s*(.*?)\s*```", statement_markdown, flags=re.S)
        if in_m and out_m:
            samples.append(SampleCase(in_m.group(1).strip(), out_m.group(1).strip()))

        return ProblemMeta(pid=pid, title=title, time_limit="1s", memory_limit="128MB", description=description, input_spec=input_spec, output_spec=output_spec, statement_markdown=statement_markdown, samples=samples)

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

    def run_with_statement(self, pid: str, raw_statement: str, workspace: Path, num_cases: int = 15) -> dict:
        polished = self.polish_statement(raw_statement)
        meta = self.parse_statement(pid, polished)
        folder = meta.pid if meta.pid else "no_pid"
        problem_dir = workspace / folder
        source_dir, data_dir, build_dir = problem_dir / "source", problem_dir / "testdata", problem_dir / "build"
        for d in (source_dir, data_dir, build_dir):
            d.mkdir(parents=True, exist_ok=True)

        write_text(problem_dir / "problem_zh.md", meta.statement_markdown + "\n")
        write_text(source_dir / "generator.py", self.generator_builder.build(meta.statement_markdown, num_cases, 2, 2, max(1, num_cases // 2), max(1, num_cases // 3)))
        write_text(source_dir / "solution.cpp", self.solution_builder.build(meta.statement_markdown))

        for i in range(1, num_cases + 1):
            run_generator_in_sandbox(problem_dir, "source/generator.py", i)

        in_count = self._collect_and_flatten_inputs(problem_dir, data_dir)
        if in_count == 0:
            raise RuntimeError("未找到任何 .in 文件")

        runner = PipelineRunner(data_dir)
        runner.compile_solution(str((source_dir / "solution.cpp").resolve()), "solution")
        outputs, skipped = runner.produce_outputs("./solution")

        safe_title = re.sub(r"[^\w\-\u4e00-\u9fff]+", "-", meta.title).strip("-")[:50]
        key = hashlib.md5(f"{meta.title}-{num_cases}".encode()).hexdigest()[:8]
        prefix = f"{meta.pid}-" if meta.pid else ""
        zip_path = build_dir / f"{prefix}{safe_title}-{key}.zip"
        build_hydro_package(meta, data_dir, zip_path, solution_path=source_dir / "solution.cpp")
        return {"zip_path": str(zip_path), "status": "success", "inputs": in_count, "outputs": len(outputs), "skipped": len(skipped)}
