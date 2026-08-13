"""Tests for brief CLI command surface (brief_cmds)."""

from __future__ import annotations

import unittest

import click
from click.testing import CliRunner

from brief_cmds import register_brief_commands


def _brief_cli() -> click.Group:
    @click.group()
    def root() -> None:
        pass

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


if __name__ == "__main__":
    unittest.main()
