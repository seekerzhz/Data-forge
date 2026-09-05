from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def sandbox_backend() -> str:
    """Return the configured sandbox backend: bwrap (preferred) or rlimit."""
    configured = os.getenv("DATAFORGE_SANDBOX", "auto").strip().lower()
    if configured in {"bwrap", "bubblewrap"}:
        if not shutil.which("bwrap"):
            raise RuntimeError("DATAFORGE_SANDBOX=bwrap 但系统未找到 bwrap")
        return "bwrap"
    if configured == "rlimit":
        return "rlimit"
    return "bwrap" if shutil.which("bwrap") else "rlimit"


def _prlimit_prefix(cpu_seconds: int, memory_mb: int) -> list[str]:
    """Prefer prlimit over preexec_fn so limits stay safe under worker threads."""
    if not shutil.which("prlimit"):
        return []
    memory_bytes = memory_mb * 1024 * 1024
    return [
        "prlimit",
        f"--cpu={cpu_seconds}",
        f"--as={memory_bytes}",
        f"--fsize={20 * 1024 * 1024}",
        f"--nofile=64",
        f"--nproc=64",
        "--",
    ]


def _bwrap_command(workdir: Path, argv: list[str]) -> list[str]:
    """Build a bubblewrap argv that isolates network and filesystem writes."""
    work = workdir.resolve()
    # bubblewrap 0.4 may lack --clearenv; unset sensitive vars explicitly.
    unset_vars = [
        "DEEPSEEK_API_KEY",
        "ARK_API_KEY",
        "OPENAI_API_KEY",
        "OPENAI_COMPAT_API_KEY",
        "DATAFORGE_API_TOKEN",
        "AWS_SECRET_ACCESS_KEY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    cmd = [
        "bwrap",
        "--die-with-parent",
        "--new-session",
        "--unshare-net",
        "--unshare-pid",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind-try",
        "/lib64",
        "/lib64",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind-try",
        "/sbin",
        "/sbin",
        "--ro-bind-try",
        "/etc/ld.so.cache",
        "/etc/ld.so.cache",
        "--ro-bind-try",
        "/etc/localtime",
        "/etc/localtime",
        "--bind",
        str(work),
        str(work),
        "--chdir",
        str(work),
        "--setenv",
        "HOME",
        str(work),
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "--setenv",
        "LANG",
        os.getenv("LANG", "C.UTF-8"),
        "--setenv",
        "LC_ALL",
        os.getenv("LC_ALL", "C.UTF-8"),
    ]
    for name in unset_vars:
        cmd.extend(["--unsetenv", name])
    cmd.extend(["--", *argv])
    return cmd


def run_sandboxed(
    workdir: Path,
    argv: list[str],
    *,
    timeout_s: float = 5.0,
    memory_mb: int = 256,
    stdin=None,
    stdout=None,
    stderr=None,
) -> subprocess.CompletedProcess[bytes]:
    """Run argv inside the best available sandbox, rooted at workdir."""
    backend = sandbox_backend()
    cpu_seconds = max(1, int(timeout_s) + 1)
    limited_argv = _prlimit_prefix(cpu_seconds, memory_mb) + argv
    # Never wrap bwrap itself with prlimit — that can break user-namespace creation.
    if backend == "bwrap":
        cmd = _bwrap_command(workdir, limited_argv)
        cwd = None
    else:
        cmd = limited_argv
        cwd = workdir
    return subprocess.run(
        cmd,
        cwd=cwd,
        timeout=timeout_s,
        check=True,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


def run_generator_in_sandbox(
    workspace: Path,
    script_name: str,
    case_id: int,
    timeout_s: int = 5,
    output_dir: str = "testdata",
) -> Path:
    """Execute generated Python data generator with constrained resources.

    Args:
        workspace: Problem workspace used as the subprocess working directory.
        script_name: Generator path relative to `workspace`.
        case_id: Current test case id passed to the generator.
        timeout_s: Wall-clock and CPU timeout in seconds.
        output_dir: Directory, relative to ``workspace``, where this invocation
            must write its input file.

    Returns:
        The generated input file path.

    Raises:
        RuntimeError: If the generator exits successfully but produces no input.
    """
    # Prefer system python inside the sandbox (stdlib only); avoid host venv paths.
    python = "/usr/bin/python3" if Path("/usr/bin/python3").is_file() else "python3"
    destination = workspace / output_dir
    destination.mkdir(parents=True, exist_ok=True)
    result = run_sandboxed(
        workspace,
        [python, script_name, "--id", str(case_id), "--output-dir", output_dir],
        timeout_s=timeout_s,
        memory_mb=256,
        stdout=subprocess.PIPE,
    )
    expected = destination / f"{case_id}.in"
    if expected.is_file():
        return expected

    # Some otherwise valid LLM-generated scripts print a case instead of writing
    # the requested file. Preserve that data rather than failing the whole task.
    if result.stdout and result.stdout.strip():
        expected.write_bytes(result.stdout)
        return expected

    candidates = sorted(path for path in destination.rglob("*.in") if path.is_file())
    if len(candidates) == 1:
        shutil.copyfile(candidates[0], expected)
        return expected

    # Older generated scripts commonly hard-code ``testdata/<id>.in`` (or a
    # file in the workspace) despite accepting --output-dir.  Case invocations
    # now use isolated staging directories, so retain compatibility with those
    # scripts by recovering only the file for *this* case.  Matching the case
    # name, rather than accepting an arbitrary .in file, prevents one parallel
    # invocation from being assigned another invocation's input.
    legacy_name = f"{case_id}.in"
    legacy_candidates = [
        workspace / legacy_name,
        workspace / "testdata" / legacy_name,
    ]
    legacy_candidates.extend(
        path
        for path in workspace.rglob(legacy_name)
        if path.is_file() and destination not in path.parents and path != expected
    )
    for candidate in sorted(set(legacy_candidates)):
        if candidate.is_file():
            shutil.copyfile(candidate, expected)
            return expected

    raise RuntimeError(
        f"生成器未为用例 {case_id} 写入 .in 文件；期望路径：{expected}"
    )
