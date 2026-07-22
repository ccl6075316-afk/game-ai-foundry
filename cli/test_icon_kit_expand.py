"""icon_kit expands to per-item generates (no slice)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline_manifest import build_manifest


def _kit_brief(*, items, use_style_img2img=None):
    asset = {
        "name": "item_icons",
        "id": "item_icons",
        "type": "icon_kit",
        "usage": "item_icon",
        "usage_description": "Inventory icons",
        "generate_method": "image",
        "items": items,
        "grid": "2x2",
        "display_size": {"width": 64, "height": 64},
    }
    if use_style_img2img is not None:
        asset["use_style_img2img"] = use_style_img2img
    return {
        "project": {
            "title": "T",
            "genre": "platformer",
            "gameplay_loop": "loop",
            "description": "d",
            "art_direction": "pixel",
            "dimension": "2d",
            "session_goal": "demo",
            "controls": {"move": ["A", "D"], "jump": ["Space"]},
            "viewport": {"width": 1280, "height": 720},
        },
        "assets": [asset],
    }


class IconKitExpandTests(unittest.TestCase):
    def test_manifest_expands_items_no_slice(self) -> None:
        brief = _kit_brief(
            items=[
                "sword",
                {
                    "id": "health_potion",
                    "label": "red potion",
                    "usage": "pickup",
                    "usage_description": "heal pickup",
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            out = root / "output"
            plans = root / "plans"
            with patch(
                "gamefactory.load_config",
                return_value={"image": {"model": "main-m", "bulk_model": "cheap-m"}},
            ):
                manifest = build_manifest(
                    brief_path,
                    output_dir=out,
                    plans_dir=plans,
                    include_godot=False,
                    include_game_dev=False,
                )
        steps = [t["step"] for t in manifest["tasks"]]
        self.assertNotIn("image.slice", steps)
        gens = [t for t in manifest["tasks"] if t["step"] == "image.generate"]
        self.assertEqual(len(gens), 2)
        for g in gens:
            self.assertIn("--model cheap-m", g["command"])
        ids = {t["asset_id"] for t in gens}
        self.assertTrue(any("sword" in i for i in ids))
        self.assertTrue(any("health_potion" in i for i in ids))
        crafts = [t for t in manifest["tasks"] if t["step"] == "prompt.craft"]
        self.assertEqual(len(crafts), 2)
        self.assertTrue(any("--item" in t["command"] for t in crafts))
        potion = next(t for t in gens if "health_potion" in t["asset_id"])
        self.assertEqual(potion["artifacts"].get("kit_item_id"), "health_potion")
        self.assertEqual(potion["artifacts"].get("kit_item_usage"), "pickup")
        self.assertEqual(potion["artifacts"].get("kit_item"), "red potion")
        sword = next(t for t in gens if "sword" in t["asset_id"])
        self.assertNotIn("--reference-image", sword["command"])
        self.assertIn("--reference-image", potion["command"])
        self.assertTrue(any("sword" in d and "image.generate" in d for d in potion["depends_on"]))

    def test_kit_style_opt_out(self) -> None:
        brief = _kit_brief(items=["a", "b"], use_style_img2img=False)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            with patch(
                "gamefactory.load_config",
                return_value={"image": {"model": "m", "bulk_model": "c"}},
            ):
                manifest = build_manifest(
                    brief_path,
                    output_dir=root / "output",
                    plans_dir=root / "plans",
                    include_godot=False,
                    include_game_dev=False,
                )
        gens = [t for t in manifest["tasks"] if t["step"] == "image.generate"]
        self.assertEqual(len(gens), 2)
        for g in gens:
            self.assertNotIn("--reference-image", g["command"])

    def test_single_item_no_kit_style(self) -> None:
        brief = _kit_brief(items=["only"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            with patch(
                "gamefactory.load_config",
                return_value={"image": {"model": "m", "bulk_model": "c"}},
            ):
                manifest = build_manifest(
                    brief_path,
                    output_dir=root / "output",
                    plans_dir=root / "plans",
                    include_godot=False,
                    include_game_dev=False,
                )
        gens = [t for t in manifest["tasks"] if t["step"] == "image.generate"]
        self.assertEqual(len(gens), 1)
        self.assertNotIn("--reference-image", gens[0]["command"])


if __name__ == "__main__":
    unittest.main()
