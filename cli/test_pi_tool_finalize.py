"""Tests for IT Pi tool-only turn finalization (no leftover FOUNDRY_TOOL)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pi_runtime import _finalize_tool_only_message, run_pi_agent_turn


class PiToolFinalizeTests(unittest.TestCase):
    def test_fallback_summarizes_failures(self) -> None:
        msg = _finalize_tool_only_message(
            [
                {
                    "ok": False,
                    "argv": ["pipeline", "diagnose", "--json"],
                    "error": "manifest not found",
                }
            ]
        )
        self.assertNotIn("FOUNDRY_TOOL", msg)
        self.assertIn("pipeline diagnose", msg)
        self.assertIn("fail", msg)

    @patch("pi_foundry_tools.run_tool_round")
    @patch("pi_runtime.run_pi_text_completion")
    def test_tool_only_reply_does_not_leak_fence(
        self, complete: object, run_tools: object
    ) -> None:
        fence = (
            "<<<FOUNDRY_TOOL\n"
            '["pipeline", "status", "--json"]\n'
            "FOUNDRY_TOOL>>>"
        )
        complete.return_value = fence  # type: ignore[attr-defined]
        run_tools.return_value = (  # type: ignore[attr-defined]
            [{"ok": False, "argv": ["pipeline", "status", "--json"], "error": "no"}],
            "",  # strip left empty
        )
        out = run_pi_agent_turn(
            system_prompt="sys",
            user_text="查一下",
            config={},
            max_tool_rounds=0,  # one completion only
            tool_profile="it",
        )
        msg = str(out["assistant_message"])
        self.assertNotIn("<<<FOUNDRY_TOOL", msg)
        self.assertNotIn("FOUNDRY_TOOL>>>", msg)
        self.assertIn("工具已执行完毕", msg)


if __name__ == "__main__":
    unittest.main()
