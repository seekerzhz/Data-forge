from __future__ import annotations

import re

_MAX_SLUG_LENGTH = 80


def sanitize_slug(value: str, fallback: str = "item", max_length: int = _MAX_SLUG_LENGTH) -> str:
    """Return a filesystem-safe slug for user or LLM supplied names.

    Args:
        value: Raw value that may contain whitespace, separators, or unsafe characters.
        fallback: Value used when sanitization removes all characters.
        max_length: Maximum returned slug length.

    Returns:
        A non-empty slug containing only word characters, hyphens, and CJK text.
    """
    normalized = re.sub(r"[\\/]+", "-", value.strip())
    normalized = re.sub(r"[^\w\-\u4e00-\u9fff]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-._")
    return (normalized[:max_length].strip("-._") or fallback)[:max_length]


def sanitize_pid(value: str) -> str:
    """Return a safe problem id suitable for directory and package names.

    Args:
        value: User-provided or parsed problem id.

    Returns:
        A sanitized problem id, or an empty string when no id is present.
    """
    if not value.strip():
        return ""
    return sanitize_slug(value.upper(), fallback="problem", max_length=40)
