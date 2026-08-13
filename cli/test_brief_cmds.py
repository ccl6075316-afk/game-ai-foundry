"""Tests for brief CLI command surface (brief_cmds)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import click
from click.testing import CliRunner

from brief_cmds import register_brief_commands


def _brief_cli() -> click.Group:
    @click.group()
    @click.pass_context
    def root(ctx: click.Context) -> None:
        ctx.ensure_object(dict)
        ctx.obj.setdefault("config", {})

    register_brief_commands(root)
    return root


class BriefCmdsSurfaceTests(unittest.TestCase):
    def test_brief_help_has_no_zh_doc(self) -> None:
        runner = CliRunner()
        result = runner.invoke(_brief_cli(), ["brief", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("zh-doc", result.output)

    def test_brief_chat_help_has_no_zh_doc(self) -> None:
        runner = CliRunner()
        result = runner.invoke(_brief_cli(), ["brief", "chat", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("zh-doc", result.output)

    def test_brief_chat_export_help_has_no_skip_zh_doc(self) -> None:
        runner = CliRunner()
        result = runner.invoke(_brief_cli(), ["brief", "chat", "export", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("skip-zh-doc", result.output)
        self.assertNotIn("zh-doc", result.output)

    def test_localize_help_mentions_offline_map(self) -> None:
        runner = CliRunner()
        result = runner.invoke(_brief_cli(), ["brief", "localize", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("offline-map", result.output)

    def test_localize_without_llm_refuses_non_fishing(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            brief_path = Path(td) / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "Space Runner",
                            "genre": "platformer",
                            "description": "A runner.",
                        },
                        "assets": [],
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "brief_localize.make_llm_translator",
                return_value=None,
            ):
                result = runner.invoke(
                    _brief_cli(),
                    [
                        "brief",
                        "localize",
                        "--brief",
                        str(brief_path),
                        "--i-confirm",
                        "--json",
                    ],
                )
            self.assertEqual(result.exit_code, 2, result.output)
            self.assertIn("host LLM", result.output)
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            self.assertEqual(brief["project"]["description"], "A runner.")

    def test_localize_offline_map_flag_allows_fishing_map(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            brief_path = Path(td) / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "Space Runner",
                            "genre": "platformer",
                            "description": "A fishing game.",
                        },
                        "assets": [],
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "brief_localize.make_llm_translator",
                return_value=None,
            ):
                result = runner.invoke(
                    _brief_cli(),
                    [
                        "brief",
                        "localize",
                        "--brief",
                        str(brief_path),
                        "--i-confirm",
                        "--offline-map",
                        "fishing",
                        "--json",
                    ],
                )
            self.assertEqual(result.exit_code, 0, result.output)
            payload = json.loads(result.output)
            self.assertTrue(payload.get("ok"))
            self.assertEqual(payload.get("translator"), "offline_map")
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            self.assertEqual(brief["project"]["description"], "一款钓鱼游戏。")

    def test_localize_fishing_path_allows_offline_without_flag(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "fishing-2d"
            root.mkdir()
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "Coast",
                            "description": "A fishing game.",
                        },
                        "assets": [],
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "brief_localize.make_llm_translator",
                return_value=None,
            ):
                result = runner.invoke(
                    _brief_cli(),
                    [
                        "brief",
                        "localize",
                        "--brief",
                        str(brief_path),
                        "--i-confirm",
                        "--json",
                    ],
                )
            self.assertEqual(result.exit_code, 0, result.output)
            payload = json.loads(result.output)
            self.assertEqual(payload.get("translator"), "offline_map")
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            self.assertEqual(brief["project"]["description"], "一款钓鱼游戏。")


if __name__ == "__main__":
    unittest.main()
