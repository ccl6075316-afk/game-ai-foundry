"""Tests for Brief Tab host-chat helpers."""

from __future__ import annotations

import copy
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
    _system_prompt,
    build_autofix_user_message,
    deep_merge_brief,
    export_brief,
    list_sessions,
    load_session,
    maybe_compress_session,
    new_session,
    resolve_mode,
    run_autofix,
    run_turn,
    save_session,
    session_path_for_id,
    session_status,
    user_requests_commit_brief,
    user_requests_commit_doc,
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

    def test_user_requests_commit_doc(self) -> None:
        self.assertTrue(user_requests_commit_doc("整理成设计说明"))
        self.assertTrue(user_requests_commit_doc("写成 markdown"))
        self.assertTrue(user_requests_commit_doc("整理成一篇完整设计说明 markdown"))
        self.assertFalse(user_requests_commit_doc("落实成 brief"))
        self.assertEqual(resolve_mode(new_session("d1"), "整理成文档"), "commit_doc")

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

    def test_chat_turn_forces_ready_false_without_draft(self) -> None:
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

    def test_chat_turn_persists_progressive_draft(self) -> None:
        session = new_session("chat2")
        session["draft_brief"] = {
            "project": {"title": "Magic Prince", "genre": "2d_platformer"},
            "assets": [{"name": "hero", "type": "character"}],
        }
        llm_payload = {
            "assistant_message": "已把跳跃写进草稿。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "draft_brief": {
                    "project": {
                        "title": "Magic Prince",
                        "genre": "2d_platformer",
                        "controls": {"jump": ["Space"]},
                    },
                    "assets": [
                        {"name": "hero", "type": "character"},
                        {"name": "slime", "type": "character"},
                    ],
                }
            },
            "ready_to_export": True,  # chat must force false
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value=json.dumps(llm_payload)):
            result = run_turn(session, user_message="加个史莱姆和跳跃", config=config)
        self.assertFalse(result["ready_to_export"])
        self.assertFalse(session["ready_to_export"])
        self.assertEqual(session["mode"], "chat")
        draft = session["draft_brief"]
        self.assertEqual(draft["project"]["title"], "Magic Prince")
        self.assertEqual(draft["project"]["controls"]["jump"], ["Space"])
        self.assertEqual(len(draft["assets"]), 2)
        payload = _build_user_payload(session, "chat")
        self.assertIn("current_draft_brief", payload)

    def test_deep_merge_brief_keeps_assets_when_project_patched(self) -> None:
        base = {
            "project": {"title": "A", "genre": "platformer"},
            "assets": [{"name": "hero"}, {"name": "coin"}],
        }
        incoming = {"project": {"title": "A", "controls": {"jump": ["Space"]}}}
        merged = deep_merge_brief(base, incoming)
        assert merged is not None
        self.assertEqual(len(merged["assets"]), 2)
        self.assertEqual(merged["project"]["genre"], "platformer")
        self.assertEqual(merged["project"]["controls"]["jump"], ["Space"])

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
        self.assertIsNone(st.get("draft_brief"))

    def test_status_includes_draft_summary(self) -> None:
        session = new_session("s2")
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
            },
            "assets": [{"name": "hero", "type": "character", "usage": "player_idle"}],
        }
        st = session_status(session)
        self.assertEqual(st["title"], "Demo")
        self.assertEqual(st["genre"], "2d_platformer")
        self.assertEqual(st["asset_count"], 1)
        self.assertEqual(st["assets"][0]["name"], "hero")
        self.assertIsNotNone(st["draft_brief"])
        self.assertFalse(st["ready_to_export"])

    def test_system_prompt_injects_animation_graphs_skill(self) -> None:
        for mode in ("chat", "commit_brief"):
            prompt = _system_prompt(mode)
            self.assertIn("animation_graphs", prompt)
            self.assertIn("禁止", prompt)
            self.assertIn("states", prompt)
            self.assertIn("Godot clip", prompt)
        doc_prompt = _system_prompt("commit_doc")
        self.assertNotIn("禁止（常见幻觉）", doc_prompt)

    def test_autofix_message_includes_gaps_and_clip_hint(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {
                    "name": "hero",
                    "type": "character",
                    "usage": "reference_still",
                    "usage_description": "ref",
                    "description": "h",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                },
                {
                    "name": "hero_walk",
                    "type": "character",
                    "usage": "player_locomotion",
                    "usage_description": "walk",
                    "description": "w",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                    "reference_asset": "hero",
                    "action": "walking",
                    "animation_method": "video",
                },
            ],
            "animation_graphs": [
                {
                    "character_asset": "hero",
                    "default_clip": "idle",
                    "transitions": [{"from": "idle", "to": "跑动"}],
                }
            ],
        }
        msg = build_autofix_user_message(["animation_graphs 'hero': unknown to clip '跑动'"], draft)
        self.assertIn("unknown to clip", msg)
        self.assertIn("states", msg)
        self.assertIn("hero:", msg)
        self.assertIn("idle", msg)
        self.assertIn("资产 → Godot clip", msg)

    def test_autofix_deterministic_clears_clip_mismatch(self) -> None:
        """Clip name typos are code-fixed; LLM must not be required."""
        session = new_session("af0")
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "description": "A simple demo game.",
                "art_direction": "pixel",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
                "session_goal": "Move.",
                "player_asset": "hero",
                "controls": {"move_left": ["A"], "move_right": ["D"]},
                "viewport": {"width": 1280, "height": 720},
                "camera": {"mode": "follow_player"},
            },
            "assets": [
                {
                    "name": "hero",
                    "type": "character",
                    "usage": "reference_still",
                    "usage_description": "ref",
                    "description": "Hero",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                },
                {
                    "name": "hero_walk",
                    "type": "character",
                    "usage": "player_locomotion",
                    "usage_description": "walk",
                    "description": "Walk",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                    "reference_asset": "hero",
                    "action": "walking",
                    "animation_method": "video",
                },
            ],
            "animation_graphs": [
                {
                    "character_asset": "hero",
                    "default_clip": "idle",
                    "states": [{"id": "跑动", "clip": "跑动"}],
                    "transitions": [
                        {"from": "idle", "to": "hero_walk", "bidirectional": True},
                    ],
                }
            ],
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion") as mock_llm:
            result = run_autofix(session, config=config, max_rounds=3)
        mock_llm.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertEqual(result["gaps"], [])
        graph = session["draft_brief"]["animation_graphs"][0]
        self.assertNotIn("states", graph)
        self.assertEqual(graph["transitions"][0]["to"], "walk")

    def test_autofix_loop_clears_gaps(self) -> None:
        """Non-mechanical gaps still go through LLM rounds."""
        session = new_session("af1")
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "description": "A simple demo game.",
                "art_direction": "",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
                "session_goal": "Move.",
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
                },
            ],
        }
        fixed = copy.deepcopy(session["draft_brief"])
        fixed["project"]["art_direction"] = "pixel art"
        fix_payload = {
            "assistant_message": "已补 art_direction。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {"draft_brief": fixed},
            "ready_to_export": False,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(fix_payload, ensure_ascii=False),
        ):
            result = run_autofix(session, config=config, max_rounds=3)
        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "contract_complete")
        self.assertEqual(result["gaps"], [])
        self.assertGreaterEqual(result["rounds_run"], 1)

    def test_status_reaudits_and_clears_stale_gaps(self) -> None:
        """Stale session gaps must not stick after draft is already fixed."""
        session = new_session("s3")
        session["gaps"] = [
            "animation_graphs '球员_普通': unknown to clip '跑动'",
        ]
        # Minimal draft without multi-clip graph requirement — audit should not keep that gap
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "description": "A simple demo game.",
                "art_direction": "pixel",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
                "session_goal": "Move.",
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
        }
        st = session_status(session)
        self.assertFalse(
            any("跑动" in g for g in st["gaps"]),
            f"stale gap leaked: {st['gaps']}",
        )

    def test_chat_turn_persists_draft_document(self) -> None:
        session = new_session("doc1")
        llm_payload = {
            "assistant_message": "我先把讨论写成草稿说明。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "draft_document": {
                    "title": "攻击手感笔记",
                    "format": "markdown",
                    "body": "# 攻击手感\n\n- 轻攻击三段\n",
                }
            },
            "ready_to_export": False,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value=json.dumps(llm_payload)):
            result = run_turn(session, user_message="记一下攻击手感", config=config)
        self.assertFalse(result["ready_to_export"])
        self.assertEqual(session["draft_document"]["title"], "攻击手感笔记")
        self.assertIn("轻攻击", session["draft_document"]["body"])
        st = session_status(session)
        self.assertTrue(st["has_document"])
        self.assertEqual(st["document_title"], "攻击手感笔记")

    def test_commit_doc_keyword_stores_body(self) -> None:
        session = new_session("doc2")
        session["messages"] = [
            {"role": "user", "content": "横版跳跃，三段斩"},
            {"role": "assistant", "content": "好的。"},
        ]
        commit_payload = {
            "assistant_message": "设计说明已整理。",
            "choices": ["保存"],
            "mode": "commit_doc",
            "intent_hint": "none",
            "artifact": {
                "kind": "document",
                "title": "横版设计说明",
                "format": "markdown",
                "body": "# 横版设计说明\n\n三段斩。\n",
            },
            "ready_to_export": True,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(commit_payload, ensure_ascii=False),
        ) as mock_llm:
            result = run_turn(session, user_message="整理成设计说明", config=config)
        msgs = mock_llm.call_args.kwargs["messages"]
        self.assertIn("Commit Doc", msgs[0]["content"])
        self.assertTrue(result["ready_to_export"])
        self.assertIn("三段斩", session["draft_document"]["body"])


if __name__ == "__main__":
    unittest.main()
