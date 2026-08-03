"""Tests for unfinished IT narration detection / nudge behavior."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pi_runtime import looks_like_unfinished_narration, run_pi_agent_turn


class UnfinishedNarrationTests(unittest.TestCase):
    def test_detects_fake_continue(self) -> None:
        text = (
            "main_hub 是空的，manifest 也不存在。"
            "我再确认一下策划里引用了哪张图、以及 visual-target 根目录有哪些文件。"
        )
        self.assertTrue(looks_like_unfinished_narration(text))

    def test_conclusion_not_flagged(self) -> None:
        text = (
            "结论：图片找不到是因为尚未 pipeline plan，"
            "projects/fishing-2d/pipeline/manifest.json 不存在，main_hub 目录为空。"
        )
        self.assertFalse(looks_like_unfinished_narration(text))

    @patch("pi_runtime.run_pi_text_completion")
    @patch("pi_foundry_tools.run_tool_round")
    def test_nudge_then_conclude(self, run_tools: object, complete: object) -> None:
        # 1) prose promises more work but no tool fence → nudge
        # 2) after nudge: final conclusion
        complete.side_effect = [  # type: ignore[attr-defined]
            "我再确认一下策划引用了哪张图。",
            "结论：尚未 pipeline plan，manifest 不存在，所以图片预览找不到。",
        ]
        run_tools.side_effect = [  # type: ignore[attr-defined]
            ([], "我再确认一下策划引用了哪张图。"),
            ([], "结论：尚未 pipeline plan，manifest 不存在，所以图片预览找不到。"),
        ]
        out = run_pi_agent_turn(
            system_prompt="sys",
            user_text="为什么图片找不到",
            config={},
            max_tool_rounds=1,
            tool_profile="it",
        )
        self.assertEqual(out.get("unfinished_nudges"), 1)
        self.assertFalse(out.get("hit_round_limit"))
        self.assertIn("结论", out["assistant_message"])
        self.assertNotIn("本回合已结束", out["assistant_message"])
        self.assertNotIn("工具轮次已用尽", out["assistant_message"])
        self.assertEqual(complete.call_count, 2)  # type: ignore[attr-defined]

    @patch("pi_runtime.run_pi_text_completion")
    @patch("pi_foundry_tools.run_tool_round")
    def test_hit_round_limit_appends_notice(self, run_tools: object, complete: object) -> None:
        # Always return tools so the loop never breaks until budget ends.
        complete.return_value = "还在查"  # type: ignore[attr-defined]
        run_tools.return_value = (  # type: ignore[attr-defined]
            [{"ok": True, "argv": ["doctor", "--json"]}],
            "还在查",
        )
        out = run_pi_agent_turn(
            system_prompt="sys",
            user_text="查环境",
            config={},
            max_tool_rounds=0,  # budget = 1 + 0 + 2 nudges? max_tool_rounds+1+nudges
            # With max_tool_rounds=0 → budget = max(1, 0+1+2) = 3, all continue via tools
            tool_profile="it",
        )
        # Force tighter: max_tool_rounds=0, max_nudges=2 → budget 3, all with results → else branch
        self.assertTrue(out.get("hit_round_limit"))
        self.assertIn("工具轮次已用尽", out["assistant_message"])


if __name__ == "__main__":
    unittest.main()
