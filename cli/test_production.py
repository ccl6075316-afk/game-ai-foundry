"""Tests for production derive / validate."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from production import (
    PRODUCTION_SCHEMA_VERSION,
    derive_production,
    load_production,
    save_production,
    validate_production,
)
from test_fixtures import EXAMPLE_BRIEF, write_brief


class ProductionDeriveTest(unittest.TestCase):
    def test_derive_from_example_brief(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        self.assertEqual(
            data["production_meta"]["schema_version"],
            PRODUCTION_SCHEMA_VERSION,
        )
        doc = data["production_doc"]
        self.assertEqual(doc["genre"], "2d_platformer")
        self.assertEqual(doc["player"]["asset"], "knight")
        self.assertEqual(doc["viewport"]["width"], 1280)
        self.assertTrue(doc["godot_tasks"])
        self.assertTrue(doc["scenes"])
        self.assertEqual(doc["scaffold"]["main_scene"], "scenes/main.tscn")
        self.assertIn("input_map", [t["id"] for t in doc["godot_tasks"]])
        self.assertIn("player_controller", [t["id"] for t in doc["godot_tasks"]])

    def test_derive_validate_roundtrip(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        errors = validate_production(data, brief_path=EXAMPLE_BRIEF)
        self.assertEqual(errors, [])

    def test_save_and_load(self) -> None:
        brief = write_brief(
            {
                "project": {
                    "title": "Tmp",
                    "description": "tmp",
                    "art_direction": "flat",
                    "dimension": "2d",
                    "genre": "top_down",
                    "gameplay_loop": "explore",
                    "session_goal": "demo",
                    "player_asset": "hero",
                    "controls": {"move_up": ["W"]},
                    "viewport": {"width": 800, "height": 600},
                },
                "assets": [
                    {
                        "name": "hero",
                        "type": "character",
                        "usage": "player_idle",
                        "usage_description": "hero",
                        "description": "hero",
                        "display_size": {"width": 32, "height": 32},
                    }
                ],
            }
        )
        try:
            data = derive_production(brief)
            out = brief.parent / "production_test.json"
            save_production(data, out)
            loaded = load_production(out)
            self.assertEqual(loaded["production_doc"]["genre"], "top_down")
            self.assertEqual(validate_production(loaded, brief_path=brief), [])
        finally:
            brief.unlink(missing_ok=True)
            (brief.parent / "production_test.json").unlink(missing_ok=True)

    def test_validate_rejects_empty_tasks(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        data["production_doc"]["godot_tasks"] = []
        errors = validate_production(data)
        self.assertTrue(any("godot_tasks" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
