"""Tests for LLM config host fallback."""

from __future__ import annotations

import unittest

from llm_config import resolve_code_api_settings, resolve_host_api_settings, resolve_prompt_api_settings


class LlmConfigTests(unittest.TestCase):
    def test_prompt_falls_back_to_host(self) -> None:
        config = {
            "host": {
                "api_key": "host-key",
                "api_base": "https://host.example/v1",
                "model": "host-model",
            },
            "prompt": {"model": "prompt-model"},
        }
        resolved = resolve_prompt_api_settings(config)
        self.assertEqual(resolved["api_key"], "host-key")
        self.assertEqual(resolved["api_base"], "https://host.example/v1")
        self.assertEqual(resolved["prompt_model"], "prompt-model")
        self.assertEqual(resolved["source"], "host")

    def test_prompt_uses_own_key_when_set(self) -> None:
        config = {
            "host": {"api_key": "host-key", "api_base": "https://host.example/v1"},
            "prompt": {"api_key": "prompt-key", "api_base": "https://prompt.example/v1", "model": "m"},
        }
        resolved = resolve_prompt_api_settings(config)
        self.assertEqual(resolved["api_key"], "prompt-key")
        self.assertEqual(resolved["source"], "prompt")

    def test_code_falls_back_to_host(self) -> None:
        config = {
            "host": {
                "api_key": "host-key",
                "api_base": "https://host.example/v1",
                "model": "host-model",
            },
            "code": {"model": "code-model"},
        }
        resolved = resolve_code_api_settings(config)
        self.assertEqual(resolved["api_key"], "host-key")
        self.assertEqual(resolved["code_model"], "code-model")
        self.assertEqual(resolved["source"], "host")

    def test_host_falls_back_to_image_legacy(self) -> None:
        config = {
            "image": {
                "api_key": "img-key",
                "api_base": "https://openrouter.ai/api/v1",
            }
        }
        resolved = resolve_host_api_settings(config)
        self.assertEqual(resolved["api_key"], "img-key")
        self.assertEqual(resolved["source"], "host")


if __name__ == "__main__":
    unittest.main()
