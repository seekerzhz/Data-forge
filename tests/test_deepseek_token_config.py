import os
import unittest
from unittest.mock import patch

from core.service import ForgeService


class DeepSeekTokenConfigTests(unittest.TestCase):
    def test_generator_requests_use_configured_deepseek_token_budget(self) -> None:
        with patch.dict(os.environ, {"DEEPSEEK_REASONING_MAX_TOKENS": "16384"}):
            with patch("core.service.LLMClient") as client:
                ForgeService(provider="deepseek")

        self.assertEqual(client.call_args.args[0].max_tokens, 16384)

    def test_deepseek_token_budget_keeps_existing_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("core.service.LLMClient") as client:
                ForgeService(provider="deepseek")

        self.assertEqual(client.call_args.args[0].max_tokens, 8192)


if __name__ == "__main__":
    unittest.main()
