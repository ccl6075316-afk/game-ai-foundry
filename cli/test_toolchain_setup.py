"""Tests for startup toolchain check."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from toolchain_setup import check_toolchain


class ToolchainSetupTests(unittest.TestCase):
  def test_check_returns_components(self) -> None:
    report = check_toolchain({})
    self.assertIn("components", report)
    ids = {c["id"] for c in report["components"]}
    self.assertIn("ffmpeg", ids)
    self.assertIn("godot", ids)

  @patch("toolchain_setup.resolve_ffmpeg", return_value=None)
  @patch("toolchain_setup._godot_path_from_config", return_value=None)
  def test_missing_required_lists_ffmpeg_and_godot(self, _godot, _ffmpeg) -> None:
    report = check_toolchain({})
    self.assertIn("ffmpeg", report["missing_required"])
    self.assertIn("godot", report["missing_required"])
    self.assertTrue(report["needs_attention"])


if __name__ == "__main__":
  unittest.main()
