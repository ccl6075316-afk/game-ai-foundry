"""Tests for open provider_accounts list/remove (T1)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from provider_upsert import (
    account_kind,
    is_builtin_provider_id,
    is_valid_provider_slug,
    list_provider_accounts,
    remove_provider_account,
    upsert_provider_account,
)


class ProviderAccountsOpenTests(unittest.TestCase):
    def test_slug_helpers(self) -> None:
        self.assertTrue(is_builtin_provider_id("deepseek"))
        self.assertFalse(is_builtin_provider_id("custom"))
        self.assertFalse(is_builtin_provider_id("apilio"))
        self.assertTrue(is_valid_provider_slug("apilio-backup"))
        self.assertFalse(is_valid_provider_slug("Bad"))
        self.assertFalse(is_valid_provider_slug("a"))
        self.assertEqual(account_kind("deepseek"), "builtin")
        self.assertEqual(account_kind("custom"), "user")
        self.assertEqual(account_kind("custom", {}), "user")
        self.assertEqual(account_kind("apilio"), "user")

    def test_list_includes_kind_and_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "provider_accounts": {
                            "deepseek": {"api_key": "sk-ds", "text_model": "m"},
                            "custom": {
                                "api_key": "sk-c",
                                "api_base": "https://api.apilio.ai/v1",
                                "label": "Apilio",
                            },
                            "apilio-backup": {
                                "kind": "user",
                                "label": "备用",
                                "api_base": "https://api.apilio.ai/v1",
                                "api_key": "sk-b",
                            },
                        }
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            res = list_provider_accounts(config_path=path)
            self.assertTrue(res["ok"])
            by_id = {a["id"]: a for a in res["accounts"]}
            self.assertEqual(by_id["deepseek"]["kind"], "builtin")
            self.assertTrue(by_id["deepseek"]["has_api_key"])
            self.assertEqual(by_id["custom"]["kind"], "user")
            self.assertEqual(by_id["custom"]["label"], "Apilio")
            self.assertEqual(by_id["apilio-backup"]["label"], "备用")
            payload = json.dumps(res)
            self.assertNotIn("sk-ds", payload)
            self.assertNotIn("sk-c", payload)
            self.assertNotIn("sk-b", payload)
            for item in res["accounts"]:
                self.assertNotIn("api_key", item)

    def test_remove_blocked_when_host_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "host": {"provider": "apilio"},
                        "provider_accounts": {
                            "apilio": {
                                "kind": "user",
                                "api_base": "https://api.apilio.ai/v1",
                                "api_key": "sk-a",
                            }
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            res = remove_provider_account(
                provider="apilio",
                i_confirm=True,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("host.provider", res["error"])
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("apilio", data["provider_accounts"])

    def test_remove_blocked_when_image_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "image": {"provider": "apilio", "bulk_provider": "deepseek"},
                        "provider_accounts": {
                            "apilio": {
                                "kind": "user",
                                "api_base": "https://api.apilio.ai/v1",
                                "api_key": "sk-a",
                            },
                            "deepseek": {"api_key": "sk-d"},
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            res = remove_provider_account(
                provider="apilio",
                i_confirm=True,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("image.provider", res["error"])

            res2 = remove_provider_account(
                provider="deepseek",
                i_confirm=True,
                config_path=path,
            )
            self.assertFalse(res2["ok"])
            self.assertIn("image.bulk_provider", res2["error"])

    def test_remove_succeeds_when_unreferenced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            upsert_provider_account(
                provider="apilio",
                api_key="sk-a",
                api_base="https://api.apilio.ai/v1",
                i_confirm=True,
                set_active_text=False,
                config_path=path,
            )
            res = remove_provider_account(
                provider="apilio",
                i_confirm=True,
                config_path=path,
            )
            self.assertTrue(res["ok"])
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("apilio", data.get("provider_accounts", {}))

    def test_upsert_user_account_persists_image_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            res = upsert_provider_account(
                provider="apilio",
                api_key="sk-a",
                api_base="https://api.apilio.ai/v1",
                image_model="gemini-3.1-flash-image",
                i_confirm=True,
                set_active_text=False,
                config_path=path,
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["image_model"], "gemini-3.1-flash-image")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                data["provider_accounts"]["apilio"]["image_model"],
                "gemini-3.1-flash-image",
            )


if __name__ == "__main__":
    unittest.main()
