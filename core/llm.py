from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass
class LLMConfig:
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "deepseek"))
    model: str | None = None
    temperature: float = 0.1
    max_tokens: int | None = None


class LLMClient:
    """Small adapter around OpenAI-compatible chat-completion providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = self._build_client(config.provider)
        self.model = config.model or self._default_model(config.provider)

    @staticmethod
    def _default_model(provider: str) -> str:
        if provider == "deepseek":
            return os.getenv("DEEPSEEK_MODEL", "deepseek-reasoning")
        if provider == "ark":
            return os.getenv("ARK_MODEL", "doubao-seed-1-6-250615")
        if provider == "openai_compatible":
            return os.getenv("OPENAI_COMPAT_MODEL", "deepseek-chat")
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @staticmethod
    def _build_client(provider: str) -> OpenAI:
        if provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_COMPAT_API_KEY")
            if not api_key:
                raise ValueError("缺少 DEEPSEEK_API_KEY，请在 .env 或环境变量中配置")
            return OpenAI(
                api_key=api_key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            )

        if provider == "ark":
            api_key = os.getenv("ARK_API_KEY")
            if not api_key:
                raise ValueError("缺少 ARK_API_KEY，请在 .env 或环境变量中配置")
            return OpenAI(
                api_key=api_key,
                base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
            )

        if provider == "openai_compatible":
            api_key = os.getenv("OPENAI_COMPAT_API_KEY")
            if not api_key:
                raise ValueError("缺少 OPENAI_COMPAT_API_KEY，请在 .env 或环境变量中配置")
            base_url = os.getenv("OPENAI_COMPAT_BASE_URL")
            if not base_url:
                raise ValueError("缺少 OPENAI_COMPAT_BASE_URL，请在 .env 或环境变量中配置")
            return OpenAI(api_key=api_key, base_url=base_url)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("缺少 OPENAI_API_KEY，请在 .env 或环境变量中配置")
        return OpenAI(api_key=api_key)

    def chat(self, system_prompt: str, user_prompt: str, model: str | None = None, max_tokens: int | None = None) -> str:
        """Send one chat-completion request and return text content.

        Args:
            system_prompt: Instruction message for the model.
            user_prompt: User message payload.
            model: Optional per-request model override.
            max_tokens: Optional per-request output budget override.

        Returns:
            Model text response, or an empty string when the provider returns no content.
        """
        request: dict[str, Any] = {
            "model": model or self.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        token_budget = max_tokens if max_tokens is not None else self.config.max_tokens
        if token_budget is not None:
            request["max_tokens"] = token_budget

        response = self.client.chat.completions.create(**request)
        return response.choices[0].message.content or ""
