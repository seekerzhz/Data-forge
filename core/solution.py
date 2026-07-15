from __future__ import annotations

import os
from pathlib import Path

from core.llm import LLMClient
from core.utils import extract_code_block, read_text


class SolutionBuilder:
    """Build C++17 standard solutions from problem statements through the LLM."""

    def __init__(self, llm: LLMClient, prompt_path: Path):
        self.llm = llm
        self.template = read_text(prompt_path)

    def build(self, problem_statement: str) -> str:
        """Generate C++17 standard solution source code.

        Args:
            problem_statement: Polished problem statement.

        Returns:
            Extracted C++ source code from the LLM response.
        """
        user_prompt = self.template.replace("{{problem}}", problem_statement)
        kwargs: dict = {
            "system_prompt": (
                "You are a world-class competitive programmer. "
                "Write concise, high-performance C++17 code in a style close to tourist. "
                "Add brief Chinese comments for key logic only. Output C++ code only."
            ),
            "user_prompt": user_prompt,
        }
        if self.llm.provider == "deepseek":
            kwargs["model"] = os.getenv("DEEPSEEK_REASONING_MODEL", "deepseek-v4-pro")
            kwargs["max_tokens"] = int(os.getenv("DEEPSEEK_REASONING_MAX_TOKENS", "8192"))
        return extract_code_block(self.llm.chat(**kwargs), language="cpp")
