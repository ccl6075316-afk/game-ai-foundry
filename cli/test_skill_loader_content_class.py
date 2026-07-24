"""Tests for content-class prompt skill loader routing."""

from __future__ import annotations

import unittest

from skill_loader import load_prompt_skills_for_asset, resolve_class_skill_name


class ResolveClassSkillNameTests(unittest.TestCase):
    def test_floor_tile_content_class(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"content_class": "floor_tile"}),
            "class-tiles",
        )

    def test_backdrop_sparse_content_class(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"content_class": "backdrop_sparse"}),
            "class-backdrops",
        )

    def test_weapon_content_class(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"content_class": "weapon"}),
            "class-props",
        )

    def test_character_type_fallback(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"type": "character"}),
            "class-character",
        )

    def test_player_usage_fallback(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"usage": "player_idle"}),
            "class-character",
        )

    def test_tile_texture_usage_fallback(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"usage": "tile_texture", "type": "texture"}),
            "class-tiles",
        )

    def test_ui_element_fallback(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"usage": "ui_element", "type": "character"}),
            "class-ui",
        )

    def test_icon_kit_type_fallback(self) -> None:
        self.assertEqual(
            resolve_class_skill_name({"type": "icon_kit"}),
            "class-ui",
        )


class LoadPromptSkillsForAssetTests(unittest.TestCase):
    def test_always_includes_shared_locks_and_planner(self) -> None:
        text = load_prompt_skills_for_asset({"content_class": "floor_tile"})
        self.assertIn("# Shared locks (all asset classes)", text)
        self.assertIn("# Asset Planner (prompt-crafter role only)", text)

    def test_tile_loads_tiles_class_not_character(self) -> None:
        text = load_prompt_skills_for_asset({"content_class": "floor_tile"})
        self.assertIn("# Class: tiles", text)
        self.assertNotIn("# Class: character", text)

    def test_character_loads_character_class(self) -> None:
        text = load_prompt_skills_for_asset({"type": "character", "usage": "player_idle"})
        self.assertIn("# Class: character", text)
        self.assertIn("mattable still", text.lower())

    def test_backdrop_sparse_loads_backdrops_class(self) -> None:
        text = load_prompt_skills_for_asset({"content_class": "backdrop_sparse"})
        self.assertIn("# Class: backdrops", text)
        self.assertIn("backdrop_sparse", text)

    def test_prop_and_tile_system_text_differs(self) -> None:
        tile_text = load_prompt_skills_for_asset({"content_class": "floor_tile"})
        prop_text = load_prompt_skills_for_asset({"content_class": "prop_static"})
        self.assertIn("Seamless tileable", tile_text)
        self.assertIn("prop_interactable", prop_text)
        self.assertNotEqual(tile_text, prop_text)


if __name__ == "__main__":
    unittest.main()
