from __future__ import annotations

import re
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def extract_code_block(text: str, language: str | None = None) -> str:
    """Extract first markdown code block.

    If `language` is provided, prefer matching that language fence.
    """
    if language:
        pattern = rf"```{re.escape(language)}\s*(.*?)```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip() + "\n"

    generic = re.search(r"```(?:[a-zA-Z0-9_+-]*)\s*(.*?)```", text, re.DOTALL)
    if generic:
        return generic.group(1).strip() + "\n"

    return text.strip() + "\n"


def sort_input_files(files: list[Path]) -> list[Path]:
    def key(path: Path):
        stem = path.stem
        return (0, int(stem)) if stem.isdigit() else (1, stem)

    return sorted(files, key=key)
