from __future__ import annotations

import re
import shutil
from pathlib import Path
import zipfile

import yaml

from core.models import ProblemMeta


def _normalize_statement(markdown: str, problem: ProblemMeta) -> str:
    md = markdown.strip() if markdown else ""
    if not md.startswith("#"):
        md = f"# {problem.title}\n\n" + md

    # 始终追加结构化输入输出，避免上游 markdown 字段缺失导致题面看不到对应段落。
    if problem.input_spec.strip():
        md += f"\n\n## 输入格式\n\n{problem.input_spec.strip()}\n"
    if problem.output_spec.strip():
        md += f"\n\n## 输出格式\n\n{problem.output_spec.strip()}\n"
    return md.strip() + "\n"


def _append_samples(markdown: str, problem: ProblemMeta) -> str:
    if not problem.samples:
        return markdown
    parts = [markdown.strip()]
    for i, sample in enumerate(problem.samples, 1):
        parts.append(f"\n\n## 输入输出样例 #{i}\n")
        parts.append(f"### 输入 #{i}\n")
        parts.append(f"```\n{sample.input_data.rstrip()}\n```\n")
        parts.append(f"### 输出 #{i}\n")
        parts.append(f"```\n{sample.output_data.rstrip()}\n```\n")
    return "\n".join(parts).strip() + "\n"


def _keep_image_hyperlinks(markdown: str) -> str:
    # 将 markdown 图片语法转换为普通超链接，避免 additional_file 依赖。
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"[\1](\2)", markdown)


def build_hydro_package(problem: ProblemMeta, workspace: Path, out_zip: Path) -> Path:
    root = workspace / f"{problem.pid}"
    testdata = root / "testdata"
    root.mkdir(parents=True, exist_ok=True)
    testdata.mkdir(parents=True, exist_ok=True)

    (root / "problem.yaml").write_text(
        yaml.safe_dump({"title": problem.title, "tag": problem.tags, "pid": problem.pid}, allow_unicode=True),
        encoding="utf-8",
    )

    base_md = problem.statement_markdown or f"# {problem.title}\n\n## 题目描述\n\n{problem.description}\n"
    md = _normalize_statement(base_md, problem)
    md = _append_samples(md, problem)
    md = _keep_image_hyperlinks(md)
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
