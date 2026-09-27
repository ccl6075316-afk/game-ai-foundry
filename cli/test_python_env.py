"""Tests for repo-local Python resolution helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from python_env import (
    diagnose_python_env,
    is_windows_store_stub,
    venv_python,
)


class PythonEnvTests(unittest.TestCase):
    def test_detects_windows_store_stub(self) -> None:
        stub = Path(r"C:\Users\admin\AppData\Local\Microsoft\WindowsApps\python.exe")
        self.assertTrue(is_windows_store_stub(stub))
        self.assertFalse(is_windows_store_stub(Path(r"C:\Python311\python.exe")))

    def test_diagnose_includes_launcher_paths(self) -> None:
        report = diagnose_python_env()
        self.assertIn("current_python", report)
        self.assertIn("usable_for_cli", report)
        self.assertIn("gamefactory.cmd", report["launcher"]["windows_cmd"])
        self.assertEqual(Path(report["venv_python"]), venv_python())

    def test_store_stub_marked_unusable_even_if_imports_ok(self) -> None:
        with (
            patch("python_env.sys.executable", r"C:\WindowsApps\python.exe"),
            patch(
                "python_env._probe_imports",
                return_value={"ok": True, "modules": {"click": True}, "missing": []},
            ),
        ):
            report = diagnose_python_env()
        self.assertTrue(report["current_is_store_stub"])
        self.assertFalse(report["usable_for_cli"])


if __name__ == "__main__":
    unittest.main()
