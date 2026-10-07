"""Tests for production.layout → Godot scene fragments."""

from __future__ import annotations

import unittest

from godot_layout import (
    build_layout_world_fragments,
    prop_texture_res_path,
    sanitize_prop_node_name,
    scene_layer_runtime_scale,
    xy_norm_to_pixels,
)


class GodotLayoutTest(unittest.TestCase):
    def test_xy_norm_to_pixels(self) -> None:
        self.assertEqual(xy_norm_to_pixels([0.5, 0.5], {"width": 1280, "height": 720}), (640, 360))
        self.assertEqual(xy_norm_to_pixels([0.2, 0.475], {"width": 1280, "height": 720}), (256, 342))

    def test_build_fragments_parents_under_world(self) -> None:
        layout = {
            "coord_space": "viewport_norm",
            "regions": [],
            "placements": [
                {"asset": "wooden_crate", "xy_norm": [0.2, 0.475], "region": "playable"},
                {"asset": "mossy_rock", "xy_norm": [0.8, 0.475], "region": "playable"},
            ],
        }
        ext, nodes, next_id = build_layout_world_fragments(
            layout,
            {"width": 1280, "height": 720},
            ext_id_start=10,
        )
        self.assertEqual(len(ext), 2)
        self.assertIn('path="res://assets/props/wooden_crate_nobg.png"', ext[0])
        joined = "\n".join(nodes)
        self.assertIn('[node name="WoodenCrate" type="Sprite2D" parent="World"]', joined)
        self.assertIn("position = Vector2(256, 342)", joined)
        self.assertIn('[node name="MossyRock" type="Sprite2D" parent="World"]', joined)
        self.assertEqual(next_id, 12)

    def test_build_fragments_with_scale(self) -> None:
        layout = {
            "placements": [
                {"asset": "crate", "xy_norm": [0.5, 0.5], "scale": 0.5},
            ],
        }
        _, nodes, _ = build_layout_world_fragments(
            layout,
            {"width": 1280, "height": 720},
            ext_id_start=10,
        )
        joined = "\n".join(nodes)
        self.assertIn("scale = Vector2(0.5, 0.5)", joined)

    def test_scene_layer_source_pixels_are_scaled_at_runtime(self) -> None:
        self.assertEqual(
            scene_layer_runtime_scale((1536, 512), (1920, 540), 1.0, opaque=True),
            (1.25, 1.0546875),
        )
        self.assertEqual(
            scene_layer_runtime_scale((1024, 512), (768, 270), 1.0, opaque=False),
            (0.52734375, 0.52734375),
        )
        layout = {
            "placements": [
                {"asset": "water", "xy_norm": [0.5, 0.75],
                 "scale": 1.0, "scale_xy": [1.25, 1.0546875], "z_index": 2},
            ],
        }
        _, nodes, _ = build_layout_world_fragments(layout, {"width": 1920, "height": 1080})
        self.assertIn("scale = Vector2(1.25, 1.0546875)", "\n".join(nodes))
        self.assertIn("z_index = 2", "\n".join(nodes))

    def test_sanitize_and_res_path(self) -> None:
        self.assertEqual(sanitize_prop_node_name("wooden_crate"), "WoodenCrate")
        self.assertEqual(prop_texture_res_path("wooden_crate"), "assets/props/wooden_crate_nobg.png")


if __name__ == "__main__":
    unittest.main()
