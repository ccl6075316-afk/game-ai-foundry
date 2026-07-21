"""Tests for mutating FOUNDRY_TOOL permission gate."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from pi_foundry_tools import run_allowed_gamefactory
from tool_permission import (
    PermissionTurnState,
    ensure_i_confirm,
    request_mutate_permission,
    summarize_argv,
)


class ToolPermissionUnitTest(unittest.TestCase):
    def test_summarize_redacts_api_key(self) -> None:
        s = summarize_argv(
            ["setup", "provider", "upsert", "--api-key", "sk-secret", "--json"]
        )
        self.assertIn("--api-key", s)
        self.assertIn("***", s)
        self.assertNotIn("sk-secret", s)

    def test_ensure_i_confirm(self) -> None:
        self.assertEqual(
            ensure_i_confirm(["setup", "install", "ffmpeg"]),
            ["setup", "install", "ffmpeg", "--i-confirm"],
        )
        self.assertEqual(
            ensure_i_confirm(["setup", "install", "ffmpeg", "--i-confirm"]),
            ["setup", "install", "ffmpeg", "--i-confirm"],
        )

    def test_no_bridge_defaults_to_once(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("GAMEFACTORY_TOOL_PERMISSION_URL", None)
            d = request_mutate_permission(["setup", "install", "ffmpeg", "--i-confirm"])
        self.assertEqual(d, "once")

    def test_turn_memory_skips_second_ask(self) -> None:
        calls: list[dict] = []

        def requester(payload: dict) -> str:
            calls.append(payload)
            return "turn"

        state = PermissionTurnState()
        d1 = request_mutate_permission(
            ["setup", "install", "ffmpeg", "--i-confirm"],
            session_id="s1",
            turn_state=state,
            requester=requester,
        )
        d2 = request_mutate_permission(
            ["pipeline", "reset", "--task-id", "t1", "--i-confirm"],
            session_id="s1",
            turn_state=state,
            requester=requester,
        )
        self.assertEqual(d1, "turn")
        self.assertEqual(d2, "once")
        self.assertEqual(len(calls), 1)

    def test_deny_from_requester(self) -> None:
        d = request_mutate_permission(
            ["setup", "install", "ffmpeg", "--i-confirm"],
            requester=lambda _p: "deny",
        )
        self.assertEqual(d, "deny")


class ToolPermissionGateIntegrationTest(unittest.TestCase):
    def test_mutate_denied_does_not_run(self) -> None:
        with patch(
            "pi_foundry_tools.request_mutate_permission", return_value="deny"
        ), patch("pi_foundry_tools.permission_bridge_configured", return_value=True):
            with patch("pi_foundry_tools.subprocess.run") as run:
                result = run_allowed_gamefactory(
                    ["setup", "install", "ffmpeg", "--json", "--i-confirm"],
                    permission_session_id="chat-1",
                )
        self.assertFalse(result["ok"])
        self.assertIn("denied", (result.get("error") or "").lower())
        run.assert_not_called()

    def test_mutate_with_bridge_asks_even_without_i_confirm_then_injects(
        self,
    ) -> None:
        captured: dict[str, object] = {}

        class FakeProc:
            returncode = 0
            stdout = '{"ok": true}'
            stderr = ""

        def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            captured["cmd"] = cmd
            return FakeProc()

        with (
            patch("pi_foundry_tools.permission_bridge_configured", return_value=True),
            patch("pi_foundry_tools.request_mutate_permission", return_value="once"),
            patch("pi_foundry_tools.subprocess.run", side_effect=fake_run),
            patch("pi_foundry_tools.Path.is_file", return_value=True),
        ):
            result = run_allowed_gamefactory(
                ["setup", "install", "ffmpeg", "--json"],
                permission_session_id="chat-1",
            )
        self.assertTrue(result["ok"])
        cmd = captured["cmd"]
        assert isinstance(cmd, list)
        # stripped for install before CLI
        self.assertNotIn("--i-confirm", cmd)

    def test_readonly_skips_gate(self) -> None:
        with patch("pi_foundry_tools.request_mutate_permission") as gate:
            with patch("pi_foundry_tools.permission_bridge_configured", return_value=True):
                with patch("pi_foundry_tools.subprocess.run") as run:
                    class FakeProc:
                        returncode = 0
                        stdout = "{}"
                        stderr = ""

                    run.return_value = FakeProc()
                    with patch("pi_foundry_tools.Path.is_file", return_value=True):
                        run_allowed_gamefactory(
                            ["doctor", "--json"],
                            permission_session_id="chat-1",
                        )
        gate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
