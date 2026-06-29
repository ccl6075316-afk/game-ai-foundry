"""Tests for godogen-style display_size + generation image_size."""

from __future__ import annotations

import unittest

from asset_sizing import audit_display_size_consistency, resolve_generation_image_size
from brief import AssetSpec, AssetType, CharacterAnimationGraph, ProjectContext
from display_size import DisplaySize, parse_display_size


class DisplaySizeTests(unittest.TestCase):
    def test_parse_dict_and_string(self) -> None:
        self.assertEqual(parse_display_size({"width": 128, "height": 128}), DisplaySize(128, 128))
        self.assertEqual(parse_display_size("64x64 px per icon"), DisplaySize(64, 64))

    def test_generation_size_scales_with_display(self) -> None:
        project = ProjectContext(viewport={"width": 1280, "height": 720})
        spec = AssetSpec(
            name="hero",
            type=AssetType.CHARACTER,
            display_size=DisplaySize(128, 128),
        )
        self.assertEqual(resolve_generation_image_size(spec, project), "1024x1024")

    def test_background_uses_display(self) -> None:
        project = ProjectContext(viewport={"width": 1280, "height": 720})
        spec = AssetSpec(
            name="bg",
            type=AssetType.BACKGROUND,
            usage="world_background",
            display_size=DisplaySize(1280, 720),
        )
        self.assertEqual(resolve_generation_image_size(spec, project), "1280x720")

    def test_mismatched_reference_asset_fails_audit(self) -> None:
        ref = AssetSpec(
            name="knight",
            type=AssetType.CHARACTER,
            usage="reference_still",
            usage_description="ref",
            display_size=DisplaySize(128, 128),
        )
        walk = AssetSpec(
            name="knight_walk",
            type=AssetType.CHARACTER,
            usage="player_locomotion",
            usage_description="walk",
            display_size=DisplaySize(96, 96),
            reference_asset="knight",
            action="walk",
        )
        errors = audit_display_size_consistency([ref, walk])
        self.assertTrue(any("must match" in e for e in errors))

    def test_animation_graph_family_same_size(self) -> None:
        ref = AssetSpec(
            name="knight",
            type=AssetType.CHARACTER,
            usage="reference_still",
            usage_description="ref",
            display_size=DisplaySize(128, 128),
        )
        walk = AssetSpec(
            name="knight_walk",
            type=AssetType.CHARACTER,
            usage="player_locomotion",
            usage_description="walk",
            display_size=DisplaySize(128, 128),
            reference_asset="knight",
            action="walk",
        )
        graph = CharacterAnimationGraph(character_asset="knight")
        self.assertEqual(
            audit_display_size_consistency([ref, walk], animation_graphs=[graph]),
            [],
        )


if __name__ == "__main__":
    unittest.main()
