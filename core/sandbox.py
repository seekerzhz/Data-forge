from __future__ import annotations

import resource
import subprocess
from pathlib import Path


def _limit_resources(cpu_seconds: int, memory_mb: int) -> None:
    """Apply CPU, memory, and output-size limits before executing generated code."""
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    memory_bytes = memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (20 * 1024 * 1024, 20 * 1024 * 1024))


def run_generator_in_sandbox(workspace: Path, script_name: str, case_id: int, timeout_s: int = 5) -> None:
    """Execute generated Python data generator with constrained resources.

    Args:
        workspace: Problem workspace used as the subprocess working directory.
        script_name: Generator path relative to `workspace`.
        case_id: Current test case id passed to the generator.
        timeout_s: Wall-clock and CPU timeout in seconds.
    """
    subprocess.run(
        ["python3", script_name, "--id", str(case_id), "--output-dir", "testdata"],
        cwd=workspace,
        timeout=timeout_s,
        check=True,
        preexec_fn=lambda: _limit_resources(cpu_seconds=timeout_s, memory_mb=256),
    )
