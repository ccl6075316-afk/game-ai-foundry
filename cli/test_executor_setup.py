"""Tests for executor setup wizard."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from executor_setup import (
    all_executor_status,
    configure_codex_api,
    executor_status,
    resolve_codex_sync_settings,
    resolve_hermes_sync_settings,
    resolve_openrouter_api_key,
    run_executor_step,
)


class ExecutorSetupTests(unittest.TestCase):
    def test_all_executor_status_structure(self) -> None:
        report = all_executor_status()
        self.assertIn("executors", report)
        for eid in ("codex", "hermes", "cursor"):
            self.assertIn(eid, report["executors"])
            info = report["executors"][eid]
            self.assertIn("steps", info)
            self.assertTrue(len(info["steps"]) >= 2)

    def test_resolve_openrouter_from_provider_accounts(self) -> None:
        config = {
            "provider_accounts": {
                "openrouter": {"api_key": "sk-or-test"},
            },
        }
        self.assertEqual(resolve_openrouter_api_key(config), "sk-or-test")

    def test_resolve_hermes_sync_deepseek(self) -> None:
        config = {
            "host": {"provider": "deepseek"},
            "provider_accounts": {
                "deepseek": {
                    "api_key": "sk-ds-test",
                    "api_base": "https://api.deepseek.com/v1",
                    "text_model": "deepseek-chat",
                },
            },
        }
        sync = resolve_hermes_sync_settings(config)
        self.assertEqual(sync["foundry_provider"], "deepseek")
        self.assertEqual(sync["hermes_provider"], "custom")
        self.assertEqual(sync["env_key"], "OPENAI_API_KEY")
        self.assertEqual(sync["api_key"], "sk-ds-test")
        self.assertEqual(sync["api_base"], "https://api.deepseek.com/v1")
        self.assertEqual(sync["model"], "deepseek-chat")

    def test_resolve_hermes_prefers_agents_hermes_provider(self) -> None:
        config = {
            "host": {"provider": "openrouter"},
            "agents": {"hermes_provider": "deepseek"},
            "provider_accounts": {
                "openrouter": {"api_key": "sk-or"},
                "deepseek": {
                    "api_key": "sk-ds",
                    "api_base": "https://api.deepseek.com/v1",
                    "text_model": "deepseek-chat",
                },
            },
        }
        sync = resolve_hermes_sync_settings(config)
        self.assertEqual(sync["foundry_provider"], "deepseek")
        self.assertEqual(sync["api_key"], "sk-ds")

    def test_resolve_hermes_sync_explicit_provider(self) -> None:
        config = {
            "host": {"provider": "openrouter"},
            "provider_accounts": {
                "kimi": {
                    "api_key": "sk-kimi",
                    "api_base": "https://api.moonshot.cn/v1",
                    "text_model": "kimi-k2.5",
                },
            },
        }
        sync = resolve_hermes_sync_settings(config, provider_id="kimi")
        self.assertEqual(sync["foundry_provider"], "kimi")
        self.assertEqual(sync["api_key"], "sk-kimi")

    @patch("executor_setup.shutil.which", return_value=None)
    def test_codex_install_cli_requires_npm(self, _which: object) -> None:
        with self.assertRaises(RuntimeError):
            run_executor_step("codex", "install_cli")

    @patch("executor_setup._codex_logged_in", return_value=True)
    @patch("executor_setup.shutil.which", return_value="/usr/bin/codex")
    def test_codex_login_skips_when_logged_in(self, _which: object, _auth: object) -> None:
        result = run_executor_step("codex", "login")
        self.assertTrue(result.get("already"))

    @patch("executor_setup._spawn_detached")
    @patch("executor_setup._codex_logged_in", return_value=False)
    @patch("executor_setup.shutil.which", return_value="/usr/bin/codex")
    def test_codex_login_starts_detached(
        self,
        _which: object,
        _auth: object,
        spawn: object,
    ) -> None:
        result = run_executor_step("codex", "login")
        spawn.assert_called_once()
        self.assertTrue(result.get("started"))

    @patch("executor_setup._run")
    @patch(
        "executor_setup.resolve_hermes_sync_settings",
        return_value={
            "foundry_provider": "openrouter",
            "hermes_provider": "openrouter",
            "env_key": "OPENROUTER_API_KEY",
            "api_key": "sk-or-x",
            "api_base": "https://openrouter.ai/api/v1",
            "model": "deepseek/deepseek-chat",
        },
    )
    @patch("executor_setup.shutil.which", return_value="/usr/bin/hermes")
    def test_configure_hermes_api(self, _which: object, _sync: object, run: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            with patch("executor_setup._hermes_env_path", return_value=env_path):
                result = run_executor_step("hermes", "configure_api")
            self.assertTrue(result.get("ok"))
            self.assertIn("OPENROUTER_API_KEY=sk-or-x", env_path.read_text())
            self.assertEqual(result.get("foundry_provider"), "openrouter")
            self.assertGreaterEqual(run.call_count, 1)

    @patch("executor_setup._run")
    @patch(
        "executor_setup.resolve_hermes_sync_settings",
        return_value={
            "foundry_provider": "deepseek",
            "hermes_provider": "custom",
            "env_key": "OPENAI_API_KEY",
            "api_key": "sk-ds",
            "api_base": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
        },
    )
    @patch("executor_setup.shutil.which", return_value="/usr/bin/hermes")
    def test_configure_hermes_api_custom_provider(
        self, _which: object, _sync: object, run: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            with patch("executor_setup._hermes_env_path", return_value=env_path):
                result = run_executor_step("hermes", "configure_api")
            self.assertTrue(result.get("ok"))
            self.assertIn("OPENAI_API_KEY=sk-ds", env_path.read_text())
            self.assertEqual(result.get("hermes_provider"), "custom")
            calls = [" ".join(c.args[0]) for c in run.call_args_list]
            self.assertTrue(any("model.provider" in c and "custom" in c for c in calls))
            self.assertTrue(any("model.base_url" in c and "deepseek.com" in c for c in calls))

    @patch("executor_setup.shutil.which", return_value="/usr/bin/cursor")
    def test_cursor_verify_ok(self, _which: object) -> None:
        result = run_executor_step("cursor", "verify_cli")
        self.assertTrue(result.get("ok"))

    def test_executor_status_json_serializable(self) -> None:
        payload = executor_status("hermes")
        json.dumps(payload, ensure_ascii=False)
        self.assertIn("sync_provider", payload)

    def test_resolve_codex_sync_from_executors_preset(self) -> None:
        config = {
            "agents": {
                "godot-developer": {"provider": "openrouter", "use_third_party": False},
                "executors": {
                    "codex": {
                        "provider": "deepseek",
                        "model": "deepseek-chat",
                        "use_third_party": True,
                    }
                },
            },
            "provider_accounts": {
                "deepseek": {"api_key": "sk-deepseek", "text_model": "deepseek-chat"},
            },
        }
        sync = resolve_codex_sync_settings(config)
        self.assertTrue(sync["use_third_party"])
        self.assertEqual(sync["foundry_provider"], "deepseek")
        self.assertEqual(sync["api_key"], "sk-deepseek")

    def test_resolve_codex_sync_from_godot_developer(self) -> None:
        config = {
            "agents": {
                "godot-developer": {
                    "provider": "openrouter",
                    "model": "anthropic/claude-sonnet-4",
                    "use_third_party": True,
                },
            },
            "provider_accounts": {
                "openrouter": {
                    "api_key": "sk-or-codex",
                    "api_base": "https://openrouter.ai/api/v1",
                },
            },
        }
        sync = resolve_codex_sync_settings(config)
        self.assertTrue(sync["use_third_party"])
        self.assertEqual(sync["foundry_provider"], "openrouter")
        self.assertEqual(sync["codex_provider_id"], "foundry_openrouter")
        self.assertEqual(sync["env_key"], "OPENROUTER_API_KEY")
        self.assertEqual(sync["api_key"], "sk-or-codex")
        self.assertEqual(sync["model"], "anthropic/claude-sonnet-4")

    def test_resolve_codex_sync_instance_overlay(self) -> None:
        config = {
            "agents": {
                "godot-developer": {"provider": "openrouter", "use_third_party": False},
                "instances": {
                    "dev-1": {
                        "role_kind": "programmer",
                        "provider": "deepseek",
                        "model": "deepseek-chat",
                        "use_third_party": True,
                    },
                },
            },
            "provider_accounts": {
                "deepseek": {
                    "api_key": "sk-ds",
                    "api_base": "https://api.deepseek.com/v1",
                },
            },
        }
        sync = resolve_codex_sync_settings(config, instance_id="dev-1")
        self.assertTrue(sync["use_third_party"])
        self.assertEqual(sync["foundry_provider"], "deepseek")
        self.assertEqual(sync["api_key"], "sk-ds")

    def test_resolve_codex_sync_use_third_party_false(self) -> None:
        config = {
            "agents": {
                "godot-developer": {
                    "provider": "openrouter",
                    "use_third_party": False,
                },
            },
            "provider_accounts": {"openrouter": {"api_key": "sk-or"}},
        }
        sync = resolve_codex_sync_settings(config)
        self.assertFalse(sync["use_third_party"])

    @patch("executor_setup.resolve_codex_sync_settings")
    def test_configure_codex_api_skipped_when_not_third_party(self, resolve: object) -> None:
        resolve.return_value = {
            "use_third_party": False,
            "foundry_provider": "openrouter",
        }
        result = configure_codex_api()
        self.assertTrue(result["ok"])
        self.assertTrue(result.get("skipped"))

    @patch("executor_setup.shutil.which", return_value="/usr/bin/codex")
    def test_configure_codex_api_writes_config_and_env(self, _which: object) -> None:
        config = {
            "agents": {
                "godot-developer": {
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "use_third_party": True,
                },
            },
            "provider_accounts": {
                "deepseek": {
                    "api_key": "sk-ds-sync",
                    "api_base": "https://api.deepseek.com/v1",
                },
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / ".codex"
            codex_home.mkdir()
            config_path = codex_home / "config.toml"
            config_path.write_text('model = "gpt-5"\nmodel_provider = "openai"\n', encoding="utf-8")
            env_path = codex_home / ".env"
            with patch("executor_setup._codex_home", return_value=codex_home):
                with patch("executor_setup._load_config", return_value=config):
                    result = configure_codex_api()
            self.assertTrue(result["ok"])
            text = config_path.read_text(encoding="utf-8")
            self.assertIn('model = "deepseek-chat"', text)
            self.assertIn('model_provider = "foundry_deepseek"', text)
            self.assertIn("[model_providers.foundry_deepseek]", text)
            self.assertIn("https://api.deepseek.com/v1", text)
            self.assertIn("DEEPSEEK_API_KEY=sk-ds-sync", env_path.read_text(encoding="utf-8"))

    @patch("executor_setup.shutil.which", return_value="/usr/bin/codex")
    def test_configure_codex_api_missing_key(self, _which: object) -> None:
        config = {
            "agents": {
                "godot-developer": {
                    "provider": "openrouter",
                    "use_third_party": True,
                },
            },
            "provider_accounts": {},
        }
        with patch("executor_setup._load_config", return_value=config):
            result = configure_codex_api()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_key")

    def test_codex_executor_status_has_sync_api_step(self) -> None:
        payload = executor_status("codex")
        step_ids = [s["id"] for s in payload["steps"]]
        self.assertIn("sync_api", step_ids)
        self.assertIn("sync_provider", payload)

    @patch("executor_setup._configure_codex_api")
    @patch("executor_setup.shutil.which", return_value="/usr/bin/codex")
    def test_run_executor_step_codex_sync_api(self, _which: object, configure: object) -> None:
        configure.return_value = {"ok": True, "foundry_provider": "openrouter"}
        result = run_executor_step("codex", "sync_api")
        configure.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual(result["step"], "sync_api")


if __name__ == "__main__":
    unittest.main()
