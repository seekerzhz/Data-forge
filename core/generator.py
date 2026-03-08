from __future__ import annotations

from pathlib import Path

from core.llm import LLMClient
from core.utils import extract_code_block, read_text


class GeneratorBuilder:
    def __init__(self, llm: LLMClient, prompt_path: Path):
        self.llm = llm
        self.template = read_text(prompt_path)

    def build(self, problem_statement: str) -> str:
        user_prompt = self.template.replace("{{problem}}", problem_statement)
        answer = self.llm.chat(
            system_prompt="你是算法竞赛数据构造专家，请只输出 Python 代码。",
            user_prompt=user_prompt,
        )
        return extract_code_block(answer, language="python")
