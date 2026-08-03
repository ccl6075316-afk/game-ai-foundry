"""Tests for IT shell run."""

from __future__ import annotations

import unittest

from pi_foundry_tools import is_allowed_argv
from shell_ops import ShellError, resolve_cwd, run_shell


class ShellOpsTests(unittest.TestCase):
    def test_echo(self) -> None:
        out = run_shell("echo hello-foundry-shell")
        self.assertTrue(out["ok"])
        self.assertIn("hello-foundry-shell", out["stdout"])

    def test_pipeline_allowed_in_command(self) -> None:
        out = run_shell("echo a | cat")
        self.assertTrue(out["ok"])
        self.assertIn("a", out["stdout"])

    def test_cwd_outside_rejected(self) -> None:
        with self.assertRaises(ShellError):
            resolve_cwd("/tmp")

    def test_redacts_sk(self) -> None:
        out = run_shell("echo sk-abcdefghijklmnopqrstuv")
        self.assertIn("***", out["stdout"])
        self.assertNotIn("sk-abcdefghijklmnop", out["stdout"])


class ShellWhitelistTests(unittest.TestCase):
    def test_requires_i_confirm(self) -> None:
        self.assertFalse(
            is_allowed_argv(["shell", "run", "--command", "echo hi", "--json"])
        )
        self.assertTrue(
            is_allowed_argv(
                ["shell", "run", "--command", "echo hi | head", "--i-confirm", "--json"]
            )
        )

    def test_brief_profile_rejects(self) -> None:
        self.assertFalse(
            is_allowed_argv(
                ["shell", "run", "--command", "echo hi", "--i-confirm", "--json"],
                profile="brief",
            )
        )


if __name__ == "__main__":
    unittest.main()
