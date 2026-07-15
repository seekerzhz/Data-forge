from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

load_dotenv()


@dataclass
class LLMConfig:
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "deepseek"))
    model: str | None = None
    temperature: float = 0.1
    max_tokens: int | None = None


DEEPSEEK_REASONING_ALIAS = "deepseek-reasoning"
DEEPSEEK_DEFAULT_REASONING_MODEL = "deepseek-v4-pro"


class LLMClient:
    """Small adapter around OpenAI-compatible chat-completion providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.provider
        self.client = self._build_client(config.provider)
        self.model = self._normalize_model(config.model or self._default_model(config.provider))
        self.max_retries = max(1, int(os.getenv("LLM_MAX_RETRIES", "3")))
        self.retry_base_s = float(os.getenv("LLM_RETRY_BASE_SECONDS", "1.0"))

    @staticmethod
    def _default_model(provider: str) -> str:
        if provider == "deepseek":
            return os.getenv("DEEPSEEK_MODEL", DEEPSEEK_DEFAULT_REASONING_MODEL)
        if provider == "ark":
            return os.getenv("ARK_MODEL", "doubao-seed-1-6-250615")
        if provider == "openai_compatible":
            return os.getenv("OPENAI_COMPAT_MODEL", "deepseek-chat")
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _normalize_model(self, model: str) -> str:
        if self.provider == "deepseek" and model == DEEPSEEK_REASONING_ALIAS:
            return DEEPSEEK_DEFAULT_REASONING_MODEL
        return model

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

        Retries transient provider errors with exponential backoff.
        """
        request: dict[str, Any] = {
            "model": self._normalize_model(model or self.model),
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        token_budget = max_tokens if max_tokens is not None else self.config.max_tokens
        if token_budget is not None:
            request["max_tokens"] = token_budget

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(**request)
                return response.choices[0].message.content or ""
            except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
                last_error = exc
            except APIStatusError as exc:
                last_error = exc
                if exc.status_code is None or exc.status_code < 500:
                    raise
            if attempt + 1 >= self.max_retries:
                break
            delay = self.retry_base_s * (2**attempt) + random.uniform(0, 0.25)
            time.sleep(delay)

        assert last_error is not None
        raise last_error
