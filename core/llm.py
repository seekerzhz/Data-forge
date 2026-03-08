from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass
class LLMConfig:
    provider: str = "ark"
    model: str | None = None
    temperature: float = 0.1


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = self._build_client(config.provider)
        self.model = config.model or self._default_model(config.provider)

    @staticmethod
    def _default_model(provider: str) -> str:
        if provider == "ark":
            return os.getenv("ARK_MODEL", "doubao-seed-1-6-250615")
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @staticmethod
    def _build_client(provider: str) -> OpenAI:
        if provider == "ark":
            api_key = os.getenv("ARK_API_KEY")
            if not api_key:
                raise ValueError("缺少 ARK_API_KEY，请在 .env 或环境变量中配置")
            return OpenAI(
                api_key=api_key,
                base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("缺少 OPENAI_API_KEY，请在 .env 或环境变量中配置")
        return OpenAI(api_key=api_key)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.config.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
