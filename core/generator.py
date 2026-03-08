from __future__ import annotations

from pathlib import Path

from core.llm import LLMClient
from core.utils import extract_code_block, read_text


class GeneratorBuilder:
    def __init__(self, llm: LLMClient, prompt_path: Path):
        self.llm = llm
        self.template = read_text(prompt_path)

    def build(
        self,
        problem_statement: str,
        total_cases: int,
        small_cases: int,
        special_cases: int,
        random_cases: int,
        max_cases: int,
    ) -> str:
        user_prompt = (
            self.template.replace("{{problem}}", problem_statement)
            .replace("{{total_cases}}", str(total_cases))
            .replace("{{small_cases}}", str(small_cases))
            .replace("{{special_cases}}", str(special_cases))
            .replace("{{random_cases}}", str(random_cases))
            .replace("{{max_cases}}", str(max_cases))
        )
        answer = self.llm.chat(
            system_prompt="You are an ICPC-level test data engineer. Output Python code only.",
            user_prompt=user_prompt,
        )
        return extract_code_block(answer, language="python")
