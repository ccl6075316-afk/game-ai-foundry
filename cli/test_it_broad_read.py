"""Tests for IT broad read (inspect + conversations)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conversations_ops import list_sessions, show_session
from inspect_ops import InspectError, list_dir, read_file, redact_secrets, resolve_readable_path
from pi_foundry_tools import is_allowed_argv


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

    def test_config_json_redacts_keys(self) -> None:
        cfg = Path.home() / ".gamefactory" / "config.json"
        if not cfg.is_file():
            self.skipTest("no local config")
        result = read_file(str(cfg), max_bytes=500_000)
        self.assertTrue(result["ok"])
        blob = json.dumps(result.get("json") or result.get("content") or "")
        self.assertNotRegex(blob, r"sk-[a-zA-Z0-9_-]{20,}")


class ConversationsTests(unittest.TestCase):
    def test_list_brief(self) -> None:
        out = list_sessions("brief", limit=5)
        self.assertTrue(out["ok"])
        self.assertEqual(out["role"], "brief")

    def test_show_brief_tail(self) -> None:
        listed = list_sessions("brief", limit=1)
        if not listed["sessions"]:
            self.skipTest("no brief sessions")
        sid = listed["sessions"][0]["id"]
        shown = show_session("brief", sid, tail=5)
        self.assertTrue(shown["ok"])
        self.assertLessEqual(len(shown["messages"]), 5)


class WhitelistTests(unittest.TestCase):
    def test_inspect_and_conversations_allowed(self) -> None:
        self.assertTrue(is_allowed_argv(["inspect", "list", "--path", "plans", "--json"]))
        self.assertTrue(is_allowed_argv(["inspect", "read", "--path", "AGENTS.md", "--json"]))
        self.assertTrue(is_allowed_argv(["conversations", "list", "--role", "brief", "--json"]))
        self.assertTrue(
            is_allowed_argv(
                ["conversations", "show", "--role", "brief", "--session-id", "x", "--tail", "10", "--json"]
            )
        )


if __name__ == "__main__":
    unittest.main()
