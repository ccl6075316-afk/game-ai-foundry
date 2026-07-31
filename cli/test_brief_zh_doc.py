"""Tests for Chinese brief companion document."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from brief_zh_doc import (
    BRIEF_ZH_DOC_NAME,
    brief_zh_doc_path_for,
    render_brief_zh_skeleton,
    write_brief_zh_document,
)


class BriefZhDocTests(unittest.TestCase):
    def test_skeleton_has_chinese_sections_and_asset_ids(self) -> None:
        brief = {
            "brief_meta": {"frozen_at": "2026-07-26T00:00:00+00:00", "source": "test"},
            "project": {
                "title": "Forest Platformer",
                "description": "A knight in the woods.",
                "genre": "2d_platformer",
                "dimension": "2d",
                "gameplay_loop": "Run and jump.",
                "session_goal": "One level.",
                "art_direction": "Cartoon.",
                "player_asset": "knight",
                "view": "side",
            },
            "assets": [
                {
                    "id": "knight",
                    "name": "knight",
                    "type": "character",
                    "usage": "player_idle",
                    "usage_description": "Idle pose",
                }
            ],
        }
        md = render_brief_zh_skeleton(brief)
        self.assertIn("中文说明", md)
        self.assertIn("玩法循环", md)
        self.assertIn("资产列表", md)
        self.assertIn("`knight`", md)
        self.assertIn("导出前", md)
        self.assertIn("brief.draft.json", md)

    def test_skeleton_includes_scenes_systems_ui_panels(self) -> None:
        brief = {
            "project": {
                "title": "钓",
                "description": "short overview",
                "genre": "sim",
                "dimension": "2d",
                "gameplay_loop": "cast and sell",
                "session_goal": "endless",
                "art_direction": "pixel",
                "scenes": [
                    {"id": "dock", "title": "钓场", "summary": "Cast line."},
                ],
                "systems": [
                    {"id": "economy", "title": "经济", "summary": "Tickets and prices."},
                ],
                "ui_panels": [
                    {"id": "sell", "title": "出售", "slots": ["卖出", "入库"]},
                ],
            },
            "assets": [],
        }
        md = render_brief_zh_skeleton(brief)
        self.assertIn("场景（有进出的屏）", md)
        self.assertIn("`dock`", md)
        self.assertIn("逻辑系统（跨场景）", md)
        self.assertIn("`economy`", md)
        self.assertIn("UI 面板", md)
        self.assertIn("`sell`", md)

    def test_skeleton_includes_planner_notes(self) -> None:
        brief = {
            "project": {
                "title": "钓",
                "description": "eng",
                "genre": "g",
                "dimension": "2d",
                "gameplay_loop": "loop",
                "session_goal": "goal",
                "art_direction": "art",
            },
            "assets": [],
        }
        md = render_brief_zh_skeleton(brief, planner_notes="# 笔记\n\n- 已拍板：拔河收线")
        self.assertIn("策划笔记", md)
        self.assertIn("拔河收线", md)

    def test_write_from_draft_without_brief_json(self) -> None:
        brief = {
            "project": {
                "title": "Demo",
                "description": "d",
                "genre": "g",
                "dimension": "2d",
                "gameplay_loop": "loop",
                "session_goal": "goal",
                "art_direction": "art",
            },
            "assets": [{"id": "a1", "name": "a1", "type": "prop", "usage": "prop"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brief.draft.json").write_text(json.dumps(brief), encoding="utf-8")
            missing_brief = root / "brief.json"
            info = write_brief_zh_document(missing_brief, config={}, use_llm=False)
            self.assertTrue(Path(info["zh_doc_path"]).is_file())
            self.assertEqual(info["zh_doc_mode"], "skeleton")
            self.assertIn("工作草稿", Path(info["zh_doc_path"]).read_text(encoding="utf-8"))

    def test_write_uses_skeleton_without_api(self) -> None:
        brief = {
            "project": {
                "title": "Demo",
                "description": "d",
                "genre": "g",
                "dimension": "2d",
                "gameplay_loop": "loop",
                "session_goal": "goal",
                "art_direction": "art",
            },
            "assets": [{"id": "a1", "name": "a1", "type": "prop", "usage": "prop"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = Path(tmp) / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            info = write_brief_zh_document(brief_path, brief, config={})
            out = Path(info["zh_doc_path"])
            self.assertEqual(out.name, BRIEF_ZH_DOC_NAME)
            self.assertTrue(out.is_file())
            self.assertEqual(info["zh_doc_mode"], "skeleton")
            self.assertEqual(brief_zh_doc_path_for(brief_path), out)


if __name__ == "__main__":
    unittest.main()
