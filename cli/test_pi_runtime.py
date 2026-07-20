"""Unit tests for embedded Pi runtime helpers (no network)."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from pi_runtime import pi_status, resolve_pi_api_auth, resolve_pi_cli_js


class PiRuntimeAuthTest(unittest.TestCase):
    def test_prefers_openrouter_account(self) -> None:
        auth = resolve_pi_api_auth(
            {
                "provider_accounts": {
                    "openrouter": {"api_key": "sk-or-test"},
                    "deepseek": {"api_key": "sk-ds-test"},
                },
                "host": {"provider": "deepseek", "api_key": "sk-host"},
            }
        )
        self.assertEqual(auth["provider"], "openrouter")
        self.assertEqual(auth["api_key"], "sk-or-test")
        self.assertEqual(auth["env_key"], "OPENROUTER_API_KEY")

    def test_falls_back_to_deepseek(self) -> None:
        auth = resolve_pi_api_auth(
            {
                "provider_accounts": {"deepseek": {"api_key": "sk-ds-test"}},
                "host": {"provider": "deepseek"},
            }
        )
        self.assertEqual(auth["provider"], "deepseek")
        self.assertEqual(auth["api_key"], "sk-ds-test")

    def test_missing_key(self) -> None:
        auth = resolve_pi_api_auth({"provider_accounts": {}, "host": {}})
        self.assertIsNone(auth["api_key"])
        self.assertIn("API Key", auth.get("error") or "")


class PiRuntimeStatusTest(unittest.TestCase):
    def test_status_without_runtime(self) -> None:
        with (
            patch("pi_runtime.resolve_pi_runtime_root", return_value=None),
            patch("pi_runtime.resolve_node_bin", return_value="/usr/bin/node"),
            patch("pi_runtime.resolve_pi_api_auth", return_value={"api_key": "x", "provider": "openrouter"}),
        ):
            report = pi_status(config={})
        self.assertFalse(report["ready"])
        self.assertIn("prepare_embedded_pi", report.get("hint") or "")

    def test_resolve_cli_none_when_missing_root(self) -> None:
        missing = Path("/nonexistent/pi-runtime-root-xyz")
        self.assertIsNone(resolve_pi_cli_js(missing))

if __name__ == "__main__":
    unittest.main()
