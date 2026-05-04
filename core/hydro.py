from __future__ import annotations

import shutil
from pathlib import Path
import zipfile
import yaml

from core.models import ProblemMeta


def build_hydro_package(problem: ProblemMeta, workspace: Path, out_zip: Path) -> Path:
    root = workspace / f"{problem.pid}"
    testdata = root / "testdata"
    root.mkdir(parents=True, exist_ok=True)
    testdata.mkdir(parents=True, exist_ok=True)

    (root / "problem.yaml").write_text(
        yaml.safe_dump({"title": problem.title, "tag": problem.tags, "pid": problem.pid}, allow_unicode=True),
        encoding="utf-8",
    )

    md = f"# {problem.title}\n\n## 题目描述\n{problem.description}\n\n## 输入格式\n{problem.input_spec}\n\n## 输出格式\n{problem.output_spec}\n"
    (root / "problem_zh.md").write_text(md, encoding="utf-8")

    config = {
        "type": "default",
        "time": problem.time_limit.lower().replace(" ", ""),
        "memory": problem.memory_limit.lower().replace(" ", ""),
        "checker_type": "default",
    }
    (testdata / "config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    for f in workspace.glob("*.in"):
        shutil.copyfile(f, testdata / f.name)
        out = f.with_suffix(".out")
        if out.exists():
            shutil.copyfile(out, testdata / out.name)

    for idx, s in enumerate(problem.samples, 1):
        (testdata / f"sample{idx}.in").write_text(s.input_data + "\n", encoding="utf-8")
        (testdata / f"sample{idx}.out").write_text(s.output_data + "\n", encoding="utf-8")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            zf.write(p, p.relative_to(workspace))
    return out_zip
