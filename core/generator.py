from __future__ import annotations

from pathlib import Path

from core.llm import LLMClient
from core.utils import extract_code_block, read_text


class GeneratorBuilder:
    """Build Python data generators from problem statements through the LLM."""

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
        """Generate Python source code for a test-data generator.

        Args:
            problem_statement: Polished Markdown problem statement.
            total_cases: Requested total case count.
            small_cases: Target number of small/easy cases.
            special_cases: Target number of edge cases.
            random_cases: Target number of random cases.
            max_cases: Target number of maximum-stress cases.

        Returns:
            Extracted Python code from the LLM response.
        """
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
