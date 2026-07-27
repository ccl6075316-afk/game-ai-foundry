"""Tests for media model → PromptCapabilityProfile resolution."""

from __future__ import annotations

import unittest

from media_prompt_profile import (
    PromptCapabilityProfile,
    VOLC_VIDEO,
    apply_video_prompt_profile,
    normalize_media_model_id,
    resolve_media_prompt_profile,
)


class NormalizeMediaModelIdTests(unittest.TestCase):
    def test_lowercase_and_collapse_spaces(self) -> None:
        self.assertEqual(normalize_media_model_id("  OpenAI/GPT-Image-2  "), "openai/gpt-image-2")

    def test_weird_strings_never_raise(self) -> None:
        for raw in ("", "   ", "\t\n", "!!!", "🎨"):
            self.assertIsInstance(normalize_media_model_id(raw), str)


class ResolveMediaPromptProfileTests(unittest.TestCase):
    def test_gpt_image(self) -> None:
        profile = resolve_media_prompt_profile("openai/gpt-image-2", modality="image")
        self.assertEqual(profile.profile_id, "gpt_image")
        self.assertEqual(profile.modality, "image")
        self.assertEqual(profile.prompt_dialect, "natural")
        self.assertTrue(profile.negatives_effective)
        self.assertTrue(profile.prefer_soft_style)

    def test_gptimage_alias(self) -> None:
        profile = resolve_media_prompt_profile("gptimage-1", modality="image")
        self.assertEqual(profile.profile_id, "gpt_image")

    def test_gemini_image(self) -> None:
        profile = resolve_media_prompt_profile(
            "google/gemini-3.1-flash-image",
            modality="image",
        )
        self.assertEqual(profile.profile_id, "gemini_image")
        self.assertFalse(profile.negatives_effective)
        self.assertTrue(profile.prefer_soft_style)

    def test_volc_image(self) -> None:
        profile = resolve_media_prompt_profile("doubao-seedream-4.0", modality="image")
        self.assertEqual(profile.profile_id, "volc_image")
        self.assertTrue(profile.negatives_effective)

    def test_volc_video(self) -> None:
        profile = resolve_media_prompt_profile(
            "doubao-seedance-2-0-260128",
            modality="video",
        )
        self.assertEqual(profile.profile_id, "volc_video")
        self.assertFalse(profile.negatives_effective)

    def test_grok_imagine(self) -> None:
        profile = resolve_media_prompt_profile("grok-imagine", modality="image")
        self.assertEqual(profile.profile_id, "grok_image")

    def test_xai_grok_prefix(self) -> None:
        profile = resolve_media_prompt_profile("xai/grok-vision-beta", modality="image")
        self.assertEqual(profile.profile_id, "grok_image")

    def test_grok_not_used_for_video(self) -> None:
        profile = resolve_media_prompt_profile("grok-imagine", modality="video")
        self.assertEqual(profile.profile_id, "default")

    def test_unknown_defaults(self) -> None:
        profile = resolve_media_prompt_profile("some-random-model", modality="image")
        self.assertEqual(profile.profile_id, "default")
        self.assertEqual(profile.modality, "image")
        self.assertFalse(profile.negatives_effective)
        self.assertTrue(profile.prefer_soft_style)

    def test_seedance_with_image_modality_falls_to_default(self) -> None:
        profile = resolve_media_prompt_profile("doubao-seedance-2-0-260128", modality="image")
        self.assertEqual(profile.profile_id, "default")

    def test_weird_strings_never_raise(self) -> None:
        for raw in ("", "   ", "!!!", "🎨"):
            for modality in ("image", "video"):
                profile = resolve_media_prompt_profile(raw, modality=modality)  # type: ignore[arg-type]
                self.assertIsInstance(profile, PromptCapabilityProfile)
                self.assertEqual(profile.profile_id, "default")
                self.assertEqual(profile.modality, modality)

    def test_no_seed_profile_id(self) -> None:
        for model, modality in (
            ("doubao-seedream-4.0", "image"),
            ("doubao-seedance-2-0-260128", "video"),
        ):
            profile = resolve_media_prompt_profile(model, modality=modality)  # type: ignore[arg-type]
            self.assertNotIn("seed", profile.profile_id)


class ApplyVideoPromptProfileTests(unittest.TestCase):
    def test_volc_video_folds_negatives_into_avoid_and_adds_soft_style(self) -> None:
        raw = "Smooth walk cycle to the right.\n\nNegatives: blur"
        out = apply_video_prompt_profile(raw, VOLC_VIDEO)
        self.assertNotIn("Negatives:", out)
        self.assertIn("Avoid:", out)
        self.assertIn("blur", out)
        self.assertIn("Soft style alignment with art direction", out)
        self.assertEqual(out.count("Soft style alignment with art direction"), 1)

    def test_seedance_model_resolves_volc_video_profile(self) -> None:
        profile = resolve_media_prompt_profile(
            "doubao-seedance-2-0-260128",
            modality="video",
        )
        self.assertEqual(profile.profile_id, "volc_video")


if __name__ == "__main__":
    unittest.main()
