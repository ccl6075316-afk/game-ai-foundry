"""Tests for brief animation_graphs / transitions."""

from __future__ import annotations

import unittest

from brief import (
    AssetSpec,
    AssetType,
    CharacterAnimationGraph,
    AnimationTransitionEdge,
    ProjectContext,
    apply_deterministic_animation_graph_fixes,
    apply_deterministic_asset_type_fixes,
    apply_deterministic_brief_fixes,
    apply_deterministic_hud_fixes,
    apply_deterministic_visual_reference_fixes,
    infer_asset_type_from_hints,
    parse_assets_for_audit,
    looks_like_visual_reference_path,
    audit_animation_graphs,
    audit_brief_for_export,
    characters_requiring_animation_graph,
    load_brief_full,
    validate_brief_for_export,
)
from display_size import DisplaySize
from test_fixtures import EXAMPLE_BRIEF, MINIMAL_VIDEO_BRIEF, write_brief


class BriefTransitionsTests(unittest.TestCase):
    def test_example_brief_has_knight_graph(self) -> None:
        _, _, graphs = load_brief_full(EXAMPLE_BRIEF)
        self.assertEqual(len(graphs), 1)
        self.assertEqual(graphs[0].character_asset, "knight")
        self.assertEqual(graphs[0].transitions[0].from_clip, "idle")

    def test_magic_prince_requires_graph(self) -> None:
        from pathlib import Path

        brief = Path(__file__).resolve().parent.parent / "resources" / "magic-prince-brief.json"
        project, assets, graphs = load_brief_full(brief)
        self.assertIn("magic_prince", characters_requiring_animation_graph(assets))
        validate_brief_for_export(project, assets, animation_graphs=graphs)

    def test_one_shot_requires_then(self) -> None:
        project = ProjectContext(
            title="T",
            description="game",
            art_direction="art",
            dimension="2d",
        )
        ref = AssetSpec(
            name="hero",
            id="hero",
            type=AssetType.CHARACTER,
            usage="reference_still",
            usage_description="ref",
            display_size=DisplaySize(128, 128),
            description="hero",
        )
        walk = AssetSpec(
            name="hero_walk",
            id="hero_walk",
            type=AssetType.CHARACTER,
            usage="player_locomotion",
            usage_description="walk",
            display_size=DisplaySize(128, 128),
            description="walk",
            reference_asset="hero",
            action="walking",
            animation_method="video",
        )
        attack = AssetSpec(
            name="hero_attack",
            id="hero_attack",
            type=AssetType.CHARACTER,
            usage="player_attack",
            usage_description="atk",
            display_size=DisplaySize(128, 128),
            description="atk",
            reference_asset="hero",
            action="attack",
            animation_method="video",
            animation_loop=False,
        )
        assets = [ref, walk, attack]
        bad_graph = CharacterAnimationGraph(
            character_asset="hero",
            default_clip="idle",
            transitions=[AnimationTransitionEdge(from_clip="walk", to_clip="attack")],
        )
        errors = audit_animation_graphs(assets, [bad_graph])
        self.assertTrue(any("then" in e for e in errors))

    def test_minimal_video_needs_graph_in_audit(self) -> None:
        bare = dict(MINIMAL_VIDEO_BRIEF)
        bare.pop("animation_graphs", None)
        path = write_brief(bare)
        try:
            project, assets, graphs = load_brief_full(path)
            self.assertIn("knight", characters_requiring_animation_graph(assets))
            from brief import audit_brief_for_export

            errors = audit_brief_for_export(project, assets, animation_graphs=graphs)
            self.assertTrue(any("animation_graphs" in e for e in errors))
        finally:
            path.unlink(missing_ok=True)

    def test_deterministic_remap_asset_name_to_clip(self) -> None:
        draft = {
            "assets": [
                {
                    "name": "球员_普通",
                    "type": "character",
                    "usage": "reference_still",
                    "usage_description": "ref",
                    "description": "p",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                },
                {
                    "name": "球员_普通_跑动",
                    "type": "character",
                    "usage": "player_locomotion",
                    "usage_description": "run",
                    "description": "run",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                    "reference_asset": "球员_普通",
                    "action": "running",
                    "animation_method": "video",
                },
                {
                    "name": "球员_普通_倒地",
                    "type": "character",
                    "usage": "player_action",
                    "usage_description": "fall",
                    "description": "fall",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                    "reference_asset": "球员_普通",
                    "action": "fall",
                    "animation_method": "video",
                    "animation_loop": False,
                },
            ],
            "animation_graphs": [
                {
                    "character_asset": "球员_普通",
                    "default_clip": "球员_普通",
                    "states": [{"id": "跑", "clip": "跑动"}],
                    "transitions": [
                        {"from": "idle", "to": "球员_普通_跑动", "bidirectional": True},
                        {"from": "跑动", "to": "倒地"},
                    ],
                }
            ],
        }
        fixed, notes = apply_deterministic_animation_graph_fixes(draft)
        self.assertTrue(any("states" in n for n in notes))
        g = fixed["animation_graphs"][0]
        self.assertNotIn("states", g)
        self.assertEqual(g["default_clip"], "idle")
        tos = {e["to"] for e in g["transitions"]}
        self.assertIn("跑动", tos)
        self.assertIn("倒地", tos)
        fall = next(e for e in g["transitions"] if e["to"] == "倒地")
        self.assertEqual(fall.get("then"), "idle")
        errors = audit_animation_graphs(
            [AssetSpec.from_dict(a) for a in fixed["assets"]],
            [
                CharacterAnimationGraph.from_dict(g)
                for g in fixed["animation_graphs"]
            ],
        )
        self.assertEqual(errors, [])

    def test_deterministic_asset_id_and_art_direction_fill(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "ui_style": "pixel cozy",
                "art_direction": "",
            },
            "assets": [
                {
                    "name": "鱼_鲫鱼_游动",
                    "type": "character_pose",
                    "usage": "animation_clip",
                    "description": "swim",
                    "display_size": "64x64 px",
                    "generate_method": "video",
                    "reference_asset": "fish",
                    "action": "swim",
                    "animation_method": "video",
                },
                {
                    "id": "BAD ID",
                    "name": "rod_icon",
                    "type": "texture",
                    "usage": "ui_icon",
                    "description": "rod",
                    "display_size": "32x32 px",
                    "generate_method": "image",
                },
            ],
        }
        from brief import apply_deterministic_asset_id_fixes, apply_deterministic_project_field_fixes

        fixed, notes = apply_deterministic_asset_id_fixes(draft)
        self.assertTrue(any("filled" in n for n in notes))
        ids = [a["id"] for a in fixed["assets"]]
        self.assertTrue(all(isinstance(i, str) and i[:1].islower() for i in ids))
        self.assertNotIn("BAD ID", ids)
        self.assertTrue(ids[0].startswith("pose_"))
        fixed2, notes2 = apply_deterministic_project_field_fixes(fixed)
        self.assertEqual(fixed2["project"]["art_direction"], "pixel cozy")
        self.assertTrue(any("art_direction" in n for n in notes2))

    def test_deterministic_asset_type_aliases(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {
                    "name": "fish_swim",
                    "type": "animation",
                    "usage": "animation_clip",
                    "reference_asset": "fish",
                    "animation_method": "video",
                    "description": "swim",
                },
                {
                    "name": "rod_icon",
                    "type": "item",
                    "usage": "ui_icon",
                    "description": "rod",
                },
                {
                    "name": "kit",
                    "type": "item",
                    "usage": "ui_icon",
                    "items": ["a", "b"],
                    "description": "kit",
                },
            ],
        }
        fixed, notes = apply_deterministic_asset_type_fixes(draft)
        self.assertTrue(any("animation->character_pose" in n for n in notes))
        self.assertTrue(any("item->texture" in n for n in notes))
        self.assertTrue(any("item->icon_kit" in n for n in notes))
        by_name = {a["name"]: a["type"] for a in fixed["assets"]}
        self.assertEqual(by_name["fish_swim"], "character_pose")
        self.assertEqual(by_name["rod_icon"], "texture")
        self.assertEqual(by_name["kit"], "icon_kit")

    def test_infer_asset_type_from_name_and_id_hints(self) -> None:
        self.assertEqual(
            infer_asset_type_from_hints({"name": "主界面_建筑_钓具店"}),
            "texture",
        )
        self.assertEqual(
            infer_asset_type_from_hints({"name": "鱼_鲫鱼_角色"}),
            "character",
        )
        self.assertEqual(
            infer_asset_type_from_hints({"name": "鱼_鲫鱼_游动"}),
            "character_pose",
        )
        self.assertEqual(
            infer_asset_type_from_hints({"name": "水族馆_小型缸_观赏背景"}),
            "background",
        )
        self.assertEqual(
            infer_asset_type_from_hints({"id": "tex_hub_boat_rod", "name": "船"}),
            "texture",
        )
        self.assertIsNone(infer_asset_type_from_hints({"name": "未分类物件"}))

    def test_parse_assets_for_audit_collects_all_bad_types(self) -> None:
        assets_raw = [
            {"name": "a1", "type": "animation", "description": "x"},
            {"name": "a2", "type": "animation", "description": "x"},
            {"name": "i1", "type": "item", "description": "x"},
            {
                "id": "ok",
                "name": "hero",
                "type": "character",
                "usage": "reference_still",
                "usage_description": "ref",
                "description": "h",
                "display_size": "64x64 px",
                "generate_method": "image",
            },
        ]
        assets, errors = parse_assets_for_audit(assets_raw)
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].name, "hero")
        blob = "\n".join(errors)
        self.assertIn("illegal type 'animation'", blob)
        self.assertIn("illegal type 'item'", blob)
        self.assertIn("2 asset(s)", blob)

    def test_deterministic_hud_binds_ui_elements(self) -> None:
        draft = {
            "project": {"title": "T", "description": "d", "art_direction": "a", "dimension": "2d"},
            "assets": [
                {
                    "name": "判罚事件UI",
                    "type": "icon_kit",
                    "usage": "ui_element",
                    "usage_description": "ui",
                    "description": "ui",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                    "items": ["黄牌", "红牌"],
                }
            ],
        }
        fixed, notes = apply_deterministic_hud_fixes(draft)
        self.assertTrue(any("hud" in n for n in notes))
        hud = fixed["project"]["hud"]
        self.assertEqual(len(hud), 1)
        self.assertEqual(hud[0]["asset"], "判罚事件UI")
        self.assertTrue(hud[0]["anchor"])
        project = ProjectContext.from_dict(fixed["project"])
        assets = [AssetSpec.from_dict(a) for a in fixed["assets"]]
        gaps = audit_brief_for_export(project, assets, animation_graphs=[])
        self.assertFalse(any("project.hud" in g for g in gaps))

    def test_visual_reference_prose_rejected(self) -> None:
        self.assertFalse(
            looks_like_visual_reference_path(
                "TV broadcast perspective, Q版风格参考胡闹厨房"
            )
        )
        self.assertTrue(
            looks_like_visual_reference_path(
                "output/my-game/visual-target/selected.png"
            )
        )
        draft = {
            "project": {
                "title": "T",
                "description": "d",
                "art_direction": "pixel art",
                "dimension": "2d",
                "visual_reference": "Cute Overcooked style, warm palette",
            },
            "assets": [],
        }
        fixed, notes = apply_deterministic_visual_reference_fixes(draft)
        self.assertTrue(any("visual_reference" in n for n in notes))
        self.assertEqual(fixed["project"]["visual_reference"], "")
        self.assertIn("Cute Overcooked", fixed["project"]["art_direction"])
        project = ProjectContext.from_dict(fixed["project"])
        gaps = audit_brief_for_export(project, [], animation_graphs=[])
        self.assertFalse(any("visual_reference" in g for g in gaps))

    def test_clear_scene_visual_reference_prose(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "description": "d",
                "art_direction": "pixel art",
                "dimension": "2d",
                "scenes": [
                    {
                        "id": "dock",
                        "title": "钓场",
                        "visual_reference": "warm coastal pixel mood board",
                    }
                ],
            },
            "assets": [],
        }
        fixed, notes = apply_deterministic_visual_reference_fixes(draft)
        self.assertTrue(any("scenes[dock]" in n for n in notes))
        self.assertNotIn("visual_reference", fixed["project"]["scenes"][0])
        self.assertIn("warm coastal", fixed["project"]["art_direction"])


if __name__ == "__main__":
    unittest.main()
