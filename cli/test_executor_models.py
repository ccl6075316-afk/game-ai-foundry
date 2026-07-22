"""Tests for executor_models discovery parsers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from executor_models import (
    list_executor_models,
    parse_codex_debug_models,
    parse_cursor_list_models_text,
)


class ParseCursorModelsTest(unittest.TestCase):
    def test_no_models_message(self) -> None:
        self.assertEqual(
            parse_cursor_list_models_text("Loading models…\nNo models available for this account.\n"),
            [],
        )

    def test_bullet_list(self) -> None:
        text = "Available models:\n- auto\n- opus-4.5\n- composer-2\n"
        ids = [m["id"] for m in parse_cursor_list_models_text(text)]
        self.assertEqual(ids, ["auto", "opus-4.5", "composer-2"])

    def test_json_array(self) -> None:
        models = parse_cursor_list_models_text('[{"id":"auto","label":"Auto"},{"id":"opus-4.5"}]')
        self.assertEqual([m["id"] for m in models], ["auto", "opus-4.5"])


class ParseCodexModelsTest(unittest.TestCase):
    def test_json_models_key(self) -> None:
        raw = '{"models":[{"slug":"gpt-5.3","display_name":"GPT-5.3"},{"id":"gpt-5.5"}]}'
        ids = [m["id"] for m in parse_codex_debug_models(raw)]
        self.assertEqual(ids, ["gpt-5.3", "gpt-5.5"])


class ListExecutorModelsTest(unittest.TestCase):
    def test_cursor_cli_missing(self) -> None:
        with patch("executor_models._which_cursor_agent", return_value=None):
            res = list_executor_models("cursor")
        self.assertFalse(res["ok"])
        self.assertEqual(res["models"], [])
        self.assertIn("未找到", res["hint"] or "")

    def test_cursor_empty_account(self) -> None:
        with (
            patch("executor_models._which_cursor_agent", return_value="/bin/agent"),
            patch(
                "executor_models._run",
                return_value=(0, "No models available for this account.\n", ""),
            ),
        ):
            res = list_executor_models("cursor")
        self.assertTrue(res["ok"])
        self.assertEqual(res["models"], [])
        self.assertIn("无可用模型", res["hint"] or "")
        self.assertIn("CURSOR_API_KEY", res["hint"] or "")

    def test_cursor_ok(self) -> None:
        with (
            patch("executor_models._which_cursor_agent", return_value="/bin/agent"),
            patch(
                "executor_models._run",
                return_value=(0, "- auto\n- opus-4.5\n", ""),
            ),
        ):
            res = list_executor_models("cursor")
        self.assertTrue(res["ok"])
        self.assertEqual([m["id"] for m in res["models"]], ["auto", "opus-4.5"])


if __name__ == "__main__":
    unittest.main()
