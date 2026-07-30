"""Tests for Pi CLI --thinking level from agents.instances."""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from pi_runtime import (
    _pi_cli_model_and_thinking,
    normalize_thinking_level,
    resolve_pi_thinking_level,
    run_pi_smoke,
    run_pi_text_completion,
)


class NormalizeThinkingLevelTest(unittest.TestCase):
    def test_defaults_to_off(self) -> None:
        for raw in (None, "", "  ", "unknown", "MAXIMAL", "xhigh"):
            self.assertEqual(normalize_thinking_level(raw), "off", msg=repr(raw))

    def test_accepts_four_levels(self) -> None:
        self.assertEqual(normalize_thinking_level("off"), "off")
        self.assertEqual(normalize_thinking_level("LOW"), "low")
        self.assertEqual(normalize_thinking_level(" medium "), "medium")
        self.assertEqual(normalize_thinking_level("high"), "high")


class ResolvePiThinkingLevelTest(unittest.TestCase):
    def test_no_instance_or_config_off(self) -> None:
        self.assertEqual(resolve_pi_thinking_level(None), "off")
        self.assertEqual(resolve_pi_thinking_level({}), "off")
        self.assertEqual(resolve_pi_thinking_level({"agents": {"instances": {}}}, "missing"), "off")

    def test_from_instance(self) -> None:
        cfg = {
            "agents": {
                "instances": {
                    "it-1": {"thinking_level": "high"},
                }
            }
        }
        self.assertEqual(resolve_pi_thinking_level(cfg, "it-1"), "high")
        self.assertEqual(resolve_pi_thinking_level(cfg, "it-1",), "high")

    def test_illegal_instance_value_off(self) -> None:
        cfg = {"agents": {"instances": {"x": {"thinking_level": "bogus"}}}}
        self.assertEqual(resolve_pi_thinking_level(cfg, "x"), "off")


class PiCliModelAndThinkingTest(unittest.TestCase):
    def test_argv_fragment_after_model(self) -> None:
        cfg = {"agents": {"instances": {"a": {"thinking_level": "medium"}}}}
        self.assertEqual(
            _pi_cli_model_and_thinking("openai/gpt-4o-mini", cfg, "a"),
            ["--model", "openai/gpt-4o-mini", "--thinking", "medium"],
        )


class PiCmdInjectionTest(unittest.TestCase):
    _ready_status = {
        "cli_js": "/fake/cli.js",
        "node": "/fake/node",
        "node_ok": True,
        "runtime_root": "/fake/runtime",
    }

    def test_smoke_cmd_includes_thinking(self) -> None:
        config = {"agents": {"instances": {"smoke-1": {"thinking_level": "low"}}}}
        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            class P:
                returncode = 0
                stdout = "PONG"
                stderr = ""
            return P()

        with (
            patch("pi_runtime.pi_status", return_value=self._ready_status),
            patch(
                "pi_runtime.resolve_pi_api_auth",
                return_value={
                    "provider": "openrouter",
                    "model": "m1",
                    "api_key": "sk-test",
                    "env_key": "OPENROUTER_API_KEY",
                },
            ),
            patch("pi_runtime.resolve_node_launch", return_value=("/fake/node", {})),
            patch("pi_runtime.subprocess.run", side_effect=fake_run),
        ):
            run_pi_smoke(config=config, instance_id="smoke-1")

        cmd = captured["cmd"]
        idx = cmd.index("--model")
        self.assertEqual(cmd[idx : idx + 4], ["--model", "m1", "--thinking", "low"])

    def test_text_completion_cmd_includes_thinking(self) -> None:
        config = {"agents": {"instances": {"brief-1": {"thinking_level": "high"}}}}
        captured: dict = {}
        runtime_root = tempfile.mkdtemp()
        status = {**self._ready_status, "runtime_root": runtime_root}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            class P:
                returncode = 0
                stdout = "hello"
                stderr = ""
            return P()

        with (
            patch("pi_runtime.pi_status", return_value=status),
            patch(
                "pi_runtime.resolve_pi_auth_for_turn",
                return_value={
                    "provider": "openrouter",
                    "model": "m2",
                    "api_key": "sk-test",
                    "env_key": "OPENROUTER_API_KEY",
                },
            ),
            patch("pi_runtime.resolve_node_launch", return_value=("/fake/node", {})),
            patch("pi_runtime.subprocess.run", side_effect=fake_run),
        ):
            run_pi_text_completion(
                system_prompt="sys",
                user_text="user",
                config=config,
                instance_id="brief-1",
            )

        cmd = captured["cmd"]
        idx = cmd.index("--model")
        self.assertEqual(cmd[idx : idx + 4], ["--model", "m2", "--thinking", "high"])


if __name__ == "__main__":
    unittest.main()
