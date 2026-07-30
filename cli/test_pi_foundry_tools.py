"""Tests for Pi Foundry tool whitelist."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from pi_foundry_tools import (
    _session_allows_export,
    extract_foundry_tools,
    is_allowed_argv,
    run_allowed_gamefactory,
    strip_foundry_tools,
)


class PiFoundryToolsTest(unittest.TestCase):
    def test_extract_and_strip(self) -> None:
        text = (
            "先查环境\n"
            "<<<FOUNDRY_TOOL\n"
            '["doctor", "--json"]\n'
            "FOUNDRY_TOOL>>>\n"
            "等结果"
        )
        tools = extract_foundry_tools(text)
        self.assertEqual(tools, [["doctor", "--json"]])
        self.assertIn("先查环境", strip_foundry_tools(text))
        self.assertNotIn("FOUNDRY_TOOL", strip_foundry_tools(text))

    def test_allowlist(self) -> None:
        self.assertTrue(is_allowed_argv(["doctor", "--json"]))
        self.assertTrue(is_allowed_argv(["pipeline", "diagnose", "--json"]))
        self.assertTrue(is_allowed_argv(["setup", "executor", "status", "--json"]))
        self.assertTrue(
            is_allowed_argv(
                [
                    "setup",
                    "provider",
                    "upsert",
                    "--provider",
                    "deepseek",
                    "--api-key",
                    "sk-test",
                    "--i-confirm",
                    "--json",
                ]
            )
        )
        self.assertTrue(
            is_allowed_argv(["setup", "install", "ffmpeg", "--json", "--i-confirm"])
        )
        self.assertTrue(
            is_allowed_argv(
                [
                    "setup",
                    "agents",
                    "executors",
                    "upsert",
                    "--executor",
                    "pi",
                    "--provider",
                    "deepseek",
                    "--i-confirm",
                    "--json",
                ]
            )
        )
        self.assertTrue(
            is_allowed_argv(
                [
                    "setup",
                    "agents",
                    "instances",
                    "upsert",
                    "--instance-id",
                    "it-1",
                    "--thinking-level",
                    "medium",
                    "--i-confirm",
                    "--json",
                ]
            )
        )
        self.assertTrue(
            is_allowed_argv(
                ["pipeline", "run", "--jobs", "4", "--json", "--i-confirm"],
                profile="it",
            )
        )
        self.assertTrue(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "zh-doc",
                    "--session-id",
                    "s1",
                    "--brief-rel",
                    "projects/x/brief.json",
                    "--json",
                    "--i-confirm",
                ],
                profile="it",
            )
        )
        self.assertTrue(is_allowed_argv(["project", "external", "list", "--json"]))
        self.assertTrue(is_allowed_argv(["assets", "review", "list", "--json"]))
        self.assertTrue(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "bind",
                    "--session-id",
                    "s1",
                    "--brief-rel",
                    "projects/x/brief.json",
                    "--json",
                    "--i-confirm",
                ],
                profile="it",
            )
        )
        self.assertTrue(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "autofix",
                    "--session-id",
                    "s1",
                    "--json",
                    "--i-confirm",
                ],
                profile="it",
            )
        )
        self.assertTrue(
            is_allowed_argv(
                ["brief", "chat", "makeability", "--session-id", "s1", "--json"],
                profile="it",
            )
        )
        self.assertTrue(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "enrich",
                    "--session-id",
                    "s1",
                    "--json",
                    "--i-confirm",
                ],
                profile="it",
            )
        )
        self.assertTrue(
            is_allowed_argv(
                ["pipeline", "plan", "--brief", "projects/x/brief.json", "--json", "--i-confirm"],
                profile="it",
            )
        )
        self.assertFalse(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "zh-doc",
                    "--session-id",
                    "s1",
                    "--brief-rel",
                    "gui/evil/brief.json",
                    "--json",
                    "--i-confirm",
                ],
                profile="it",
            )
        )
        self.assertFalse(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "export",
                    "--session-id",
                    "s1",
                    "-o",
                    "projects/x/brief.json",
                    "--json",
                ],
                profile="it",
                allow_export=True,
            )
        )
        self.assertFalse(is_allowed_argv(["doctor", "--json", ";", "rm", "-rf", "/"]))
        self.assertFalse(is_allowed_argv(["git", "push", "origin", "main"]))

    def test_mutate_requires_i_confirm(self) -> None:
        self.assertFalse(is_allowed_argv(["setup", "install", "ffmpeg", "--json"]))
        self.assertFalse(is_allowed_argv(["setup", "ensure", "--json"]))
        self.assertFalse(
            is_allowed_argv(
                ["setup", "executor", "step", "hermes", "configure_api", "--json"]
            )
        )
        self.assertFalse(is_allowed_argv(["pipeline", "heal", "--json"]))
        self.assertFalse(
            is_allowed_argv(["pipeline", "reset", "--task-id", "t1", "--json"])
        )
        self.assertFalse(is_allowed_argv(["pipeline", "run", "--jobs", "2", "--json"]))
        self.assertFalse(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "zh-doc",
                    "--session-id",
                    "s1",
                    "--brief-rel",
                    "projects/x/brief.json",
                    "--json",
                ]
            )
        )
        self.assertFalse(
            is_allowed_argv(
                [
                    "brief",
                    "chat",
                    "bind",
                    "--session-id",
                    "s1",
                    "--brief-rel",
                    "projects/x/brief.json",
                    "--json",
                ]
            )
        )
        self.assertFalse(
            is_allowed_argv(
                [
                    "setup",
                    "provider",
                    "upsert",
                    "--provider",
                    "deepseek",
                    "--api-key",
                    "sk",
                    "--json",
                ]
            )
        )

    def test_brief_profile_rejects_it_mutate(self) -> None:
        argv = ["setup", "install", "ffmpeg", "--json", "--i-confirm"]
        self.assertTrue(is_allowed_argv(argv, profile="it"))
        self.assertFalse(is_allowed_argv(argv, profile="brief"))
        self.assertFalse(
            is_allowed_argv(["doctor", "--json"], profile="brief")
        )
        self.assertFalse(
            is_allowed_argv(
                ["pipeline", "run", "--jobs", "2", "--json", "--i-confirm"],
                profile="brief",
            )
        )
        self.assertTrue(
            is_allowed_argv(
                ["brief", "chat", "status", "--session-id", "s1", "--json"],
                profile="brief",
            )
        )

    def test_install_strips_i_confirm_before_cli(self) -> None:
        captured: dict[str, object] = {}

        class FakeProc:
            returncode = 0
            stdout = '{"ok": true}'
            stderr = ""

        def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            captured["cmd"] = cmd
            return FakeProc()

        with patch("pi_foundry_tools.subprocess.run", side_effect=fake_run):
            with patch("pi_foundry_tools.Path.is_file", return_value=True):
                result = run_allowed_gamefactory(
                    ["setup", "install", "ffmpeg", "--json", "--i-confirm"]
                )
        self.assertTrue(result["ok"])
        cmd = captured["cmd"]
        assert isinstance(cmd, list)
        self.assertNotIn("--i-confirm", cmd)
        self.assertIn("install", cmd)
        self.assertIn("ffmpeg", cmd)

    def test_export_gated_without_flag(self) -> None:
        argv = [
            "brief",
            "chat",
            "export",
            "--session-id",
            "s1",
            "-o",
            "projects/demo/brief.json",
            "--json",
        ]
        self.assertFalse(is_allowed_argv(argv, allow_export=False, profile="brief"))
        self.assertTrue(is_allowed_argv(argv, allow_export=True, profile="brief"))
        # IT never exports even if allow_export is mis-set
        self.assertFalse(is_allowed_argv(argv, allow_export=True, profile="it"))

    def test_export_rejects_bad_path(self) -> None:
        argv = [
            "brief",
            "chat",
            "export",
            "--session-id",
            "s1",
            "-o",
            "C:/Windows/brief.json",
            "--json",
        ]
        self.assertFalse(is_allowed_argv(argv, allow_export=True, profile="brief"))
        argv2 = [
            "brief",
            "chat",
            "export",
            "--session-id",
            "s1",
            "-o",
            "cli/evil.json",
            "--json",
        ]
        self.assertFalse(is_allowed_argv(argv2, allow_export=True, profile="brief"))

    def test_reject_disallowed_run(self) -> None:
        result = run_allowed_gamefactory(["git", "status"])
        self.assertFalse(result["ok"])
        self.assertIn("whitelist", result.get("error") or "")
        result2 = run_allowed_gamefactory(["pipeline", "run", "--jobs", "2", "--json"])
        self.assertFalse(result2["ok"])

    def test_session_allows_export_real_gate(self) -> None:
        from host_chat import new_session, save_session, session_path_for_id

        session = new_session("exp-gate-1")
        session["ready_to_export"] = False
        path = session_path_for_id("exp-gate-1")
        save_session(path, session)
        try:
            ok, reason = _session_allows_export("exp-gate-1")
            self.assertFalse(ok)
            self.assertIn("ready_to_export", reason)

            session["ready_to_export"] = True
            save_session(path, session)
            ok2, reason2 = _session_allows_export("exp-gate-1")
            self.assertTrue(ok2)
            self.assertEqual(reason2, "ready_to_export")
        finally:
            if path.is_file():
                path.unlink()

    def test_export_blocked_when_session_not_ready(self) -> None:
        from host_chat import new_session, save_session, session_path_for_id

        session = new_session("exp-block-1")
        session["ready_to_export"] = False
        path = session_path_for_id("exp-block-1")
        save_session(path, session)
        try:
            result = run_allowed_gamefactory(
                [
                    "brief",
                    "chat",
                    "export",
                    "--session-id",
                    "exp-block-1",
                    "-o",
                    "projects/x/brief.json",
                    "--json",
                ],
                allow_export=True,
                profile="brief",
            )
            self.assertFalse(result["ok"])
            self.assertIn("export blocked", result.get("error") or "")
        finally:
            if path.is_file():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
