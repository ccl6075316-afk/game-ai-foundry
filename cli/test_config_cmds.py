"""Tests for allowlisted config set."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config_cmds import apply_config_set


class ConfigSetTests(unittest.TestCase):
    def test_set_size_multiple(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            result = apply_config_set(
                "image.constraints.size_multiple",
                "16",
                path=path,
            )
            self.assertEqual(result["after"], 16)
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("size_multiple", text)

    def test_reject_unknown_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            with self.assertRaises(ValueError):
                apply_config_set("text.api_key", "sk-secret", path=path)


if __name__ == "__main__":
    unittest.main()
