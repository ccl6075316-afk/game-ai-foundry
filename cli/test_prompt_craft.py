"""CJK assemble guards for prompt craft."""

from __future__ import annotations

import unittest

from prompt_craft import PromptCraftError, assemble_asset_prompt, contains_cjk


class CjkAssembleGuardTests(unittest.TestCase):
    def test_contains_cjk(self):
        self.assertTrue(contains_cjk("红色小船"))
        self.assertFalse(contains_cjk("red boat"))

    def test_assemble_rejects_cjk_description_fallback(self):
        project = {"view": "side", "art_direction": "像素风"}
        spec = {"description": "码头上的红色小船", "type": "character"}
        with self.assertRaises(PromptCraftError):
            assemble_asset_prompt({}, project=project, spec=spec)

    def test_assemble_accepts_english_subject(self):
        project = {"view": "side"}
        spec = {"description": "码头上的红色小船", "type": "character"}
        prompt = assemble_asset_prompt(
            {"subject": "A small red boat at a wooden pier"},
            project=project,
            spec=spec,
        )
        self.assertIn("red boat", prompt.lower())


if __name__ == "__main__":
    unittest.main()
