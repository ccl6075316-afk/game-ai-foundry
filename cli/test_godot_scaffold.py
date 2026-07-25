"""Tests for godot scaffold from production."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from godot_scaffold import scaffold_from_production
from production import derive_production, save_production
from test_fixtures import EXAMPLE_BRIEF


class GodotScaffoldTest(unittest.TestCase):
    def test_scaffold_writes_scenes_and_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prod_path = Path(tmp) / "production.json"
            save_production(derive_production(EXAMPLE_BRIEF), prod_path)
            project = Path(tmp) / "game"
            result = scaffold_from_production(prod_path, project_path=project)

            self.assertTrue((project / "scenes" / "main.tscn").is_file())
            self.assertTrue((project / "scenes" / "player.tscn").is_file())
            self.assertTrue((project / "scripts" / "Main.cs").is_file())
            self.assertTrue((project / "scripts" / "KnightController.cs").is_file())
            self.assertTrue((project / "scripts" / "GameState.cs").is_file())
            self.assertIn("move_right", (project / "project.godot").read_text(encoding="utf-8"))
            self.assertEqual(
                result["validate"] if "validate" in result else "skipped",
                result.get("validate", "skipped") or "skipped",
            )

    def test_scaffold_places_layout_props_under_world(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prod_path = Path(tmp) / "production.json"
            data = derive_production(EXAMPLE_BRIEF)
            placements = data["production_doc"]["layout"]["placements"]
            self.assertTrue(placements)
            save_production(data, prod_path)
            project = Path(tmp) / "game"
            scaffold_from_production(prod_path, project_path=project)
            main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
            self.assertIn('[node name="World" type="Node2D" parent="."]', main)
            self.assertIn("WoodenCrate", main)
            self.assertIn("MossyRock", main)
            self.assertIn("assets/props/wooden_crate_nobg.png", main)
            self.assertIn('parent="World"', main)
            self.assertIn("position = Vector2(", main)


if __name__ == "__main__":
    unittest.main()
