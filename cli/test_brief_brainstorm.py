"""Tests for brief brainstorm session helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brief_brainstorm import (
    BriefBrainstormError,
    _merge_draft,
    _parse_llm_json,
    export_brief,
    load_session,
    new_session,
    run_turn,
    save_session,
    validate_brief_dict,
)


class BriefBrainstormTests(unittest.TestCase):
    def test_parse_llm_json_fenced(self) -> None:
        raw = 'Here:\n```json\n{"assistant_message": "hi", "choices": ["A"]}\n```'
        parsed = _parse_llm_json(raw)
        self.assertEqual(parsed["assistant_message"], "hi")
        self.assertEqual(parsed["choices"], ["A"])

    def test_merge_draft_assets_by_name(self) -> None:
        existing = {
            "project": {"title": "T"},
            "assets": [{"name": "hero", "type": "character", "description": "old"}],
        }
        incoming = {
            "project": {"art_direction": "pixel"},
            "assets": [{"name": "hero", "description": "new desc"}],
        }
        merged = _merge_draft(existing, incoming)
        self.assertEqual(merged["project"]["title"], "T")
        self.assertEqual(merged["project"]["art_direction"], "pixel")
        self.assertEqual(merged["assets"][0]["description"], "new desc")
        self.assertEqual(merged["assets"][0]["type"], "character")

    def test_session_roundtrip(self) -> None:
        session = new_session()
        session["messages"] = [{"role": "user", "content": "test"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.json"
            save_session(path, session)
            loaded = load_session(path)
        self.assertEqual(loaded["id"], session["id"])
        self.assertEqual(loaded["messages"][0]["content"], "test")

    def test_validate_brief_requires_assets(self) -> None:
        with self.assertRaises(BriefBrainstormError):
            validate_brief_dict({"project": {"title": "X"}, "assets": []})

    def test_run_turn_mock_llm(self) -> None:
        session = new_session()
        llm_payload = {
            "assistant_message": "你想做什么视角的游戏？",
            "choices": ["俯视角", "横版"],
            "draft_brief": {
                "project": {
                    "title": "Demo",
                    "description": "2D platformer demo",
                    "art_direction": "flat pixel art",
                    "dimension": "2d",
                    "genre": "2d_platformer",
                    "gameplay_loop": "Run and jump through a demo level.",
                    "session_goal": "Demo: move and jump only.",
                    "player_asset": "hero",
                    "controls": {
                        "move_left": ["A"],
                        "move_right": ["D"],
                    },
                    "viewport": {"width": 1280, "height": 720},
                    "camera": {"mode": "follow_player"},
                },
                "assets": [
                    {
                        "name": "hero",
                        "type": "character",
                        "usage": "player_idle",
                        "usage_description": "Main hero",
                        "description": "A hero",
                        "display_size": "128x128 px",
                        "animation_method": "video",
                    }
                ],
            },
            "ready_to_export": True,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "brief_brainstorm.chat_text_completion",
            return_value=json.dumps(llm_payload, ensure_ascii=False),
        ):
            result = run_turn(session, user_message="做一个监狱游戏", config=config)
        self.assertIn("视角", result["assistant_message"])
        self.assertEqual(result["choices"], ["俯视角", "横版"])
        self.assertTrue(result["ready_to_export"])
        self.assertEqual(len(session["messages"]), 2)

    def test_export_brief_from_session(self) -> None:
        session = new_session()
        session["draft_brief"] = {
            "project": {
                "title": "Prison",
                "description": "Top-down prison escape",
                "art_direction": "flat 2D sprites",
                "dimension": "2d",
                "genre": "top_down",
                "gameplay_loop": "Sneak through prison, avoid guards, reach exit.",
                "session_goal": "Prototype: walk cycle and top-down movement.",
                "player_asset": "inmate",
                "controls": {
                    "move_left": ["A", "Left"],
                    "move_right": ["D", "Right"],
                },
                "viewport": {"width": 1280, "height": 720},
            },
            "assets": [
                {
                    "name": "inmate",
                    "type": "character",
                    "usage": "player_locomotion",
                    "usage_description": "Walk cycle for inmate",
                    "description": "Prison inmate walk cycle",
                    "display_size": "128x128 px",
                    "animation_method": "video",
                }
            ],
        }
        brief = export_brief(session)
        self.assertEqual(brief["project"]["title"], "Prison")
        self.assertEqual(brief["assets"][0]["name"], "inmate")


if __name__ == "__main__":
    unittest.main()
