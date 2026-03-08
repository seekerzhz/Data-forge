#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from core.generator import GeneratorBuilder
from core.llm import LLMClient, LLMConfig
from core.runner import PipelineRunner
from core.solution import SolutionBuilder
from core.utils import read_text, write_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DataForge: 一键生成 generate.py + solution.cpp + .out")
    parser.add_argument("problem", type=Path, help="题面文件路径")
    parser.add_argument("--workspace", type=Path, default=Path("workspace/run"), help="输出目录")
    parser.add_argument("--provider", choices=["openai", "ark"], default="openai")
    parser.add_argument("--model", default=None, help="覆盖默认模型")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--skip-run", action="store_true", help="只生成代码，不执行数据生产流程")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    problem_text = read_text(args.problem)

    llm = LLMClient(LLMConfig(provider=args.provider, model=args.model, temperature=args.temperature))
    generator = GeneratorBuilder(llm, Path("prompts/generator.txt"))
    solution = SolutionBuilder(llm, Path("prompts/solution.txt"))

    workspace = args.workspace
    workspace.mkdir(parents=True, exist_ok=True)

    gen_code = generator.build(problem_text)
    sol_code = solution.build(problem_text)

    write_text(workspace / "generate.py", gen_code)
    write_text(workspace / "solution.cpp", sol_code)

    print(f"[DataForge] 已生成: {workspace / 'generate.py'}")
    print(f"[DataForge] 已生成: {workspace / 'solution.cpp'}")

    if args.skip_run:
        print("[DataForge] 已跳过执行阶段（--skip-run）")
        return

    runner = PipelineRunner(workspace)
    runner.run_generator("generate.py")
    runner.compile_solution("solution.cpp", "solution")
    outputs = runner.produce_outputs("./solution")

    print(f"[DataForge] 已生成输入文件: {len(list(workspace.glob('*.in')))} 个")
    print(f"[DataForge] 已生成输出文件: {len(outputs)} 个")


if __name__ == "__main__":
    main()
