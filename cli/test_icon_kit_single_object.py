"""Tests for item slug + image model tier routing + icon item objects."""

from __future__ import annotations

import unittest

from brief import (
    AssetSpec,
    AssetType,
    IconKitItem,
    find_icon_kit_item,
    parse_icon_kit_item,
    slugify_item_label,
    unique_item_slugs,
    unique_kit_item_slugs,
)
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


class IconKitItemObjectTests(unittest.TestCase):
    def test_parse_string_and_object(self) -> None:
        s = parse_icon_kit_item("sword")
        self.assertEqual(s.id, "sword")
        self.assertFalse(s.id_from_object)
        o = parse_icon_kit_item(
            {
                "id": "health_potion",
                "label": "red potion",
                "usage": "pickup",
                "usage_description": "restores HP",
            }
        )
        self.assertEqual(o.id, "health_potion")
        self.assertEqual(o.prompt_label, "red potion")
        self.assertEqual(o.usage, "pickup")
        self.assertTrue(o.id_from_object)

    def test_slug_from_id_not_label(self) -> None:
        items = [
            IconKitItem(id="health_potion", label="Red Healing Potion", id_from_object=True),
            parse_icon_kit_item("gold coin"),
        ]
        self.assertEqual(unique_kit_item_slugs(items), ["health_potion", "gold_coin"])

    def test_asset_from_dict_mixed_items(self) -> None:
        spec = AssetSpec.from_dict(
            {
                "name": "kit",
                "id": "kit",
                "type": "icon_kit",
                "usage": "item_icon",
                "usage_description": "icons",
                "display_size": {"width": 32, "height": 32},
                "items": [
                    "sword",
                    {"id": "potion", "usage": "pickup", "usage_description": "heal"},
                ],
            }
        )
        self.assertEqual(len(spec.items), 2)
        self.assertIsInstance(spec.items[0], IconKitItem)
        self.assertEqual(spec.items[1].usage, "pickup")
        found = find_icon_kit_item(spec, "potion")
        self.assertIsNotNone(found)
        self.assertEqual(found.usage, "pickup")

    def test_string_and_object_same_id_fails(self) -> None:
        from brief import ProjectContext, audit_brief_for_export

        project = ProjectContext(
            title="T",
            description="d",
            art_direction="pixel",
            dimension="2d",
            genre="platformer",
            gameplay_loop="loop",
            session_goal="demo",
            controls={"move": ["A", "D"]},
            viewport={"width": 1280, "height": 720},
        )
        assets = [
            AssetSpec.from_dict(
                {
                    "name": "kit",
                    "id": "kit",
                    "type": "icon_kit",
                    "usage": "item_icon",
                    "usage_description": "icons",
                    "display_size": {"width": 32, "height": 32},
                    "items": ["potion", {"id": "potion", "usage": "pickup"}],
                }
            )
        ]
        errors = audit_brief_for_export(project, assets)
        self.assertTrue(any("duplicate item id" in e for e in errors))

    def test_duplicate_explicit_id_fails_validate(self) -> None:
        from brief import ProjectContext, audit_brief_for_export

        project = ProjectContext(
            title="T",
            description="d",
            art_direction="pixel",
            dimension="2d",
            genre="platformer",
            gameplay_loop="loop",
            session_goal="demo",
            controls={"move": ["A", "D"]},
            viewport={"width": 1280, "height": 720},
        )
        assets = [
            AssetSpec.from_dict(
                {
                    "name": "kit",
                    "id": "kit",
                    "type": "icon_kit",
                    "usage": "item_icon",
                    "usage_description": "icons",
                    "display_size": {"width": 32, "height": 32},
                    "items": [
                        {"id": "same", "label": "A"},
                        {"id": "same", "label": "B"},
                    ],
                }
            )
        ]
        errors = audit_brief_for_export(project, assets)
        self.assertTrue(any("duplicate item id" in e for e in errors))

    def test_find_by_label_slug_matches_pipeline(self) -> None:
        from brief import resolve_kit_item_slug, unique_kit_item_slugs

        spec = AssetSpec.from_dict(
            {
                "name": "kit",
                "id": "kit",
                "type": "icon_kit",
                "usage": "item_icon",
                "usage_description": "icons",
                "display_size": {"width": 32, "height": 32},
                "items": [
                    {"id": "health_potion", "label": "red potion"},
                    "Health Potion",  # slugifies to health_potion → _2
                ],
            }
        )
        # Second is string — allowed; first is object. Different authored ids.
        # Collision on slugified form:
        slugs = unique_kit_item_slugs(spec.items)
        self.assertEqual(slugs[0], "health_potion")
        self.assertEqual(slugs[1], "health_potion_2")
        found = find_icon_kit_item(spec, "red potion")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "health_potion")
        self.assertEqual(resolve_kit_item_slug(spec.items, found), "health_potion")
        found2 = find_icon_kit_item(spec, "Health Potion")
        self.assertEqual(resolve_kit_item_slug(spec.items, found2), "health_potion_2")


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
