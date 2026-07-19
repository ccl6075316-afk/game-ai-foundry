"""Tests for Visual Target structured prompt assemble / VT-only system."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from prompt_craft import (
    assemble_visual_target_prompt,
    craft_visual_target_prompt,
    structured_fields_from_project_scaffold,
    _system_prompt_visual_target,
)


class FakeProject:
    title = "Black Whistle"
    description = "Referee moral choices."
    art_direction = "Chibi TV broadcast, Overcooked scale"
    dimension = "2d"
    genre = "sports sim"
    gameplay_loop = "Watch match, resolve foul QTE"
    session_goal = "Survive one match"
    player_asset = "裁判"
    camera = {"mode": "broadcast", "scope": "pitch"}
    hud = [{"asset": "decision_wheel", "anchor": "top_right"}]
    viewport = {"width": 1280, "height": 720}


class VisualTargetPromptCraftTests(unittest.TestCase):
    def test_system_excludes_asset_studio_rules(self) -> None:
        text = _system_prompt_visual_target().lower()
        self.assertIn("visual target", text)
        self.assertIn("gameplay screenshot", text)
        # Must NOT load asset-planner / asset-gen character-sheet rules
        self.assertNotIn("facing right", text)
        self.assertNotIn("require_pure_white_background", text)
        self.assertNotIn("sprite sheet", text)
        self.assertNotIn("asset-planner", text)
        self.assertIn("use_case", text)

    def test_assemble_order_wide_to_narrow(self) -> None:
        prompt = assemble_visual_target_prompt(
            {
                "use_case": "in-engine gameplay screenshot",
                "scene": "green pitch",
                "hero": "referee 18% height",
                "gameplay_beat": "raising yellow card",
                "details": "high broadcast camera",
                "hud": "decision wheel top-right",
                "style_lock": "chibi flat shading",
                "constraints": "no watermark",
            }
        )
        labels = [
            "Use case:",
            "Scene:",
            "Subject:",
            "Gameplay beat:",
            "Important details:",
            "HUD:",
            "Style lock:",
            "Constraints:",
        ]
        positions = [prompt.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("gameplay screenshot", prompt.lower())
        self.assertIn("referee", prompt.lower())

    def test_scaffold_fields_include_player(self) -> None:
        fields = structured_fields_from_project_scaffold(
            FakeProject(),
            {"id": "b", "label": "action_beat", "focus": "Foul decision beat."},
        )
        prompt = assemble_visual_target_prompt(fields)
        self.assertIn("裁判", prompt)
        self.assertIn("Use case:", prompt)
        self.assertIn("screenshot", prompt.lower())

    @patch("prompt_craft.chat_text_completion")
    def test_craft_assembles_structured_json(self, chat: object) -> None:
        chat.return_value = """{
          "use_case": "in-engine gameplay screenshot",
          "scene": "pitch under lights",
          "hero": "referee with whistle",
          "gameplay_beat": "foul QTE",
          "details": "TV broadcast angle",
          "hud": "wheel",
          "style_lock": "chibi",
          "constraints": "no poster"
        }"""
        out = craft_visual_target_prompt(
            context={"project": {"player_asset": "裁判", "art_direction": "chibi"}},
            model="test",
            api_key="k",
            api_base="https://example.com/v1",
        )
        self.assertEqual(out["prompt_source"], "llm_structured")
        self.assertTrue(out["prompt"].startswith("Use case:"))
        self.assertIn("Gameplay beat:", out["prompt"])


if __name__ == "__main__":
    unittest.main()
