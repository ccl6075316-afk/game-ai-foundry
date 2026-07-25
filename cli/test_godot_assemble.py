"""Tests for godot assemble layout props + plan resolution."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from godot_assemble import GodotAssembleError, _resolve_character_asset, assemble_from_plan, wire_main_scene
from production import derive_production, save_production
from test_fixtures import write_brief

# Minimal valid 1×1 RGBA PNG
_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


class GodotAssemblePlanTests(unittest.TestCase):
    def test_explicit_character_asset(self) -> None:
        name = _resolve_character_asset(
            {"character_asset": "magic_prince"},
            idle_still=None,
            animations=[],
        )
        self.assertEqual(name, "magic_prince")

    def test_from_idle_still_path(self) -> None:
        name = _resolve_character_asset(
            {},
            idle_still="output/demo/magic_prince_nobg.png",
            animations=[],
        )
        self.assertEqual(name, "magic_prince")

    def test_from_animation_reference_asset(self) -> None:
        name = _resolve_character_asset(
            {},
            idle_still=None,
            animations=[{"asset": "magic_prince_cannon", "reference_asset": "magic_prince"}],
        )
        self.assertEqual(name, "magic_prince")

    def test_missing_character_asset_raises(self) -> None:
        with self.assertRaises(GodotAssembleError):
            _resolve_character_asset({}, idle_still=None, animations=[{"asset": "orphan_anim"}])


class GodotAssembleLayoutTests(unittest.TestCase):
    def test_wire_main_scene_places_world_props(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "game"
            (project / "scripts").mkdir(parents=True)
            (project / "scripts" / "Main.cs").write_text("// stub\n", encoding="utf-8")
            (project / "scripts" / "Player.cs").write_text("// stub\n", encoding="utf-8")
            layout = {
                "coord_space": "viewport_norm",
                "regions": [],
                "placements": [
                    {"asset": "wooden_crate", "xy_norm": [0.2, 0.475], "region": "playable"},
                ],
            }
            wire_main_scene(
                project,
                idle_still_res="assets/sprites/idle_still.png",
                layout=layout,
                viewport={"width": 1280, "height": 720},
            )
            main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
            self.assertIn('[node name="World" type="Node2D" parent="."]', main)
            self.assertIn("WoodenCrate", main)
            self.assertIn("assets/props/wooden_crate_nobg.png", main)
            self.assertIn("position = Vector2(256, 342)", main)
            self.assertIn("load_steps=4", main)  # Main + Player scripts + idle + 1 prop

    def test_assemble_copies_prop_and_skips_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            out = repo / "output" / "demo"
            out.mkdir(parents=True)
            crate = out / "wooden_crate_nobg.png"
            crate.write_bytes(_PNG_1X1)
            # missing mossy_rock on purpose

            project_rel = "games/demo"
            plan = {
                "project_path": project_rel,
                "project_name": "Layout Assemble Demo",
                "template": "dotnet",
                "main_scene": "scenes/main.tscn",
                "animations": [],
                "backgrounds": [],
                "idle_still": str(crate.resolve()),
                "character_asset": "hero",
                "viewport": {"width": 1280, "height": 720},
                "layout": {
                    "coord_space": "viewport_norm",
                    "regions": [],
                    "placements": [
                        {"asset": "wooden_crate", "xy_norm": [0.2, 0.475]},
                        {"asset": "mossy_rock", "xy_norm": [0.8, 0.475]},
                    ],
                },
                "props": [
                    {
                        "asset": "wooden_crate",
                        "image": str(crate.resolve()),
                    },
                    {
                        "asset": "mossy_rock",
                        "image": str((out / "mossy_rock_nobg.png").resolve()),
                    },
                ],
            }
            result = assemble_from_plan(plan, repo_root=repo)
            self.assertTrue((repo / project_rel / "assets" / "props" / "wooden_crate_nobg.png").is_file())
            skipped = result.get("props_skipped") or []
            self.assertEqual(len(skipped), 1)
            self.assertEqual(skipped[0]["asset"], "mossy_rock")
            main = (repo / project_rel / "scenes" / "main.tscn").read_text(encoding="utf-8")
            self.assertIn("WoodenCrate", main)
            self.assertIn("MossyRock", main)
            self.assertIn('parent="World"', main)


class GodotPlanLayoutPreferProductionTests(unittest.TestCase):
    def test_collect_plan_prefers_production_layout(self) -> None:
        from pipeline_manifest import _collect_godot_plan, _layout_for_godot_plan
        from brief import load_brief_full

        with tempfile.TemporaryDirectory() as tmp:
            plans = Path(tmp) / "plans"
            plans.mkdir()
            brief = write_brief(
                {
                    "project": {
                        "title": "Prefer Layout",
                        "description": "d",
                        "art_direction": "flat",
                        "dimension": "2d",
                        "genre": "2d_platformer",
                        "gameplay_loop": "walk",
                        "session_goal": "demo",
                        "player_asset": "hero",
                        "view": "side",
                        "controls": {"move_left": ["A"], "move_right": ["D"]},
                        "viewport": {"width": 1280, "height": 720},
                    },
                    "assets": [
                        {
                            "name": "hero",
                            "id": "hero",
                            "type": "character",
                            "usage": "player_idle",
                            "usage_description": "hero",
                            "description": "hero",
                            "display_size": {"width": 64, "height": 64},
                        },
                        {
                            "name": "wooden_crate",
                            "id": "wooden_crate",
                            "type": "texture",
                            "usage": "world_prop",
                            "content_class": "prop_static",
                            "usage_description": "crate",
                            "description": "crate",
                            "display_size": {"width": 64, "height": 64},
                        },
                    ],
                }
            )
            try:
                data = derive_production(brief)
                # Hand-edit placement so we can detect override vs fresh derive
                data["production_doc"]["layout"]["placements"] = [
                    {
                        "asset": "wooden_crate",
                        "xy_norm": [0.11, 0.22],
                        "region": "playable",
                    }
                ]
                save_production(data, plans / f"production_{brief.stem}.json")
                project, assets, _ = load_brief_full(brief)
                layout = _layout_for_godot_plan(
                    project,
                    assets,
                    brief_stem=brief.stem,
                    plans_dir=plans,
                )
                self.assertEqual(layout["placements"][0]["xy_norm"], [0.11, 0.22])

                plan = _collect_godot_plan(
                    brief_stem=brief.stem,
                    project=project,
                    assets=assets,
                    output_dir=Path(tmp) / "output",
                    tasks_by_id={},
                    godot_project=Path(tmp) / "game",
                    plans_dir=plans,
                )
                self.assertEqual(plan["layout"]["placements"][0]["xy_norm"], [0.11, 0.22])
                self.assertEqual(plan["props"][0]["asset"], "wooden_crate")
            finally:
                brief.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
