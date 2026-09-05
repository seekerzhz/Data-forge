from __future__ import annotations

import os
import re
import shutil
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from core.generator import GeneratorBuilder
from core.llm import LLMClient, LLMConfig
from core.models import ProblemMeta, SampleCase
from core.naming import build_problem_artifact_name, sanitize_pid
from core.runner import PipelineRunner
from core.sandbox import run_generator_in_sandbox
from core.solution import SolutionBuilder
from core.utils import read_text, write_text


def _package(meta: ProblemMeta, data_dir: Path, zip_path: Path, solution_path: Path) -> None:
    """Build a Hydro-compatible ZIP package from generated test data."""
    root_name = build_problem_artifact_name(meta.pid, meta.title)
    root = data_dir / root_name
    testdata_dir = root / "testdata"
    if root.exists():
        shutil.rmtree(root)
    testdata_dir.mkdir(parents=True, exist_ok=True)

    metadata = {"title": meta.title, "tag": meta.tags}
    if meta.pid:
        metadata["pid"] = meta.pid
    (root / "problem.yaml").write_text(yaml.safe_dump(metadata, allow_unicode=True), encoding="utf-8")
    (root / "problem_zh.md").write_text((meta.statement_markdown or f"# {meta.title}").strip() + "\n", encoding="utf-8")

    if solution_path.is_file():
        shutil.copyfile(solution_path, root / "solution.cpp")

    config = {
        "type": "default",
        "time": meta.time_limit.lower().replace(" ", ""),
        "memory": meta.memory_limit.lower().replace(" ", ""),
        "checker_type": "default",
    }
    (testdata_dir / "config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    for input_file in sorted(data_dir.glob("*.in")):
        shutil.copyfile(input_file, testdata_dir / input_file.name)
        output_file = input_file.with_suffix(".out")
        if output_file.is_file():
            shutil.copyfile(output_file, testdata_dir / output_file.name)

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(data_dir))


class ForgeService:
    """Orchestrates statement polishing, data generation, judging, and packaging."""

    def __init__(self, provider: str | None = None, model: str | None = None, temperature: float = 0.1):
        selected_provider = provider or LLMConfig().provider
        max_tokens = 8192 if selected_provider == "deepseek" else None
        self.llm = LLMClient(
            LLMConfig(provider=selected_provider, model=model, temperature=temperature, max_tokens=max_tokens)
        )
        self.generator_builder = GeneratorBuilder(self.llm, Path("prompts/generator.txt"))
        self.solution_builder = SolutionBuilder(self.llm, Path("prompts/solution.txt"))
        self.statement_system_prompt = read_text(Path("prompts/statement_polish.txt"))
        self.case_workers = max(1, int(os.getenv("DATAFORGE_CASE_WORKERS", "4")))

    def polish_statement(self, raw_markdown: str) -> str:
        """Polish raw Markdown while preserving the original content as fallback."""
        polished = self.llm.chat(self.statement_system_prompt, raw_markdown).strip()
        return polished if polished else raw_markdown

    @staticmethod
    def parse_statement(problem_id: str, statement_markdown: str) -> ProblemMeta:
        """Parse Markdown into sanitized metadata used by later pipeline stages."""
        title_match = re.search(r"^#\s*(.+)$", statement_markdown, flags=re.MULTILINE)
        title = title_match.group(1).strip() if title_match else (problem_id or "Untitled Problem")
        generic_titles = {"题目描述", "未命名", "untitled problem", "title", "problem"}
        if title.lower() in generic_titles:
            fallback = re.search(r"##\s*题目描述\s*(.+)", statement_markdown)
            if fallback:
                rough = re.sub(r"[。！？!?].*", "", fallback.group(1)).strip()
                if rough:
                    title = rough[:30]
            if title.lower() in generic_titles:
                title = (problem_id or "未命名题目").strip() or "未命名题目"

        pid_match = re.search(r"(P\d+)", title, flags=re.I)
        raw_pid = (problem_id or "").strip() or (pid_match.group(1).upper() if pid_match else "")
        pid = sanitize_pid(raw_pid)

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

        return ProblemMeta(
            pid=pid,
            title=title,
            time_limit="1s",
            memory_limit="128MB",
            description=description,
            input_spec=input_spec,
            output_spec=output_spec,
            statement_markdown=statement_markdown,
            samples=samples,
        )

    @staticmethod
    def _collect_and_flatten_inputs(problem_dir: Path, data_dir: Path) -> int:
        """Collect generated `.in` files into a flat Hydro testdata directory."""
        input_files = [
            path
            for path in problem_dir.rglob("*.in")
            if path.is_file()
            and "build" not in path.parts
            and "source" not in path.parts
            and (data_dir not in path.parents or path.parent == data_dir)
        ]
        if not input_files:
            return 0
        for idx, src in enumerate(sorted(set(input_files)), 1):
            dst = data_dir / f"{idx}.in"
            if src.resolve() != dst.resolve():
                shutil.copyfile(src, dst)
        return len(set(input_files))

    def _generate_cases_parallel(
        self,
        problem_dir: Path,
        num_cases: int,
        progress: Callable[[str, int], None] | None,
    ) -> None:
        """Generate test inputs concurrently within a bounded worker pool."""
        completed = 0
        data_dir = problem_dir / "testdata"
        data_dir.mkdir(parents=True, exist_ok=True)

        def one(case_id: int) -> int:
            staging_dir = f"build/generated/{case_id}"
            generated = run_generator_in_sandbox(
                problem_dir,
                "source/generator.py",
                case_id,
                output_dir=staging_dir,
            )
            shutil.copyfile(generated, data_dir / f"{case_id}.in")
            return case_id

        with ThreadPoolExecutor(max_workers=min(self.case_workers, num_cases)) as pool:
            futures = [pool.submit(one, i) for i in range(1, num_cases + 1)]
            for future in as_completed(futures):
                future.result()
                completed += 1
                if progress:
                    progress(
                        f"生成测试数据 {completed}/{num_cases}",
                        46 + int(32 * completed / max(1, num_cases)),
                    )

    def run_with_statement(
        self,
        pid: str,
        raw_statement: str,
        workspace: Path,
        num_cases: int = 15,
        progress: Callable[[str, int], None] | None = None,
        custom_solution: str | None = None,
    ) -> dict:
        """Run the full generation pipeline for one submitted problem statement."""

        def report(message: str, percent: int) -> None:
            if progress:
                progress(message, percent)

        report("润色题面", 12)
        polished = self.polish_statement(raw_statement)
        report("解析题面", 22)
        meta = self.parse_statement(pid, polished)
        folder = build_problem_artifact_name(meta.pid, meta.title, fallback="no_pid")
        problem_dir = workspace / folder
        source_dir, data_dir, build_dir = problem_dir / "source", problem_dir / "testdata", problem_dir / "build"
        for d in (source_dir, data_dir, build_dir):
            d.mkdir(parents=True, exist_ok=True)

        write_text(problem_dir / "problem_zh.md", meta.statement_markdown + "\n")
        report("生成数据生成器", 34)
        generator_code = self.generator_builder.build(
            meta.statement_markdown,
            num_cases,
            2,
            2,
            max(1, num_cases // 2),
            max(1, num_cases // 3),
        )
        write_text(source_dir / "generator.py", generator_code)
        if custom_solution and custom_solution.strip():
            report("使用自定义标准解", 46)
            write_text(source_dir / "solution.cpp", custom_solution.strip() + "\n")
        else:
            report("生成标准解", 46)
            write_text(source_dir / "solution.cpp", self.solution_builder.build(meta.statement_markdown))

        self._generate_cases_parallel(problem_dir, num_cases, progress)

        report("整理输入文件", 80)
        in_count = self._collect_and_flatten_inputs(problem_dir, data_dir)
        if in_count == 0:
            raise RuntimeError("未找到任何 .in 文件")

        runner = PipelineRunner(data_dir)
        report("编译标准解", 84)
        runner.compile_solution(str((source_dir / "solution.cpp").resolve()), "solution")
        report("生成输出文件", 88)
        outputs, skipped = runner.produce_outputs("./solution")

        report("打包 ZIP", 96)
        zip_name = build_problem_artifact_name(meta.pid, meta.title, max_length=70)
        zip_path = build_dir / f"{zip_name}.zip"
        _package(meta, data_dir, zip_path, source_dir / "solution.cpp")
        report("完成", 100)
        return {
            "zip_path": str(zip_path),
            "status": "success",
            "inputs": in_count,
            "outputs": len(outputs),
            "skipped": len(skipped),
        }
