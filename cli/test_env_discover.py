"""Tests for environment discovery."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from env_discover import (
    discover_codex,
    discover_cursor,
    discover_executors,
    discover_pipeline,
    run_doctor,
)


class EnvDiscoverTest(unittest.TestCase):
    def test_pipeline_always_available(self) -> None:
        info = discover_pipeline()
        self.assertTrue(info["available"])

    def test_executors_keys(self) -> None:
        ex = discover_executors()
        for name in ("pipeline", "hermes", "codex", "cursor"):
            self.assertIn(name, ex)

    @patch("env_discover.shutil.which", return_value=None)
    def test_codex_missing_without_cli(self, _which: object) -> None:
        info = discover_codex()
        self.assertFalse(info["available"])
        self.assertTrue(info["hints"])

    @patch("env_discover.shutil.which", return_value="/usr/bin/codex")
    def test_codex_available_with_cli(self, _which: object) -> None:
        info = discover_codex()
        self.assertTrue(info["available"])

    @patch("env_discover.shutil.which", return_value=None)
    @patch.dict("os.environ", {}, clear=True)
    def test_cursor_missing_without_cli_or_env(self, _which: object) -> None:
        info = discover_cursor()
        self.assertFalse(info["available"])

    def test_doctor_report_shape(self) -> None:
        report = run_doctor({})
        self.assertIn("executors", report)
        self.assertIn("agents", report)
        self.assertIn("capabilities", report)
        self.assertTrue(report["capabilities"]["pipeline_run"])


if __name__ == "__main__":
    unittest.main()
