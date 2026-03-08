from __future__ import annotations

from pathlib import Path

from core.llm import LLMClient
from core.utils import extract_code_block, read_text


class SolutionBuilder:
    def __init__(self, llm: LLMClient, prompt_path: Path):
        self.llm = llm
        self.template = read_text(prompt_path)

    def build(self, problem_statement: str) -> str:
        user_prompt = self.template.replace("{{problem}}", problem_statement)
        answer = self.llm.chat(
            system_prompt=(
                "You are a world-class competitive programmer. "
                "Write concise, high-performance C++17 code in a style close to tourist. "
                "Add brief Chinese comments for key logic only. Output C++ code only."
            ),
            user_prompt=user_prompt,
        )
        return extract_code_block(answer, language="cpp")
