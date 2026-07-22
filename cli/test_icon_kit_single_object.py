"""Tests for item slug + image model tier routing."""

from __future__ import annotations

import unittest

from brief import AssetSpec, AssetType, slugify_item_label, unique_item_slugs
from image_model_route import (
    effective_generate_tier,
    resolve_image_model_for_tier,
)


class ItemSlugTests(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify_item_label("Gold Coin"), "gold_coin")
        self.assertEqual(slugify_item_label("  sword!! "), "sword")

    def test_unique_slugs(self) -> None:
        self.assertEqual(
            unique_item_slugs(["Sword", "sword", "potion"]),
            ["sword", "sword_2", "potion"],
        )


class GenerateTierTests(unittest.TestCase):
    def test_asset_parse_tier(self) -> None:
        spec = AssetSpec.from_dict(
            {
                "name": "hud",
                "id": "hud",
                "type": "texture",
                "usage": "ui_element",
                "usage_description": "btn",
                "display_size": {"width": 32, "height": 32},
                "generate_tier": "bulk",
            }
        )
        self.assertEqual(spec.generate_tier, "bulk")

    def test_kit_item_defaults_bulk(self) -> None:
        self.assertEqual(
            effective_generate_tier(generate_tier=None, for_icon_kit_item=True),
            "bulk",
        )
        self.assertEqual(
            effective_generate_tier(generate_tier="default", for_icon_kit_item=True),
            "default",
        )

    def test_resolve_bulk_fallback(self) -> None:
        cfg = {"image": {"model": "main-model"}}
        self.assertEqual(resolve_image_model_for_tier(cfg, "bulk"), "main-model")
        cfg2 = {"image": {"model": "main-model", "bulk_model": "cheap-model"}}
        self.assertEqual(resolve_image_model_for_tier(cfg2, "bulk"), "cheap-model")
        self.assertEqual(resolve_image_model_for_tier(cfg2, "default"), "main-model")
        self.assertEqual(
            resolve_image_model_for_tier(cfg2, "bulk", explicit_model="cli-model"),
            "cli-model",
        )


class IconKitGridSoftTests(unittest.TestCase):
    def test_small_grid_no_longer_upgraded_as_authority(self) -> None:
        """grid may remain as written; it no longer drives slice."""
        spec = AssetSpec.from_dict(
            {
                "name": "kit",
                "id": "kit",
                "type": "icon_kit",
                "usage": "item_icon",
                "usage_description": "icons",
                "display_size": {"width": 32, "height": 32},
                "items": ["a", "b", "c", "d", "e", "f"],
                "grid": "2x2",
            }
        )
        self.assertEqual(spec.type, AssetType.ICON_KIT)
        # Keep authored grid string (no silent upgrade for slicing).
        self.assertEqual(spec.grid, "2x2")


if __name__ == "__main__":
    unittest.main()
