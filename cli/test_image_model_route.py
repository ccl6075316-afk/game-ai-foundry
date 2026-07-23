"""Tests for image model / credential routing (default vs bulk)."""

from __future__ import annotations

import unittest

from image_model_route import (
    effective_generate_tier,
    resolve_image_credentials,
    resolve_image_model_for_tier,
    resolve_image_provider_id,
)
from proxy_utils import config_proxy_value


class ImageModelRouteTests(unittest.TestCase):
    def test_bulk_model_fallback(self) -> None:
        cfg = {"image": {"model": "main-model"}}
        self.assertEqual(resolve_image_model_for_tier(cfg, "bulk"), "main-model")
        cfg2 = {"image": {"model": "main-model", "bulk_model": "cheap-model"}}
        self.assertEqual(resolve_image_model_for_tier(cfg2, "bulk"), "cheap-model")
        self.assertEqual(resolve_image_model_for_tier(cfg2, "default"), "main-model")
        self.assertEqual(
            resolve_image_model_for_tier(cfg2, "bulk", explicit_model="cli-model"),
            "cli-model",
        )

    def test_bulk_provider_fallback(self) -> None:
        cfg = {
            "image": {"provider": "openrouter", "model": "m"},
            "provider_accounts": {
                "openrouter": {"api_key": "sk-or", "api_base": "https://openrouter.ai/api/v1"},
            },
        }
        self.assertEqual(resolve_image_provider_id(cfg, "bulk"), "openrouter")
        creds = resolve_image_credentials(cfg, "bulk")
        self.assertEqual(creds.provider, "openrouter")
        self.assertEqual(creds.api_key, "sk-or")

    def test_bulk_provider_uses_other_account(self) -> None:
        cfg = {
            "image": {
                "provider": "openrouter",
                "bulk_provider": "custom",
                "model": "or-model",
                "bulk_model": "custom-model",
            },
            "provider_accounts": {
                "openrouter": {
                    "api_key": "sk-or",
                    "api_base": "https://openrouter.ai/api/v1",
                },
                "custom": {
                    "api_key": "sk-custom",
                    "api_base": "https://custom.example/v1",
                },
            },
        }
        default = resolve_image_credentials(cfg, "default")
        bulk = resolve_image_credentials(cfg, "bulk")
        self.assertEqual(default.provider, "openrouter")
        self.assertEqual(default.api_key, "sk-or")
        self.assertEqual(default.api_base, "https://openrouter.ai/api/v1")
        self.assertEqual(default.model, "or-model")
        self.assertEqual(bulk.provider, "custom")
        self.assertEqual(bulk.api_key, "sk-custom")
        self.assertEqual(bulk.api_base, "https://custom.example/v1")
        self.assertEqual(bulk.model, "custom-model")

    def test_use_text_provider_for_default_only(self) -> None:
        cfg = {
            "host": {"provider": "deepseek"},
            "image": {
                "provider": "openrouter",
                "use_text_provider": True,
                "bulk_provider": "openrouter",
                "model": "img",
                "bulk_model": "bulk-img",
            },
            "provider_accounts": {
                "deepseek": {
                    "api_key": "sk-ds",
                    "api_base": "https://api.deepseek.com/v1",
                },
                "openrouter": {
                    "api_key": "sk-or",
                    "api_base": "https://openrouter.ai/api/v1",
                },
            },
        }
        default = resolve_image_credentials(cfg, "default")
        bulk = resolve_image_credentials(cfg, "bulk")
        self.assertEqual(default.provider, "deepseek")
        self.assertEqual(default.api_key, "sk-ds")
        self.assertEqual(bulk.provider, "openrouter")
        self.assertEqual(bulk.api_key, "sk-or")

    def test_icon_kit_tier_default(self) -> None:
        self.assertEqual(
            effective_generate_tier(generate_tier=None, for_icon_kit_item=True),
            "bulk",
        )

    def test_top_level_proxy_preferred(self) -> None:
        cfg = {
            "proxy": "http://127.0.0.1:7897",
            "host": {"proxy": "http://legacy:1"},
            "image": {"proxy": "http://legacy:2"},
        }
        self.assertEqual(config_proxy_value(cfg), "http://127.0.0.1:7897")


if __name__ == "__main__":
    unittest.main()
