"""Tests for icon_kit grid sizing helpers."""

from __future__ import annotations

import unittest

from brief import AssetSpec, AssetType, resolve_icon_grid, suggest_icon_grid


class IconGridTests(unittest.TestCase):
    def test_suggest_counts(self) -> None:
        self.assertEqual(suggest_icon_grid(3), "2x2")
        self.assertEqual(suggest_icon_grid(6), "2x3")
        self.assertEqual(suggest_icon_grid(8), "3x3")
        self.assertEqual(suggest_icon_grid(12), "3x4")

    def test_resolve_upgrades_too_small(self) -> None:
        self.assertEqual(resolve_icon_grid("2x2", 12), "3x4")
        self.assertEqual(resolve_icon_grid("2x3", 6), "2x3")

    def test_from_dict_keeps_authored_grid(self) -> None:
        spec = AssetSpec.from_dict(
            {
                "name": "kit",
                "id": "kit",
                "type": "icon_kit",
                "usage": "ui_element",
                "usage_description": "icons",
                "display_size": {"width": 32, "height": 32},
                "items": ["a", "b", "c", "d", "e", "f"],
                "grid": "2x2",
            }
        )
        self.assertEqual(spec.type, AssetType.ICON_KIT)
        self.assertEqual(spec.grid, "2x2")


if __name__ == "__main__":
    unittest.main()
