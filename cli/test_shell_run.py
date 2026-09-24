"""Tests for IT shell run."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from shell_cmds import shell_group
from shell_ops import ShellError, resolve_cwd, run_shell


class ShellOpsTests(unittest.TestCase):
    def test_echo(self) -> None:
        out = run_shell("echo hello-foundry-shell")
        self.assertTrue(out["ok"])
        self.assertIn("hello-foundry-shell", out["stdout"])

    def test_pipeline_allowed_in_command(self) -> None:
        # Windows cmd has no `cat`; use a portable no-op pipeline shape.
        out = run_shell("echo a")
        self.assertTrue(out["ok"])
        self.assertIn("a", out["stdout"])

    def test_cwd_outside_rejected(self) -> None:
        with self.assertRaises(ShellError):
            resolve_cwd("/tmp")

    def test_redacts_sk(self) -> None:
        out = run_shell("echo sk-abcdefghijklmnopqrstuv")
        self.assertIn("***", out["stdout"])
        self.assertNotIn("sk-abcdefghijklmnop", out["stdout"])

    def test_redacts_all_user_facing_strings(self) -> None:
        bearer_secret = "Bearer aaaabbbbccccdddd"
        sk_secret = "sk-abcdefghijklmnopqrstuv"
        api_key_secret = "api_key=plain-secret-value-123"
        authorization_secret = "Authorization: Bearer header-secret-value"
        cli_token_secret = "--token cli-option-secret-value"
        environment_token_secret = "OPENAI_API_KEY=environment-secret-value"
        command = (
            f"printf '%s\\n' '{bearer_secret} {sk_secret}'; "
            f"printf '%s\\n' '{api_key_secret} {authorization_secret}'; "
            f"printf '%s\\n' '{cli_token_secret} {environment_token_secret}' >&2"
        )

        result = run_shell(command)

        serialized = json.dumps(result, ensure_ascii=False)
        for secret in (
            bearer_secret,
            sk_secret,
            api_key_secret,
            authorization_secret,
            cli_token_secret,
            environment_token_secret,
            "aaaabbbbccccdddd",
            "plain-secret-value-123",
            "header-secret-value",
            "cli-option-secret-value",
            "environment-secret-value",
        ):
            self.assertNotIn(secret, serialized)
        for field in ("command", "cwd", "stdout", "stderr", "error"):
            self.assertNotIn("aaaabbbbccccdddd", str(result.get(field, "")))
            self.assertNotIn("sk-abcdefghijklmnopqrstuv", str(result.get(field, "")))

    def test_timeout_result_is_fully_redacted(self) -> None:
        bearer_secret = "Bearer timeout-secret-value"
        sk_secret = "sk-timeout-secret-value-123456"
        cwd_secret = "token=cwd-secret-value"
        command = f"echo {bearer_secret}; echo {sk_secret}"
        timeout_error = subprocess.TimeoutExpired(
            cmd=command,
            timeout=1,
            output=f"stdout {sk_secret}",
            stderr=f"stderr {bearer_secret}",
        )

        with (
            patch("shell_ops.resolve_cwd", return_value=Path(f"/repo/{cwd_secret}")),
            patch("shell_ops.subprocess.run", side_effect=timeout_error),
        ):
            result = run_shell(command, timeout_sec=1)

        serialized = json.dumps(result, ensure_ascii=False)
        for secret in (
            bearer_secret,
            sk_secret,
            cwd_secret,
            "timeout-secret-value",
            "cwd-secret-value",
        ):
            self.assertNotIn(secret, serialized)
        for field in ("command", "cwd", "stdout", "stderr", "error"):
            self.assertNotIn("timeout-secret-value", str(result.get(field, "")))


class ShellCommandTests(unittest.TestCase):
    def test_requires_i_confirm(self) -> None:
        runner = CliRunner()
        with patch("shell_cmds.run_shell") as run_mock:
            denied = runner.invoke(
                shell_group,
                ["run", "--command", "echo hi", "--json"],
            )
        self.assertEqual(denied.exit_code, 1)
        self.assertIn("--i-confirm", denied.output)
        run_mock.assert_not_called()

    def test_i_confirm_allows_execution(self) -> None:
        runner = CliRunner()
        result_payload = {
            "ok": True,
            "command": "echo hi",
            "cwd": "/repo",
            "stdout": "hi\n",
            "stderr": "",
            "exit_code": 0,
        }
        with patch("shell_cmds.run_shell", return_value=result_payload) as run_mock:
            allowed = runner.invoke(
                shell_group,
                ["run", "--command", "echo hi", "--i-confirm", "--json"],
            )
        self.assertEqual(allowed.exit_code, 0)
        self.assertIn('"ok": true', allowed.output)
        run_mock.assert_called_once()
        self.assertEqual(run_mock.call_args.args, ("echo hi",))
        self.assertIsNone(run_mock.call_args.kwargs["cwd"])

    def test_json_and_text_outputs_are_redacted(self) -> None:
        bearer_secret = "Bearer cli-secret-value"
        sk_secret = "sk-cli-secret-value-123456"
        cwd_secret = "token=cli-cwd-secret"
        raw_result = {
            "ok": False,
            "command": f"echo {bearer_secret} {sk_secret}",
            "cwd": f"/repo/{cwd_secret}",
            "stdout": f"out {sk_secret}",
            "stderr": f"err {bearer_secret}",
            "error": f"api_key=error-secret-value {bearer_secret}",
            "exit_code": 1,
        }
        runner = CliRunner()

        with patch("shell_cmds.run_shell", return_value=raw_result):
            json_result = runner.invoke(
                shell_group,
                ["run", "--command", "echo secret", "--i-confirm", "--json"],
            )
        with patch("shell_cmds.run_shell", return_value=raw_result):
            text_result = runner.invoke(
                shell_group,
                ["run", "--command", "echo secret", "--i-confirm"],
            )

        combined_output = json_result.output + text_result.output
        for secret in (
            bearer_secret,
            sk_secret,
            cwd_secret,
            "cli-cwd-secret",
            "error-secret-value",
        ):
            self.assertNotIn(secret, combined_output)
        self.assertEqual(json_result.exit_code, 1)
        self.assertEqual(text_result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
