"""Tests for provider_models catalog fetch."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from provider_models import (
    build_models_url,
    fetch_provider_models,
    parse_openai_models_payload,
    resolve_api_base,
)


class ProviderModelsHelpersTest(unittest.TestCase):
    def test_build_models_url_strips_trailing_slash(self) -> None:
        self.assertEqual(
            build_models_url("https://api.openai.com/v1/"),
            "https://api.openai.com/v1/models",
        )
        self.assertEqual(
            build_models_url("https://api.openai.com/v1"),
            "https://api.openai.com/v1/models",
        )

    def test_resolve_api_base_prefers_account(self) -> None:
        self.assertEqual(
            resolve_api_base("deepseek", {"api_base": "https://custom.example/v1"}),
            "https://custom.example/v1",
        )
        self.assertEqual(
            resolve_api_base("deepseek", {}),
            "https://api.deepseek.com/v1",
        )

    def test_parse_openai_models_payload(self) -> None:
        payload = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
        models = parse_openai_models_payload(payload)
        self.assertEqual([m["id"] for m in models], ["gpt-4o", "gpt-4o-mini"])
        self.assertEqual(models[0]["label"], "gpt-4o")


class FetchProviderModelsTest(unittest.TestCase):
    def _write_config(self, path: Path, accounts: dict) -> None:
        path.write_text(
            json.dumps({"provider_accounts": accounts}, indent=2),
            encoding="utf-8",
        )

    def test_success_with_models(self) -> None:
        def fake_http(url: str, api_key: str) -> tuple[int, bytes]:
            self.assertEqual(url, "https://api.deepseek.com/v1/models")
            self.assertEqual(api_key, "sk-test")
            body = json.dumps(
                {"data": [{"id": "deepseek-chat"}, {"id": "deepseek-v4-flash"}]}
            ).encode()
            return 200, body

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self._write_config(
                path,
                {"deepseek": {"api_key": "sk-test", "text_model": "m"}},
            )
            res = fetch_provider_models(
                provider="deepseek",
                config_path=path,
                http_get=fake_http,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["provider"], "deepseek")
        self.assertEqual(res["source"], "openai-models")
        self.assertIsNone(res["error"])
        self.assertEqual(
            [m["id"] for m in res["models"]],
            ["deepseek-chat", "deepseek-v4-flash"],
        )
        payload = json.dumps(res)
        self.assertNotIn("sk-test", payload)
        self.assertNotIn("api_key", payload)

    def test_http_401(self) -> None:
        def fake_http(_url: str, _api_key: str) -> tuple[int, bytes]:
            return 401, b'{"error":"invalid key"}'

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self._write_config(
                path,
                {
                    "custom": {
                        "api_key": "sk-secret",
                        "api_base": "https://api.apilio.ai/v1",
                    }
                },
            )
            res = fetch_provider_models(
                provider="custom",
                config_path=path,
                http_get=fake_http,
            )
        self.assertFalse(res["ok"])
        self.assertEqual(res["models"], [])
        self.assertIn("401", res["error"])
        payload = json.dumps(res)
        self.assertNotIn("sk-secret", payload)
        self.assertNotIn("api_key", payload)

    def test_success_empty_models(self) -> None:
        def fake_http(_url: str, _api_key: str) -> tuple[int, bytes]:
            return 200, json.dumps({"data": []}).encode()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self._write_config(
                path,
                {"openai": {"api_key": "sk-o"}},
            )
            res = fetch_provider_models(
                provider="openai",
                config_path=path,
                http_get=fake_http,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["models"], [])


if __name__ == "__main__":
    unittest.main()
