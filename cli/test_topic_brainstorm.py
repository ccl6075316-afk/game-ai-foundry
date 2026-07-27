"""Tests for topic multi-persona brainstorm generate + apply."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from host_chat import HostChatError, draft_fingerprint, new_session
from topic_brainstorm import apply_brainstorm_proposals, run_topic_brainstorm


def _draft() -> dict:
    return {
        "project": {
            "title": "钓鱼",
            "genre": "fishing",
            "gameplay_loop": "抛竿等待拉线",
        },
        "assets": [{"name": "hook", "type": "prop"}],
    }


def _persona_json(role: str) -> str:
    return (
        "{"
        f'"title": "{role} plan",'
        f'"bullets": ["point for {role}", "detail {role}"]'
        "}"
    )


class TopicBrainstormTests(unittest.TestCase):
    def test_generate_writes_result_not_draft(self) -> None:
        session = new_session("bs-gen")
        session["draft_brief"] = _draft()
        before_fp = draft_fingerprint(session["draft_brief"])
        config = {"api_key": "k", "model": "m", "api_base": "http://x"}

        with patch(
            "topic_brainstorm.chat_text_completion",
            side_effect=[
                _persona_json("systems"),
                _persona_json("ui_presentation"),
                _persona_json("feel_feedback"),
                _persona_json("devil_advocate"),
            ],
        ):
            with patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={"api_key": "k", "model": "m", "api_base": "http://x", "proxy": None},
            ):
                result = run_topic_brainstorm(session, "张力条怎么呈现", config=config)

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["proposal_count"], 3)
        self.assertEqual(result["mode"], "personas")
        self.assertIn("brainstorm_result", session)
        self.assertEqual(draft_fingerprint(session["draft_brief"]), before_fp)

    def test_multi_model_flag_without_config_stays_personas(self) -> None:
        session = new_session("bs-mm")
        session["draft_brief"] = _draft()
        with patch(
            "topic_brainstorm.chat_text_completion",
            side_effect=[
                _persona_json("systems"),
                _persona_json("ui_presentation"),
                _persona_json("feel_feedback"),
                _persona_json("devil_advocate"),
            ],
        ):
            with patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={"api_key": "k", "model": "m", "api_base": "http://x", "proxy": None},
            ):
                result = run_topic_brainstorm(
                    session,
                    "菜单结构",
                    multi_model=True,
                    config={"api_key": "k"},
                )
        self.assertEqual(result["mode"], "personas")
        self.assertIn("降级", result["assistant_message"])

    def test_apply_updates_draft(self) -> None:
        session = new_session("bs-apply")
        session["draft_brief"] = _draft()
        session["brainstorm_result"] = {
            "topic": "张力",
            "proposals": [
                {
                    "id": "p1",
                    "role": "ui_presentation",
                    "title": "左侧张力条",
                    "bullets": ["HUD 左上"],
                }
            ],
        }
        thickened = {
            "project": {
                "title": "钓鱼",
                "genre": "fishing",
                "gameplay_loop": "抛竿等待拉线",
                "presentation_notes": "拉线屏左侧张力条",
            },
            "assets": [{"name": "hook", "type": "prop"}],
        }
        llm_out = {
            "draft_brief": thickened,
            "asset_proposals": [{"name": "tension_bar", "type": "ui"}],
            "summary": "采用左侧张力条",
        }
        with patch(
            "topic_brainstorm.chat_text_completion",
            return_value=__import__("json").dumps(llm_out, ensure_ascii=False),
        ):
            with patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={"api_key": "k", "model": "m", "api_base": "http://x", "proxy": None},
            ):
                result = apply_brainstorm_proposals(session, ["p1"], config={"api_key": "k"})

        self.assertTrue(result["ok"])
        self.assertFalse(session.get("ready_to_export"))
        self.assertIsNotNone(session.get("draft_brief_backup"))
        self.assertEqual(
            (session["draft_brief"].get("project") or {}).get("presentation_notes"),
            "拉线屏左侧张力条",
        )
        names = [a.get("name") for a in session["draft_brief"].get("assets") or []]
        self.assertIn("tension_bar", names)

    def test_apply_unknown_id_errors(self) -> None:
        session = new_session("bs-bad")
        session["draft_brief"] = _draft()
        session["brainstorm_result"] = {"topic": "x", "proposals": [{"id": "p1", "title": "a", "bullets": []}]}
        with self.assertRaises(HostChatError):
            apply_brainstorm_proposals(session, ["p99"], config={"api_key": "k"})


if __name__ == "__main__":
    unittest.main()
