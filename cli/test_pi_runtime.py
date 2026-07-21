"""Unit tests for embedded Pi runtime helpers (no network)."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from pi_runtime import (
    node_meets_pi_min,
    parse_node_version,
    pi_status,
    resolve_node_launch,
    resolve_pi_api_auth,
    resolve_pi_auth_for_brief,
    resolve_pi_cli_js,
)


def _auth_config(**overrides: object) -> dict:
    cfg: dict = {
        "provider_accounts": {
            "openrouter": {"api_key": "sk-or-test", "text_model": "openai/gpt-4o-mini"},
            "deepseek": {"api_key": "sk-ds-test", "text_model": "deepseek-chat"},
        },
        "host": {"provider": "deepseek", "api_key": "sk-host", "model": "deepseek-chat"},
        "agents": {
            "brief": {"executor": "pi", "provider": "openrouter", "model": None},
            "it": {"executor": "pi", "provider": "openrouter", "model": None},
            "instances": {},
        },
    }
    cfg.update(overrides)
    return cfg


class PiRuntimeAuthTest(unittest.TestCase):
    def test_role_openrouter_when_both_keys_exist(self) -> None:
        auth = resolve_pi_api_auth(_auth_config())
        self.assertEqual(auth["provider"], "openrouter")
        self.assertEqual(auth["api_key"], "sk-or-test")
        self.assertEqual(auth["env_key"], "OPENROUTER_API_KEY")
        self.assertEqual(auth["source"], "role")

    def test_instance_deepseek_not_openrouter_when_both_keys_exist(self) -> None:
        config = _auth_config()
        config["agents"]["instances"]["brief-1"] = {
            "role_kind": "brief",
            "executor": "pi",
            "provider": "deepseek",
            "model": "deepseek-chat",
        }
        auth = resolve_pi_api_auth(config, role_kind="brief", instance_id="brief-1")
        self.assertEqual(auth["source"], "instance")
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["api_key"], "sk-ds-test")
        self.assertNotEqual(auth["provider"], "openrouter")

    def test_falls_back_to_host_when_no_role_provider(self) -> None:
        auth = resolve_pi_api_auth(
            {
                "provider_accounts": {"deepseek": {"api_key": "sk-ds-test"}},
                "host": {"provider": "deepseek", "api_key": "sk-ds-test"},
                "agents": {"brief": {"executor": "pi"}},
            }
        )
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["api_key"], "sk-ds-test")
        self.assertEqual(auth["source"], "host")

    def test_missing_key(self) -> None:
        auth = resolve_pi_api_auth(
            {
                "provider_accounts": {},
                "host": {},
                "agents": {"brief": {"executor": "pi"}},
            }
        )
        self.assertIsNone(auth["api_key"])
        self.assertTrue(auth.get("error"))

    def test_brief_auth_keeps_role_model_over_host_model(self) -> None:
        config = _auth_config()
        config["host"]["model"] = "deepseek/deepseek-chat"
        auth = resolve_pi_auth_for_brief(config)
        self.assertEqual(auth["source"], "role")
        self.assertEqual(auth["model"], "openai/gpt-4o-mini")


class PiNodeVersionTest(unittest.TestCase):
    def test_parse_and_min(self) -> None:
        self.assertEqual(parse_node_version("v22.19.0"), (22, 19, 0))
        self.assertEqual(parse_node_version("20.18.3"), (20, 18, 3))
        self.assertTrue(node_meets_pi_min((22, 19, 0)))
        self.assertFalse(node_meets_pi_min((20, 18, 3)))
        self.assertFalse(node_meets_pi_min((22, 18, 0)))

    def test_prefers_path_node_over_old_electron(self) -> None:
        def fake_probe(exe: str, extra_env=None):
            if "Electron" in exe or "electron" in exe.lower():
                return (20, 18, 3)
            if exe.endswith("/node22"):
                return (22, 19, 0)
            return (20, 18, 0)

        with (
            patch("pi_runtime._node_candidates") as cand,
            patch("pi_runtime.probe_node_version", side_effect=fake_probe),
        ):
            cand.return_value = [
                ("/usr/local/bin/node22", {}, "PATH"),
                (
                    "/Apps/Electron.app/Contents/MacOS/Electron",
                    {"ELECTRON_RUN_AS_NODE": "1"},
                    "electron",
                ),
            ]
            exe, extra = resolve_node_launch()
        self.assertEqual(exe, "/usr/local/bin/node22")
        self.assertEqual(extra, {})


class PiRuntimeStatusTest(unittest.TestCase):
    def test_status_without_runtime(self) -> None:
        with (
            patch("pi_runtime.resolve_pi_runtime_root", return_value=None),
            patch("pi_runtime.resolve_node_launch", return_value=("/usr/bin/node", {})),
            patch("pi_runtime.probe_node_version", return_value=(22, 19, 0)),
            patch("pi_runtime.resolve_pi_api_auth", return_value={"api_key": "x", "provider": "openrouter"}),
        ):
            report = pi_status(config={})
        self.assertFalse(report["ready"])
        self.assertIn("prepare_embedded_pi", report.get("hint") or "")

    def test_status_hints_when_node_too_old(self) -> None:
        with (
            patch("pi_runtime.resolve_pi_runtime_root", return_value=Path("/tmp/pi")),
            patch(
                "pi_runtime.resolve_pi_cli_js",
                return_value=Path("/tmp/pi/node_modules/@earendil-works/pi-coding-agent/dist/cli.js"),
            ),
            patch("pi_runtime.resolve_node_launch", return_value=("/old/node", {})),
            patch("pi_runtime.probe_node_version", return_value=(20, 18, 3)),
            patch("pi_runtime.load_embed_manifest", return_value=None),
            patch(
                "pi_runtime.resolve_pi_api_auth",
                return_value={"api_key": "x", "provider": "openrouter", "model": "m", "source": "t"},
            ),
        ):
            report = pi_status(config={})
        self.assertFalse(report["ready"])
        self.assertFalse(report["node_ok"])
        self.assertIn("22.19", report.get("hint") or "")

    def test_resolve_cli_none_when_missing_root(self) -> None:
        missing = Path("/nonexistent/pi-runtime-root-xyz")
        self.assertIsNone(resolve_pi_cli_js(missing))


if __name__ == "__main__":
    unittest.main()
