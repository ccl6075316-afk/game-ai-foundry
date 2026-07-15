"""Tests for startup toolchain check."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from toolchain_setup import check_toolchain, ensure_components


class ToolchainSetupTests(unittest.TestCase):
  def test_check_returns_components(self) -> None:
    report = check_toolchain({})
    self.assertIn("components", report)
    ids = {c["id"] for c in report["components"]}
    self.assertIn("ffmpeg", ids)
    self.assertIn("godot", ids)

  @patch("toolchain_setup.resolve_ffmpeg", return_value=None)
  @patch("toolchain_setup._godot_path_from_config", return_value=None)
  @patch("toolchain_setup._dotnet_path", return_value=None)
  def test_missing_required_lists_core_tools(self, _dotnet, _godot, _ffmpeg) -> None:
    report = check_toolchain({})
    self.assertIn("ffmpeg", report["missing_required"])
    self.assertIn("godot", report["missing_required"])
    self.assertIn("dotnet", report["missing_required"])
    self.assertTrue(report["needs_attention"])

  @patch("toolchain_setup.install_component")
  @patch("toolchain_setup.check_toolchain", return_value={"components": [{"id": "godot", "action": "auto"}]})
  @patch("toolchain_setup._is_available", side_effect=[False, True, True])
  def test_ensure_installs_missing(self, _avail: object, _check: object, install: object) -> None:
    install.return_value = {"ok": True}
    result = ensure_components(["godot"])
    install.assert_called_once_with("godot", progress=None)
    self.assertIn("godot", result["installed"])


if __name__ == "__main__":
  unittest.main()
