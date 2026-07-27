"""Tests for profile-aware assemble_asset_prompt behavior."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from media_prompt_profile import (
    GEMINI_IMAGE,
    GPT_IMAGE,
    PromptCapabilityProfile,
    resolve_media_prompt_profile,
)
from prompt_craft import assemble_asset_prompt, craft_asset_prompt


def _fields() -> dict[str, str]:
    return {
        "subject": "iron sword on white",
        "silhouette": "clear blade shape",
        "style_lock": "warm earth palette",
        "view": "side profile",
        "technical": "pure flat white background",
        "negatives": "no blur; no watermark",
    }


def _project() -> dict:
    return {"title": "Test", "art_direction": "cozy flat"}


def _spec() -> dict:
    return {
        "name": "sword",
        "type": "weapon",
        "description": "iron sword",
        "content_class": "weapon",
    }


class AssembleAssetPromptProfileTests(unittest.TestCase):
    def test_gpt_image_profile_emits_negatives_section(self) -> None:
        prompt = assemble_asset_prompt(
            _fields(),
            project=_project(),
            spec=_spec(),
            profile=GPT_IMAGE,
        )
        self.assertIn("Negatives:", prompt)
        self.assertNotIn("Avoid:", prompt)

    def test_gemini_image_profile_merges_negatives_into_style_lock(self) -> None:
        prompt = assemble_asset_prompt(
            _fields(),
            project=_project(),
            spec=_spec(),
            profile=GEMINI_IMAGE,
        )
        self.assertNotIn("Negatives:", prompt)
        self.assertIn("Style lock:", prompt)
        self.assertIn("Avoid:", prompt)
        self.assertIn("no blur", prompt)

    def test_default_profile_matches_resolve_empty_model(self) -> None:
        expected = resolve_media_prompt_profile("", modality="image")
        prompt_default = assemble_asset_prompt(
            _fields(),
            project=_project(),
            spec=_spec(),
        )
        prompt_explicit = assemble_asset_prompt(
            _fields(),
            project=_project(),
            spec=_spec(),
            profile=expected,
        )
        self.assertEqual(prompt_default, prompt_explicit)
        self.assertNotIn("Negatives:", prompt_default)

    def test_prefer_soft_style_appends_alignment_once(self) -> None:
        prompt = assemble_asset_prompt(
            _fields(),
            project=_project(),
            spec=_spec(),
            profile=GEMINI_IMAGE,
        )
        self.assertIn("Soft style alignment with art direction", prompt)
        self.assertEqual(
            prompt.count("Soft style alignment with art direction"),
            1,
        )

    def test_tags_dialect_flattens_to_comma_separated_line(self) -> None:
        tags_profile = PromptCapabilityProfile(
            profile_id="fake_tags",
            prompt_dialect="tags",
            negatives_effective=True,
            prefer_soft_style=False,
            modality="image",
        )
        prompt = assemble_asset_prompt(
            _fields(),
            project=_project(),
            spec=_spec(),
            profile=tags_profile,
        )
        self.assertNotIn("Subject:", prompt)
        self.assertNotIn("\n", prompt)
        self.assertIn("iron sword on white", prompt)
        self.assertIn("no blur", prompt)
        parts = [p.strip() for p in prompt.split(",")]
        self.assertGreater(len(parts), 3)


class CraftAssetPromptProfileBindingTests(unittest.TestCase):
    @patch("prompt_craft.chat_text_completion")
    def test_structured_craft_binds_gemini_image_profile(self, chat: object) -> None:
        chat.return_value = """{
          "subject": "iron sword on white",
          "silhouette": "clear blade shape",
          "style_lock": "warm earth palette",
          "view": "side profile",
          "technical": "pure flat white background",
          "negatives": "no blur; no watermark"
        }"""
        config = {"image": {"model": "google/gemini-2.5-flash-image-preview"}}
        out = craft_asset_prompt(
            context={
                "project": _project(),
                "asset": _spec(),
            },
            model="test-llm",
            api_key="k",
            api_base="https://example.com/v1",
            config=config,
        )
        self.assertEqual(out["prompt_source"], "llm_structured")
        self.assertEqual(out["image_model"], "google/gemini-2.5-flash-image-preview")
        self.assertEqual(out["prompt_profile_id"], "gemini_image")
        self.assertNotIn("Negatives:", out["prompt"])
        self.assertIn("Avoid:", out["prompt"])

    @patch("prompt_craft.chat_text_completion")
    def test_structured_craft_without_config_uses_default_profile(self, chat: object) -> None:
        chat.return_value = """{
          "subject": "wooden crate",
          "technical": "white background"
        }"""
        out = craft_asset_prompt(
            context={
                "project": _project(),
                "asset": _spec(),
            },
            model="test-llm",
            api_key="k",
            api_base="https://example.com/v1",
        )
        self.assertEqual(out["prompt_profile_id"], "default")
        self.assertNotIn("image_model", out)


class CraftAnimationVideoPromptProfileTests(unittest.TestCase):
    @patch("prompt_craft.chat_text_completion")
    def test_animation_video_prompt_postprocessed_for_seedance(self, chat: object) -> None:
        chat.return_value = """{
          "subject": "hero character",
          "video_prompt": "Smooth walk cycle to the right.\\n\\nNegatives: blur"
        }"""
        out = craft_asset_prompt(
            context={
                "project": _project(),
                "asset": {
                    "name": "hero_walk",
                    "type": "character",
                    "description": "hero",
                    "video_model": "doubao-seedance-2-0-260128",
                    "content_class": "character",
                },
            },
            model="test",
            api_key="k",
            api_base="https://example.com/v1",
            kind="animation",
        )
        video_prompt = out["video_prompt"]
        self.assertNotIn("Negatives:", video_prompt)
        self.assertIn("Avoid:", video_prompt)
        self.assertIn("Soft style alignment with art direction", video_prompt)
        self.assertEqual(out["video_model"], "doubao-seedance-2-0-260128")


if __name__ == "__main__":
    unittest.main()
