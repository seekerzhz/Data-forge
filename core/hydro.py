from __future__ import annotations

import shutil
from pathlib import Path
import zipfile

import yaml

from core.models import ProblemMeta


def build_hydro_package(problem: ProblemMeta, workspace: Path, out_zip: Path, solution_path: Path | None = None) -> Path:
    root_name = problem.pid if problem.pid else "problem"
    root = workspace / root_name
    testdata = root / "testdata"
    root.mkdir(parents=True, exist_ok=True)
    testdata.mkdir(parents=True, exist_ok=True)

    yaml_obj = {"title": problem.title, "tag": problem.tags}
    if problem.pid:
        yaml_obj["pid"] = problem.pid
    (root / "problem.yaml").write_text(yaml.safe_dump(yaml_obj, allow_unicode=True), encoding="utf-8")

    md = (problem.statement_markdown or f"# {problem.title}\n").strip() + "\n"
    (root / "problem_zh.md").write_text(md, encoding="utf-8")

    if solution_path and solution_path.exists():
        shutil.copyfile(solution_path, root / "solution.cpp")

    config = {"type": "default", "time": problem.time_limit.lower().replace(" ", ""), "memory": problem.memory_limit.lower().replace(" ", ""), "checker_type": "default"}
    (testdata / "config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    for f in workspace.glob("*.in"):
        shutil.copyfile(f, testdata / f.name)
        out = f.with_suffix(".out")
        if out.exists():
            shutil.copyfile(out, testdata / out.name)

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            zf.write(p, p.relative_to(workspace))
    return out_zip
