"""Tests for brief animation_graphs / transitions."""

from __future__ import annotations

import unittest

from brief import (
    AssetSpec,
    AssetType,
    CharacterAnimationGraph,
    AnimationTransitionEdge,
    ProjectContext,
    audit_animation_graphs,
    characters_requiring_animation_graph,
    load_brief_full,
    validate_brief_for_export,
)
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
            display_size="128x128 px",
            description="hero",
        )
        walk = AssetSpec(
            name="hero_walk",
            type=AssetType.CHARACTER,
            usage="player_locomotion",
            usage_description="walk",
            display_size="128x128 px",
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
            display_size="128x128 px",
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


if __name__ == "__main__":
    unittest.main()
