from __future__ import annotations

import subprocess
from pathlib import Path

from core.sandbox import run_sandboxed
from core.utils import sort_input_files


class PipelineRunner:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def _run(self, cmd: list[str]) -> None:
        """Run a host-side build command in the runner workspace."""
        subprocess.run(cmd, cwd=self.workspace, check=True)

    def compile_solution(self, source: str = "solution.cpp", output: str = "solution") -> None:
        """Compile the generated C++17 standard solution.

        Args:
            source: Path to the source file, absolute or relative to the workspace.
            output: Executable name emitted inside the workspace.
        """
        self._run(["g++", "-std=c++17", "-O2", "-o", output, source])

    def produce_outputs(self, exe: str = "./solution", per_case_timeout_s: float = 5.0) -> tuple[list[Path], list[Path]]:
        """Run the compiled solution for each `.in` file to produce `.out` files.

        Args:
            exe: Executable path relative to the workspace.
            per_case_timeout_s: Maximum seconds allowed for each input.

        Returns:
            A tuple of produced output files and skipped input files.
        """
        input_files = sort_input_files(list(self.workspace.glob("*.in")))
        outputs: list[Path] = []
        skipped: list[Path] = []
        exe_name = Path(exe).name
        for input_file in input_files:
            output_file = input_file.with_suffix(".out")
            try:
                with input_file.open("rb") as fin, output_file.open("wb") as fout:
                    run_sandboxed(
                        self.workspace,
                        [f"./{exe_name}"],
                        timeout_s=per_case_timeout_s,
                        memory_mb=512,
                        stdin=fin,
                        stdout=fout,
                        stderr=subprocess.DEVNULL,
                    )
                outputs.append(output_file)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                skipped.append(input_file)
                if output_file.exists():
                    output_file.unlink()
                print(f"[DataForge][WARN] {input_file.name} 运行失败或超时，已跳过")
        return outputs, skipped
