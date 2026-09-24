"""Tests for broad deterministic inspect reads."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inspect_ops import (
    InspectError,
    grep_files,
    list_dir,
    read_file,
    redact_secrets,
    resolve_readable_path,
    tree_dir,
)


class RedactTests(unittest.TestCase):
    def test_redacts_api_key_fields(self) -> None:
        out = redact_secrets({"api_key": "sk-secret-value-123456", "model": "x"})
        self.assertEqual(out["api_key"], "***")
        self.assertEqual(out["model"], "x")


class InspectPathTests(unittest.TestCase):
    def test_rejects_outside_roots(self) -> None:
        with self.assertRaises(InspectError):
            resolve_readable_path("/tmp/not-allowed.txt", must_exist=False)

    def test_rejects_node_modules(self) -> None:
        with self.assertRaises(InspectError):
            resolve_readable_path("gui/node_modules/foo", must_exist=False)

    def test_reads_repo_text(self) -> None:
        # AGENTS.md should exist at repo root
        result = read_file("AGENTS.md", max_bytes=2000)
        self.assertTrue(result["ok"])
        self.assertIn("content", result)
        self.assertTrue(result["content"])

    def test_tree_and_grep_cli(self) -> None:
        tree = tree_dir("cli", max_depth=1, limit=50)
        self.assertTrue(tree["ok"])
        self.assertGreater(tree["count"], 3)
        hits = grep_files("cli/inspect_ops.py", "DEFAULT_MAX_BYTES", max_matches=10)
        self.assertTrue(hits["ok"])
        self.assertGreaterEqual(hits["count"], 1)

    def test_grep_skips_denied_trees(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "secret.py").write_text(
                "UNIQUE_GREP_HIT_DENIED = 1\n", encoding="utf-8"
            )
            (root / "src").mkdir()
            (root / "src" / "ok.py").write_text("UNIQUE_GREP_HIT_OK = 1\n", encoding="utf-8")
            with patch("inspect_ops.allow_roots", return_value=[root.resolve()]):
                hits = grep_files(root, "UNIQUE_GREP_HIT")
        paths = [str(m["path"]) for m in hits["matches"]]
        self.assertTrue(any("ok.py" in p for p in paths))
        self.assertFalse(any("secret.py" in p for p in paths))

    def test_grep_rejects_invalid_or_long_pattern(self) -> None:
        with self.assertRaises(InspectError):
            grep_files("cli/inspect_ops.py", "(")
        with self.assertRaises(InspectError):
            grep_files("cli/inspect_ops.py", "a" * 300)

    def test_config_json_redacts_keys(self) -> None:
        cfg = Path.home() / ".gamefactory" / "config.json"
        if not cfg.is_file():
            self.skipTest("no local config")
        result = read_file(str(cfg), max_bytes=500_000)
        self.assertTrue(result["ok"])
        blob = json.dumps(result.get("json") or result.get("content") or "")
        self.assertNotRegex(blob, r"sk-[a-zA-Z0-9_-]{20,}")

if __name__ == "__main__":
    unittest.main()
