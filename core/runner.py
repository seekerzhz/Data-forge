from __future__ import annotations

import subprocess
from pathlib import Path

from core.utils import sort_input_files


class PipelineRunner:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def _run(self, cmd: list[str]) -> None:
        subprocess.run(cmd, cwd=self.workspace, check=True)

    def run_generator(self, script_name: str = "generate.py") -> None:
        self._run(["python3", script_name])

    def compile_solution(self, source: str = "solution.cpp", output: str = "solution") -> None:
        self._run(["g++", "-std=c++17", "-O2", "-o", output, source])

    def produce_outputs(self, exe: str = "./solution") -> list[Path]:
        input_files = sort_input_files(list(self.workspace.glob("*.in")))
        outputs: list[Path] = []
        for input_file in input_files:
            output_file = input_file.with_suffix(".out")
            with input_file.open("rb") as fin, output_file.open("wb") as fout:
                subprocess.run([exe], cwd=self.workspace, stdin=fin, stdout=fout, check=True)
            outputs.append(output_file)
        return outputs
