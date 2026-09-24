"""Tests for LLM config host fallback."""

from __future__ import annotations

import unittest

from llm_config import (
    migrate_retired_llm_models,
    normalize_llm_model,
    resolve_code_api_settings,
    resolve_host_api_settings,
    resolve_prompt_api_settings,
)


class LlmConfigTests(unittest.TestCase):
    def test_normalize_llm_model_maps_retired_deepseek_ids(self) -> None:
        self.assertEqual(normalize_llm_model("deepseek-chat"), "deepseek-v4-flash")
        self.assertEqual(
            normalize_llm_model("deepseek/deepseek-chat"),
            "deepseek/deepseek-v4-flash",
        )
        self.assertEqual(normalize_llm_model("deepseek-v4-pro"), "deepseek-v4-pro")

    def test_migrate_retired_llm_models_rewrites_nested_fields(self) -> None:
        config = {
            "host": {"model": "deepseek-chat"},
            "provider_accounts": {"deepseek": {"text_model": "deepseek/deepseek-chat"}},
        }
        notes = migrate_retired_llm_models(config)
        self.assertEqual(config["host"]["model"], "deepseek-v4-flash")
        self.assertEqual(
            config["provider_accounts"]["deepseek"]["text_model"],
            "deepseek/deepseek-v4-flash",
        )
        self.assertEqual(len(notes), 2)

    def test_prompt_follows_host_when_configured(self) -> None:
        config = {
            "host": {
                "api_key": "host-key",
                "api_base": "https://host.example/v1",
                "model": "host-model",
            },
            "prompt": {"model": "stale-prompt-model"},
        }
        resolved = resolve_prompt_api_settings(config)
        self.assertEqual(resolved["api_key"], "host-key")
        self.assertEqual(resolved["api_base"], "https://host.example/v1")
        self.assertEqual(resolved["prompt_model"], "host-model")
        self.assertEqual(resolved["source"], "host")

    def test_prompt_ignores_stale_prompt_when_host_set(self) -> None:
        config = {
            "host": {
                "api_key": "host-key",
                "api_base": "https://host.example/v1",
                "model": "host-model",
            },
            "prompt": {
                "api_key": "prompt-key",
                "api_base": "https://midjourney-like.example/v1",
                "model": "m",
            },
        }
        resolved = resolve_prompt_api_settings(config)
        self.assertEqual(resolved["api_key"], "host-key")
        self.assertEqual(resolved["api_base"], "https://host.example/v1")
        self.assertEqual(resolved["prompt_model"], "host-model")
        self.assertEqual(resolved["source"], "host")

    def test_prompt_legacy_when_host_missing(self) -> None:
        config = {
            "prompt": {
                "api_key": "prompt-key",
                "api_base": "https://prompt.example/v1",
                "model": "m",
            },
        }
        resolved = resolve_prompt_api_settings(config)
        self.assertEqual(resolved["api_key"], "prompt-key")
        self.assertEqual(resolved["api_base"], "https://prompt.example/v1")
        self.assertEqual(resolved["prompt_model"], "m")
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

    def test_host_falls_back_to_prompt_model(self) -> None:
        config = {
            "prompt": {"model": "deepseek/deepseek-v4-flash", "api_key": "p-key"},
            "image": {"api_key": "img-key", "api_base": "https://openrouter.ai/api/v1"},
        }
        resolved = resolve_host_api_settings(config)
        self.assertEqual(resolved["model"], "deepseek/deepseek-v4-flash")
        self.assertEqual(resolved["api_key"], "p-key")


if __name__ == "__main__":
    unittest.main()
