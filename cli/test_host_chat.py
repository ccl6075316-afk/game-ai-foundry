"""Tests for Brief Tab host-chat helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from host_chat import (
    HostChatError,
    _CHAR_BUDGET,
    _build_user_payload,
    _parse_llm_json,
    export_brief,
    list_sessions,
    load_session,
    maybe_compress_session,
    new_session,
    resolve_mode,
    run_turn,
    save_session,
    session_path_for_id,
    session_status,
    user_requests_commit_brief,
)


class HostChatTests(unittest.TestCase):
    def test_parse_llm_json_fenced(self) -> None:
        raw = 'Here:\n```json\n{"assistant_message": "hi", "choices": ["A"]}\n```'
        parsed = _parse_llm_json(raw)
        self.assertEqual(parsed["assistant_message"], "hi")

    def test_user_requests_commit_brief(self) -> None:
        self.assertTrue(user_requests_commit_brief("行，落实成 brief 吧"))
        self.assertTrue(user_requests_commit_brief("写成brief"))
        self.assertFalse(user_requests_commit_brief("先聊聊攻击手感"))

    def test_resolve_mode(self) -> None:
        session = new_session("abc")
        self.assertEqual(resolve_mode(session, "聊聊想法"), "chat")
        self.assertEqual(resolve_mode(session, "落实成 brief"), "commit_brief")
        session["pending_mode"] = "commit_brief"
        self.assertEqual(resolve_mode(session, "好"), "commit_brief")

    def test_session_roundtrip(self) -> None:
        session = new_session("sess-demo")
        session["messages"] = [{"role": "user", "content": "hello"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = session_path_for_id("sess-demo", base_dir=Path(tmp))
            save_session(path, session)
            loaded = load_session(path)
        self.assertEqual(loaded["id"], "sess-demo")
        self.assertEqual(loaded["messages"][0]["content"], "hello")

    def test_list_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            s = new_session("one")
            s["messages"] = [{"role": "user", "content": "magic prince"}]
            save_session(session_path_for_id("one", base_dir=base), s)
            items = list_sessions(base_dir=base)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "one")
        self.assertIn("magic", items[0]["title"])

    def test_chat_turn_does_not_store_draft(self) -> None:
        session = new_session("chat1")
        llm_payload = {
            "assistant_message": "可以先聊玩法。",
            "choices": ["横版", "俯视角"],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": True,  # malicious; must be forced false
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value=json.dumps(llm_payload)):
            result = run_turn(session, user_message="我想做个游戏", config=config)
        self.assertFalse(result["ready_to_export"])
        self.assertIsNone(session.get("draft_brief"))
        self.assertEqual(session["mode"], "chat")
        self.assertEqual(len(session["messages"]), 2)

    def test_commit_keyword_uses_commit_skill(self) -> None:
        session = new_session("c1")
        session["messages"] = [
            {"role": "user", "content": "横版魔法王子，能走跳砍"},
            {"role": "assistant", "content": "好的，我们先聊手感。"},
        ]
        commit_payload = {
            "assistant_message": "已按对话落实草案。",
            "choices": ["导出"],
            "mode": "commit_brief",
            "intent_hint": "none",
            "artifact": {
                "kind": "brief",
                "draft_brief": {
                    "project": {
                        "title": "Magic Prince",
                        "description": "2D platformer",
                        "art_direction": "painterly fantasy",
                        "dimension": "2d",
                        "genre": "2d_platformer",
                        "gameplay_loop": "Run jump slash through levels.",
                        "session_goal": "Demo move jump attack.",
                        "player_asset": "hero",
                        "controls": {"move_left": ["A"], "move_right": ["D"], "jump": ["Space"]},
                        "viewport": {"width": 1280, "height": 720},
                        "camera": {"mode": "follow_player"},
                    },
                    "assets": [
                        {
                            "name": "hero",
                            "type": "character",
                            "usage": "player_idle",
                            "usage_description": "Hero idle",
                            "description": "A prince",
                            "display_size": "128x128 px",
                            "generate_method": "image",
                        }
                    ],
                },
            },
            "ready_to_export": True,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(commit_payload, ensure_ascii=False),
        ) as mock_llm:
            result = run_turn(session, user_message="落实成 brief", config=config)
        self.assertTrue(mock_llm.called)
        system = mock_llm.call_args.kwargs.get("messages") or mock_llm.call_args[1].get("messages")
        if system is None:
            system = mock_llm.call_args[0][0] if mock_llm.call_args[0] else mock_llm.call_args.kwargs["messages"]
        # messages kw
        msgs = mock_llm.call_args.kwargs["messages"]
        self.assertIn("Commit Brief", msgs[0]["content"])
        self.assertTrue(result["ready_to_export"])
        self.assertIsNotNone(session.get("draft_brief"))
        self.assertEqual(session["mode"], "commit_brief")

    def test_intent_hint_triggers_followup_commit(self) -> None:
        session = new_session("c2")
        chat_payload = {
            "assistant_message": "好，我按 brief 落实。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "commit_brief",
            "artifact": None,
            "ready_to_export": False,
        }
        commit_payload = {
            "assistant_message": "草案好了。",
            "choices": ["导出"],
            "mode": "commit_brief",
            "intent_hint": "none",
            "artifact": {
                "kind": "brief",
                "draft_brief": {
                    "project": {
                        "title": "Demo",
                        "description": "Demo game",
                        "art_direction": "pixel",
                        "dimension": "2d",
                        "genre": "2d_platformer",
                        "gameplay_loop": "Jump around.",
                        "session_goal": "Move only.",
                        "player_asset": "hero",
                        "controls": {"move_left": ["A"], "move_right": ["D"]},
                        "viewport": {"width": 1280, "height": 720},
                        "camera": {"mode": "follow_player"},
                    },
                    "assets": [
                        {
                            "name": "hero",
                            "type": "character",
                            "usage": "player_idle",
                            "usage_description": "Hero",
                            "description": "Hero",
                            "display_size": "64x64 px",
                            "generate_method": "image",
                        }
                    ],
                },
            },
            "ready_to_export": True,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            side_effect=[
                json.dumps(chat_payload, ensure_ascii=False),
                json.dumps(commit_payload, ensure_ascii=False),
            ],
        ):
            result = run_turn(session, user_message="差不多了，帮我整理成可交付的需求吧", config=config)
        self.assertTrue(result["ready_to_export"])
        # chat ack + commit reply
        self.assertGreaterEqual(len(session["messages"]), 3)

    def test_compress_trims_old_messages(self) -> None:
        session = new_session("long")
        # Build oversized history
        session["messages"] = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": ("x" * 800)}
            for i in range(40)
        ]
        self.assertGreater(
            sum(len(m["content"]) for m in session["messages"]),
            _CHAR_BUDGET,
        )
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value="早期讨论了横版与跳跃手感。"):
            compressed = maybe_compress_session(session, config)
        self.assertTrue(compressed)
        self.assertTrue(session["summary"])
        self.assertLessEqual(len(session["messages"]), 20)
        self.assertGreater(session["compressed_count"], 0)

        payload = _build_user_payload(session, "chat")
        self.assertIn("conversation_summary", payload)

    def test_export_requires_draft(self) -> None:
        session = new_session("e1")
        with self.assertRaises(HostChatError):
            export_brief(session)

    def test_status_chat_session(self) -> None:
        session = new_session("s1")
        session["messages"] = [{"role": "user", "content": "hi"}]
        st = session_status(session)
        self.assertTrue(st["exists"])
        self.assertEqual(st["message_count"], 1)
        self.assertFalse(st["ready_to_export"])


if __name__ == "__main__":
    unittest.main()
