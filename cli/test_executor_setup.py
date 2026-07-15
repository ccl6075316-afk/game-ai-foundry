"""Tests for executor setup wizard."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from executor_setup import (
    all_executor_status,
    executor_status,
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
    @patch("executor_setup.resolve_openrouter_api_key", return_value="sk-or-x")
    @patch("executor_setup.shutil.which", return_value="/usr/bin/hermes")
    def test_configure_hermes_api(self, _which: object, _key: object, run: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            with patch("executor_setup._HERMES_ENV", env_path):
                result = run_executor_step("hermes", "configure_api")
            self.assertTrue(result.get("ok"))
            self.assertIn("OPENROUTER_API_KEY=sk-or-x", env_path.read_text())
            self.assertGreaterEqual(run.call_count, 1)

    @patch("executor_setup.shutil.which", return_value="/usr/bin/cursor")
    def test_cursor_verify_ok(self, _which: object) -> None:
        result = run_executor_step("cursor", "verify_cli")
        self.assertTrue(result.get("ok"))

    def test_executor_status_json_serializable(self) -> None:
        payload = executor_status("hermes")
        json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
