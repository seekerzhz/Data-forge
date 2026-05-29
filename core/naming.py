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


def build_problem_artifact_name(pid: str, title: str, fallback: str = "problem", max_length: int = _MAX_SLUG_LENGTH) -> str:
    """Build a human-readable safe name for workspace folders and ZIP files.

    Args:
        pid: Sanitized or raw problem id.
        title: Problem title extracted from the statement.
        fallback: Name used when both pid and title are empty after sanitization.
        max_length: Maximum returned name length.

    Returns:
        A stable, filesystem-safe name that prefers the problem title and only prefixes
        the pid when it is not already part of the title.
    """
    safe_pid = sanitize_pid(pid)
    safe_title = sanitize_slug(title, fallback="", max_length=max_length)

    if safe_pid and safe_title:
        if safe_title.upper() == safe_pid or safe_title.upper().startswith(f"{safe_pid}-"):
            return safe_title[:max_length]
        return f"{safe_pid}-{safe_title}"[:max_length].strip("-._")

    return (safe_title or safe_pid or fallback)[:max_length]
