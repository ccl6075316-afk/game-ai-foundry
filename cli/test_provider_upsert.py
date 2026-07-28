"""Tests for provider_upsert (IT toolbox write path)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from provider_upsert import upsert_provider_account


class ProviderUpsertTests(unittest.TestCase):
    def test_rejects_without_i_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            res = upsert_provider_account(
                provider="deepseek",
                api_key="sk-test-key",
                i_confirm=False,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("i-confirm", res["error"])
            self.assertFalse(path.exists())

    def test_rejects_invalid_slug_without_api_base(self) -> None:
        res = upsert_provider_account(
            provider="1invalid",
            api_key="sk-test",
            i_confirm=True,
        )
        self.assertFalse(res["ok"])
        self.assertIn("非法", res["error"])

    def test_rejects_user_slug_without_api_base(self) -> None:
        res = upsert_provider_account(
            provider="apilio",
            api_key="sk-test",
            i_confirm=True,
        )
        self.assertFalse(res["ok"])
        self.assertIn("api-base", res["error"])

    def test_accepts_user_slug_with_api_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            res = upsert_provider_account(
                provider="apilio-backup",
                api_key="sk-apilio",
                api_base="https://api.apilio.ai/v1",
                label="Apilio 备用",
                i_confirm=True,
                set_active_text=False,
                config_path=path,
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["kind"], "user")
            self.assertEqual(res["label"], "Apilio 备用")
            self.assertNotIn("sk-apilio", json.dumps(res))
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = data["provider_accounts"]["apilio-backup"]
            self.assertEqual(entry["kind"], "user")
            self.assertEqual(entry["api_base"], "https://api.apilio.ai/v1")
            self.assertEqual(entry["label"], "Apilio 备用")

    def test_rejects_placeholder_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            res = upsert_provider_account(
                provider="deepseek",
                api_key="YOUR_DEEPSEEK_KEY",
                i_confirm=True,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertFalse(res["has_api_key"])

    def test_writes_account_and_sets_active_host(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"host": {"provider": "openrouter"}}, indent=2), encoding="utf-8")
            res = upsert_provider_account(
                provider="deepseek",
                api_key="sk-deepseek-secret",
                text_model="deepseek-v4-flash",
                i_confirm=True,
                set_active_text=True,
                config_path=path,
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["kind"], "builtin")
            self.assertTrue(res["has_api_key"])
            self.assertTrue(res["set_active_text"])
            self.assertNotIn("sk-deepseek", json.dumps(res))
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["provider_accounts"]["deepseek"]["api_key"], "sk-deepseek-secret")
            self.assertEqual(data["host"]["provider"], "deepseek")
            self.assertEqual(data["host"]["api_key"], "sk-deepseek-secret")

    def test_api_key_from_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            with patch.dict("os.environ", {"GAMEFACTORY_PROVIDER_API_KEY": "sk-from-env"}, clear=False):
                res = upsert_provider_account(
                    provider="openrouter",
                    i_confirm=True,
                    set_active_text=False,
                    config_path=path,
                )
            self.assertTrue(res["ok"])
            self.assertFalse(res["set_active_text"])
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["provider_accounts"]["openrouter"]["api_key"], "sk-from-env")
            self.assertNotEqual(data.get("host", {}).get("provider"), "openrouter")

    def test_custom_requires_api_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            res = upsert_provider_account(
                provider="custom",
                api_key="sk-custom",
                i_confirm=True,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("api-base", res["error"])


if __name__ == "__main__":
    unittest.main()
