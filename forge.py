#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from core.generator import GeneratorBuilder
from core.llm import LLMClient, LLMConfig
from core.runner import PipelineRunner
from core.solution import SolutionBuilder
from core.utils import read_text, write_text


def allocate_case_groups(total: int) -> tuple[int, int, int, int]:
    """Return (small, special, random, max)."""
    if total <= 0:
        raise ValueError("--num-cases 必须大于 0")

    small = max(1, round(total * 0.1))
    special = max(1, round(total * 0.1))
    random_cnt = max(1, round(total * 0.4))
    max_cnt = max(1, total - small - special - random_cnt)

    while small + special + random_cnt + max_cnt > total:
        if random_cnt > 1:
            random_cnt -= 1
        elif max_cnt > 1:
            max_cnt -= 1
        elif special > 1:
            special -= 1
        else:
            small -= 1

    while small + special + random_cnt + max_cnt < total:
        max_cnt += 1

    return small, special, random_cnt, max_cnt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DataForge: one-command generate.py + solution.cpp + .in/.out")
    parser.add_argument("problem", type=Path, help="Path to problem statement")
    parser.add_argument("--workspace", type=Path, default=Path("workspace/run"), help="Output directory")
    parser.add_argument("--provider", choices=["openai", "ark"], default="ark")
    parser.add_argument("--model", default=None, help="Override model name from .env")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--num-cases", type=int, default=50, help="Number of test cases to generate")
    parser.add_argument("--skip-run", action="store_true", help="Only generate source files")
    parser.add_argument("--no-generate-solution", action="store_true", help="Use existing solution instead of LLM")
    parser.add_argument("--solution-path", type=Path, default=None, help="Path to user solution.cpp when no generation")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per test case runtime timeout in seconds")
    return parser.parse_args()


def resolve_solution(workspace: Path, user_solution: Path | None) -> Path:
    target = workspace / "solution.cpp"
    if user_solution is None:
        if not target.exists():
            raise FileNotFoundError("未生成解法时，需要提供 --solution-path 或提前在 workspace 放置 solution.cpp")
        return target

    src = user_solution.resolve()
    if not src.exists():
        raise FileNotFoundError(f"solution 文件不存在: {src}")
    if src != target.resolve():
        shutil.copyfile(src, target)
    return target


def main() -> None:
    args = parse_args()
    problem_text = read_text(args.problem)
    small, special, random_cnt, max_cnt = allocate_case_groups(args.num_cases)

    llm = LLMClient(LLMConfig(provider=args.provider, model=args.model, temperature=args.temperature))
    generator = GeneratorBuilder(llm, Path("prompts/generator.txt"))

    workspace = args.workspace
    workspace.mkdir(parents=True, exist_ok=True)

    gen_code = generator.build(
        problem_statement=problem_text,
        total_cases=args.num_cases,
        small_cases=small,
        special_cases=special,
        random_cases=random_cnt,
        max_cases=max_cnt,
    )
    write_text(workspace / "generate.py", gen_code)
    print(f"[DataForge] Generated: {workspace / 'generate.py'}")
    print(
        "[DataForge] Case mix => "
        f"small={small}, special={special}, random={random_cnt}, max={max_cnt}, total={args.num_cases}"
    )

    if args.no_generate_solution:
        solution_cpp = resolve_solution(workspace, args.solution_path)
        print(f"[DataForge] Using existing solution: {solution_cpp}")
    else:
        solution_builder = SolutionBuilder(llm, Path("prompts/solution.txt"))
        sol_code = solution_builder.build(problem_text)
        write_text(workspace / "solution.cpp", sol_code)
        print(f"[DataForge] Generated: {workspace / 'solution.cpp'}")

    if args.skip_run:
        print("[DataForge] Execution skipped by --skip-run")
        return

    runner = PipelineRunner(workspace)
    runner.run_generator("generate.py")
    runner.compile_solution("solution.cpp", "solution")
    outputs, skipped = runner.produce_outputs("./solution", per_case_timeout_s=args.timeout)

    print(f"[DataForge] .in files: {len(list(workspace.glob('*.in')))}")
    print(f"[DataForge] .out files: {len(outputs)}")
    if skipped:
        print(f"[DataForge][WARN] Skipped by timeout: {len(skipped)}")


if __name__ == "__main__":
    main()
