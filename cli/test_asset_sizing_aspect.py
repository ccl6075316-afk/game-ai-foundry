"""Aspect-aware generation_size + size_baseline display derivation."""

from __future__ import annotations

import unittest

from asset_sizing import (
    effective_display_dict,
    resolve_effective_display_size,
    resolve_generation_image_size,
)
from brief import AssetSpec, AssetType, ProjectContext
from display_size import DisplaySize


class AssetSizingAspectTests(unittest.TestCase):
    def test_character_16_9_generation_not_square(self) -> None:
        project = ProjectContext(viewport={"width": 1280, "height": 720})
        spec = AssetSpec(
            name="fish_swim",
            id="fish_swim",
            type=AssetType.CHARACTER,
            aspect_ratio="16:9",
            display_size=DisplaySize(192, 108),
        )
        size = resolve_generation_image_size(spec, project)
        parts = size.lower().split("x")
        self.assertEqual(len(parts), 2)
        self.assertNotEqual(parts[0], parts[1])

    def test_size_baseline_derives_display_from_real_length(self) -> None:
        project = ProjectContext(
            viewport={"width": 1280, "height": 720},
            size_baseline={
                "asset_id": "reference_fish",
                "real_length_cm": 80,
                "display_size": {"width": 213, "height": 120},
            },
        )
        spec = AssetSpec(
            name="small_fish",
            id="small_fish",
            type=AssetType.CHARACTER,
            aspect_ratio="16:9",
            real_length_cm=19,
        )
        eff = resolve_effective_display_size(spec, project)
        self.assertEqual(eff.height, 28)
        self.assertEqual(eff.width, 50)  # 28 * 16/9 rounded

    def test_effective_display_dict_for_pipeline(self) -> None:
        project = ProjectContext(viewport={"width": 1280, "height": 720})
        spec = AssetSpec(
            name="hero",
            id="hero",
            type=AssetType.CHARACTER,
            display_size=DisplaySize(64, 64),
        )
        self.assertEqual(
            effective_display_dict(spec, project),
            {"width": 64, "height": 64},
        )


if __name__ == "__main__":
    unittest.main()
