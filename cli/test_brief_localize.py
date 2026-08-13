"""Tests for brief localize (one-shot Chinese narrative migration)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from brief_localize import is_fishing_project, localize_brief_narratives
from brief_shards import load_json_shard, save_json_shard


class TestBriefLocalize(unittest.TestCase):
    def test_is_fishing_project_by_path(self) -> None:
        self.assertTrue(
            is_fishing_project(Path("projects/fishing-2d/brief.json"), brief={})
        )
        self.assertFalse(
            is_fishing_project(Path("projects/space-runner/brief.json"), brief={})
        )

    def test_is_fishing_project_by_genre_title(self) -> None:
        self.assertTrue(
            is_fishing_project(
                Path("projects/other/brief.json"),
                brief={"project": {"title": "Coastal", "genre": "fishing"}},
            )
        )
        self.assertTrue(
            is_fishing_project(
                Path("projects/other/brief.json"),
                brief={"project": {"title": "2D钓鱼模拟"}},
            )
        )
        self.assertFalse(
            is_fishing_project(
                Path("projects/other/brief.json"),
                brief={"project": {"title": "Platformer", "genre": "platformer"}},
            )
        )

    def test_localize_rewrites_shard_description(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scene_path = root / "scenes" / "hub.json"
            save_json_shard(
                scene_path,
                {
                    "id": "hub",
                    "title": "Hub",
                    "summary": "Coastal fishing pier overview.",
                },
            )
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "Fish",
                            "description": "A fishing game.",
                            "art_direction": "Pixel art.",
                            "dimension": "2d",
                        },
                        "scenes": [
                            {"id": "hub", "title": "Hub", "path": "scenes/hub.json"},
                        ],
                        "assets": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            report = localize_brief_narratives(
                brief_path,
                translator=lambda _key, text: "中文" + text,
                i_confirm=True,
            )

            self.assertTrue(report.get("ok"))
            shard = load_json_shard(scene_path)
            self.assertTrue(str(shard.get("summary", "")).startswith("中文"))
            self.assertEqual(shard.get("id"), "hub")
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            self.assertTrue(
                str(brief["project"].get("description", "")).startswith("中文")
            )

    def test_requires_i_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            brief_path = Path(td) / "brief.json"
            brief_path.write_text(
                json.dumps({"project": {"title": "T"}, "assets": []}),
                encoding="utf-8",
            )
            report = localize_brief_narratives(
                brief_path,
                translator=lambda _k, t: t,
                i_confirm=False,
            )
            self.assertFalse(report.get("ok"))
            self.assertIn("i-confirm", str(report.get("error", "")).lower())

    def test_skips_cjk_title_and_preserves_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scene_path = root / "scenes" / "hub.json"
            save_json_shard(
                scene_path,
                {
                    "id": "hub",
                    "title": "主界面",
                    "summary": "English summary only.",
                },
            )
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {"title": "2D钓鱼", "description": "English desc."},
                        "scenes": [
                            {"id": "hub", "title": "主界面", "path": "scenes/hub.json"},
                        ],
                        "assets": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = localize_brief_narratives(
                brief_path,
                translator=lambda _k, t: "译" + t,
                i_confirm=True,
            )
            self.assertTrue(report.get("ok"))
            shard = load_json_shard(scene_path)
            self.assertEqual(shard["id"], "hub")
            self.assertEqual(shard["title"], "主界面")
            self.assertTrue(str(shard["summary"]).startswith("译"))
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            self.assertEqual(brief["project"]["title"], "2D钓鱼")
            self.assertEqual(brief["scenes"][0]["id"], "hub")

    def test_deletes_brief_zh_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zh = root / "brief.zh.md"
            zh.write_text("# zh", encoding="utf-8")
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {"title": "T", "description": "English."},
                        "assets": [],
                    }
                ),
                encoding="utf-8",
            )
            report = localize_brief_narratives(
                brief_path,
                translator=lambda _k, t: "中" + t,
                i_confirm=True,
            )
            self.assertTrue(report.get("ok"))
            self.assertFalse(zh.is_file())
            self.assertIn(str(zh.resolve()), report.get("changed_paths") or [])


if __name__ == "__main__":
    unittest.main()
