from __future__ import annotations

import re
import shutil
from pathlib import Path
import zipfile

import requests
import yaml

from core.models import ProblemMeta


def _append_samples(markdown: str, problem: ProblemMeta) -> str:
    if not problem.samples:
        return markdown
    parts = [markdown.strip(), "\n\n## 样例\n"]
    for i, s in enumerate(problem.samples, 1):
        parts.append(f"### 样例 {i}\n")
        parts.append("#### 输入\n")
        parts.append(f"```text\n{s.input_data.rstrip()}\n```\n")
        parts.append("#### 输出\n")
        parts.append(f"```text\n{s.output_data.rstrip()}\n```\n")
    return "\n".join(parts).strip() + "\n"


def _download_statement_assets(markdown: str, additional_dir: Path) -> str:
    additional_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"

    def save_url(url: str, idx: int) -> str:
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("/"):
            url = "https://www.luogu.com.cn" + url
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            ext = Path(url.split("?")[0]).suffix or ".bin"
            name = f"asset_{idx}{ext}"
            path = additional_dir / name
            path.write_bytes(resp.content)
            return f"file://{name}"
        except Exception:
            return url

    links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    links += re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", markdown)
    replaced = markdown
    for i, old in enumerate(dict.fromkeys(links), 1):
        new = save_url(old, i)
        replaced = replaced.replace(old, new)
    return replaced


def build_hydro_package(problem: ProblemMeta, workspace: Path, out_zip: Path) -> Path:
    root = workspace / f"{problem.pid}"
    testdata = root / "testdata"
    additional = root / "additional_file"
    root.mkdir(parents=True, exist_ok=True)
    testdata.mkdir(parents=True, exist_ok=True)

    (root / "problem.yaml").write_text(
        yaml.safe_dump({"title": problem.title, "tag": problem.tags, "pid": problem.pid}, allow_unicode=True),
        encoding="utf-8",
    )

    md = problem.statement_markdown.strip() or f"# {problem.title}\n\n## 题目描述\n{problem.description}\n\n## 输入格式\n{problem.input_spec}\n\n## 输出格式\n{problem.output_spec}\n"
    if not md.startswith("#"):
        md = f"# {problem.title}\n\n" + md
    md = _append_samples(md, problem)
    md = _download_statement_assets(md, additional)
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
