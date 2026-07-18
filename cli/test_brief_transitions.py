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
    apply_deterministic_brief_fixes,
    apply_deterministic_hud_fixes,
    apply_deterministic_visual_reference_fixes,
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
            type=AssetType.CHARACTER,
            usage="reference_still",
            usage_description="ref",
            display_size=DisplaySize(128, 128),
            description="hero",
        )
        walk = AssetSpec(
            name="hero_walk",
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


if __name__ == "__main__":
    unittest.main()
