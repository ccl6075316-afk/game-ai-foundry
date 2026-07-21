"""Tests for per-instance agent auth resolution."""

from __future__ import annotations

import unittest

from agent_auth_resolve import merge_instance_overlay, resolve_agent_auth


def _base_config(**overrides: object) -> dict:
    cfg: dict = {
        "provider_accounts": {
            "openrouter": {"api_key": "sk-or-test", "text_model": "openai/gpt-4o"},
            "deepseek": {
                "api_key": "sk-ds-test",
                "api_base": "https://api.deepseek.com/v1",
                "text_model": "deepseek-chat",
            },
        },
        "host": {
            "provider": "openrouter",
            "api_key": "sk-host-or",
            "model": "deepseek/deepseek-chat",
        },
        "agents": {
            "brief": {"executor": "pi", "provider": "openrouter", "model": None},
            "it": {"executor": "pi", "provider": "openrouter", "model": None},
            "orchestrator": {"executor": "hermes", "provider": "openrouter", "model": None},
            "godot-developer": {
                "executor": "codex",
                "provider": None,
                "model": None,
                "use_third_party": False,
            },
            "instances": {},
        },
    }
    cfg.update(overrides)
    return cfg


class MergeInstanceOverlayTests(unittest.TestCase):
    def test_merge_overlays_instance_fields(self) -> None:
        role = {"executor": "pi", "provider": "openrouter", "model": None}
        inst = {"provider": "deepseek", "model": "deepseek-chat", "role_kind": "it"}
        merged = merge_instance_overlay(role, inst)
        self.assertEqual(merged["executor"], "pi")
        self.assertEqual(merged["provider"], "deepseek")
        self.assertEqual(merged["model"], "deepseek-chat")
        self.assertEqual(merged["role_kind"], "it")

    def test_merge_without_instance_returns_role_copy(self) -> None:
        role = {"executor": "pi", "provider": "openrouter"}
        merged = merge_instance_overlay(role, None)
        self.assertEqual(merged, role)
        self.assertIsNot(merged, role)


class ResolveAgentAuthTests(unittest.TestCase):
    def test_instance_overrides_role(self) -> None:
        config = _base_config()
        config["agents"]["instances"]["ops-1"] = {
            "role_kind": "it",
            "executor": "pi",
            "provider": "deepseek",
            "model": "deepseek-chat",
        }
        auth = resolve_agent_auth(config, role_kind="it", instance_id="ops-1")
        self.assertEqual(auth["source"], "instance")
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["model"], "deepseek-chat")
        self.assertEqual(auth["api_key"], "sk-ds-test")
        self.assertEqual(auth["env_key"], "DEEPSEEK_API_KEY")
        self.assertEqual(auth["executor"], "pi")
        self.assertEqual(auth["instance_id"], "ops-1")
        self.assertIsNone(auth.get("error"))

    def test_role_overrides_host(self) -> None:
        config = _base_config()
        config["agents"]["it"]["provider"] = "deepseek"
        auth = resolve_agent_auth(config, role_kind="it")
        self.assertEqual(auth["source"], "role")
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["api_key"], "sk-ds-test")

    def test_host_fallback_when_no_role_provider(self) -> None:
        config = _base_config()
        config["agents"]["brief"] = {"executor": "pi"}
        auth = resolve_agent_auth(config, role_kind="brief")
        self.assertEqual(auth["source"], "host")
        self.assertEqual(auth["provider"], "openrouter")
        self.assertEqual(auth["api_key"], "sk-or-test")

    def test_no_instances_falls_back_to_role(self) -> None:
        config = _base_config()
        auth = resolve_agent_auth(config, role_kind="brief", instance_id="missing-id")
        self.assertEqual(auth["source"], "role")
        self.assertEqual(auth["provider"], "openrouter")
        self.assertEqual(auth["api_key"], "sk-or-test")

    def test_missing_key_returns_error(self) -> None:
        config = _base_config()
        config["provider_accounts"]["deepseek"] = {"api_key": ""}
        config["agents"]["it"]["provider"] = "deepseek"
        auth = resolve_agent_auth(config, role_kind="it")
        self.assertIsNone(auth["api_key"])
        self.assertIn("error", auth)
        self.assertIn("API Key", auth["error"])

    def test_rejects_your_placeholder_key(self) -> None:
        config = _base_config()
        config["provider_accounts"]["openrouter"]["api_key"] = "YOUR_OPENROUTER_KEY"
        config["host"]["api_key"] = "YOUR_OPENROUTER_KEY"
        auth = resolve_agent_auth(config, role_kind="brief")
        self.assertIsNone(auth["api_key"])
        self.assertIn("error", auth)

    def test_use_third_party_passthrough(self) -> None:
        config = _base_config()
        config["provider_accounts"]["openrouter"] = {"api_key": "sk-or-codex"}
        config["agents"]["instances"]["dev-1"] = {
            "role_kind": "programmer",
            "executor": "codex",
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
            "use_third_party": True,
        }
        auth = resolve_agent_auth(config, role_kind="programmer", instance_id="dev-1")
        self.assertTrue(auth["use_third_party"])
        self.assertEqual(auth["executor"], "codex")
        self.assertEqual(auth["provider"], "openrouter")
        self.assertEqual(auth["api_key"], "sk-or-codex")

    def test_default_model_from_provider(self) -> None:
        config = _base_config()
        config["agents"]["it"]["provider"] = "deepseek"
        config["agents"]["it"]["model"] = None
        config["provider_accounts"]["deepseek"] = {"api_key": "sk-ds"}
        auth = resolve_agent_auth(config, role_kind="it")
        self.assertEqual(auth["model"], "deepseek-chat")

    def test_model_from_account_text_model(self) -> None:
        config = _base_config()
        config["agents"]["brief"]["provider"] = "openrouter"
        config["agents"]["brief"]["model"] = None
        auth = resolve_agent_auth(config, role_kind="brief")
        self.assertEqual(auth["model"], "openai/gpt-4o")

    def test_product_host_maps_to_orchestrator(self) -> None:
        config = _base_config()
        config["agents"]["orchestrator"]["provider"] = "openrouter"
        auth = resolve_agent_auth(config, role_kind="product_host")
        self.assertEqual(auth["source"], "role")
        self.assertEqual(auth["role_kind"], "product_host")

    def test_openai_compatible_provider_uses_openai_env_key(self) -> None:
        config = _base_config()
        config["provider_accounts"]["kimi"] = {
            "api_key": "sk-kimi",
            "api_base": "https://api.moonshot.cn/v1",
            "text_model": "kimi-k2.5",
        }
        config["agents"]["it"]["provider"] = "kimi"
        auth = resolve_agent_auth(config, role_kind="it")
        self.assertEqual(auth["env_key"], "OPENAI_API_KEY")
        self.assertEqual(auth["api_base"], "https://api.moonshot.cn/v1")
        self.assertEqual(auth["model"], "kimi-k2.5")

    def test_host_key_fallback_when_account_missing(self) -> None:
        config = _base_config()
        config["provider_accounts"] = {}
        config["host"] = {
            "provider": "deepseek",
            "api_key": "sk-host-ds",
            "model": "deepseek-chat",
        }
        config["agents"]["it"]["provider"] = "deepseek"
        auth = resolve_agent_auth(config, role_kind="it")
        self.assertEqual(auth["api_key"], "sk-host-ds")
        self.assertEqual(auth["source"], "role")

    def test_instance_provider_overrides_executors_preset(self) -> None:
        config = _base_config()
        config["agents"]["executors"] = {
            "pi": {"provider": "openrouter", "model": "openai/gpt-4o-mini"},
        }
        config["agents"]["brief"]["provider"] = None
        config["agents"]["instances"]["brief-1"] = {
            "role_kind": "brief",
            "executor": "pi",
            "provider": "deepseek",
            "model": "deepseek-chat",
        }
        auth = resolve_agent_auth(config, role_kind="brief", instance_id="brief-1")
        self.assertEqual(auth["source"], "instance")
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["model"], "deepseek-chat")
        self.assertEqual(auth["api_key"], "sk-ds-test")

    def test_no_instance_provider_uses_executors_preset(self) -> None:
        config = _base_config()
        config["agents"]["executors"] = {
            "pi": {"provider": "deepseek", "model": "deepseek-chat"},
        }
        config["agents"]["it"]["provider"] = "openrouter"
        auth = resolve_agent_auth(config, role_kind="it")
        self.assertEqual(auth["source"], "executor_preset")
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["model"], "deepseek-chat")
        self.assertEqual(auth["api_key"], "sk-ds-test")

    def test_no_executors_key_falls_back_to_role_then_host(self) -> None:
        config = _base_config()
        config["agents"]["it"]["provider"] = "deepseek"
        auth = resolve_agent_auth(config, role_kind="it")
        self.assertEqual(auth["source"], "role")
        self.assertEqual(auth["provider"], "deepseek")

        config["agents"]["brief"] = {"executor": "pi"}
        auth = resolve_agent_auth(config, role_kind="brief")
        self.assertEqual(auth["source"], "host")
        self.assertEqual(auth["provider"], "openrouter")

    def test_executors_codex_preset_without_instance(self) -> None:
        config = _base_config()
        config["agents"]["executors"] = {
            "codex": {
                "use_third_party": True,
                "provider": "deepseek",
                "model": "deepseek-chat",
            },
        }
        config["agents"]["godot-developer"]["provider"] = "openrouter"
        auth = resolve_agent_auth(config, role_kind="programmer")
        self.assertEqual(auth["source"], "executor_preset")
        self.assertEqual(auth["provider"], "deepseek")
        self.assertTrue(auth["use_third_party"])
        self.assertEqual(auth["executor"], "codex")

    def test_executors_hermes_preset_for_product_host(self) -> None:
        config = _base_config()
        config["agents"]["executors"] = {
            "hermes": {"provider": "deepseek"},
        }
        config["agents"]["orchestrator"]["provider"] = "openrouter"
        auth = resolve_agent_auth(config, role_kind="product_host")
        self.assertEqual(auth["source"], "executor_preset")
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["executor"], "hermes")


if __name__ == "__main__":
    unittest.main()
