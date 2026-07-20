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
        self.assertFalse(is_allowed_argv(["pipeline", "run", "--jobs", "4"]))
        self.assertFalse(is_allowed_argv(["doctor", "--json", ";", "rm", "-rf", "/"]))

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
        self.assertFalse(is_allowed_argv(argv, allow_export=False))
        self.assertTrue(is_allowed_argv(argv, allow_export=True))

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
        self.assertFalse(is_allowed_argv(argv, allow_export=True))
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
        self.assertFalse(is_allowed_argv(argv2, allow_export=True))

    def test_reject_disallowed_run(self) -> None:
        result = run_allowed_gamefactory(["pipeline", "run", "--jobs", "2"])
        self.assertFalse(result["ok"])
        self.assertIn("whitelist", result.get("error") or "")

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
            )
            self.assertFalse(result["ok"])
            self.assertIn("export blocked", result.get("error") or "")
        finally:
            if path.is_file():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
