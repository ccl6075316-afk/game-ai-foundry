"""Tests for production_doc.layout derive + validate."""

from __future__ import annotations

import copy
import unittest

from production import LAYOUT_COORD_SPACE, derive_production, validate_production
from test_fixtures import EXAMPLE_BRIEF, write_brief


def _props_brief(*, view: str = "side") -> dict:
    return {
        "project": {
            "title": "Layout Props Demo",
            "description": "layout test",
            "art_direction": "flat",
            "dimension": "2d",
            "genre": "2d_platformer",
            "gameplay_loop": "walk",
            "session_goal": "demo",
            "player_asset": "hero",
            "view": view,
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
            {
                "name": "sword_rack",
                "id": "sword_rack",
                "type": "texture",
                "usage": "world_prop",
                "content_class": "weapon",
                "usage_description": "weapon prop",
                "description": "sword rack",
                "display_size": {"width": 64, "height": 64},
            },
            {
                "name": "grass_tile",
                "id": "grass_tile",
                "type": "texture",
                "usage": "tile_texture",
                "content_class": "floor_tile",
                "usage_description": "tile",
                "description": "grass",
                "display_size": {"width": 64, "height": 64},
            },
        ],
    }


class ProductionLayoutTest(unittest.TestCase):
    def test_derive_includes_layout_regions(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        layout = data["production_doc"].get("layout")
        self.assertIsInstance(layout, dict)
        self.assertEqual(layout.get("coord_space"), LAYOUT_COORD_SPACE)
        self.assertTrue(layout.get("regions"))
        self.assertIsInstance(layout.get("placements"), list)

    def test_derive_places_props_in_side_view(self) -> None:
        brief = write_brief(_props_brief(view="side"))
        try:
            data = derive_production(brief)
            layout = data["production_doc"]["layout"]
            self.assertEqual({r["id"] for r in layout["regions"]}, {"sky", "playable", "ground"})
            assets = {p["asset"] for p in layout["placements"]}
            self.assertEqual(assets, {"sword_rack", "wooden_crate"})
            for placement in layout["placements"]:
                self.assertEqual(placement["region"], "playable")
                xy = placement["xy_norm"]
                self.assertEqual(len(xy), 2)
                self.assertTrue(0.2 <= xy[0] <= 0.8)
                self.assertTrue(0.0 <= xy[1] <= 1.0)
            errors = validate_production(data, brief_path=brief)
            self.assertEqual(errors, [])
        finally:
            brief.unlink(missing_ok=True)

    def test_validate_rejects_unknown_placement_asset(self) -> None:
        brief = write_brief(_props_brief(view="side"))
        try:
            data = derive_production(brief)
            data["production_doc"]["layout"]["placements"].append(
                {"asset": "missing_prop", "xy_norm": [0.5, 0.5], "region": "playable"}
            )
            errors = validate_production(data, brief_path=brief)
            self.assertTrue(
                any("missing_prop" in e and "not found in brief" in e for e in errors)
            )
        finally:
            brief.unlink(missing_ok=True)

    def test_validate_without_layout_still_ok(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        data["production_doc"].pop("layout", None)
        self.assertEqual(validate_production(data, brief_path=EXAMPLE_BRIEF), [])

    def test_validate_rejects_unknown_region(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        layout = copy.deepcopy(data["production_doc"]["layout"])
        layout["placements"] = [
            {"asset": "knight", "xy_norm": [0.5, 0.5], "region": "nowhere"}
        ]
        data["production_doc"]["layout"] = layout
        errors = validate_production(data)
        self.assertTrue(any("unknown region 'nowhere'" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
