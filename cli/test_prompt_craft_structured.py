"""Tests for structured asset prompt assemble / craft backward compat."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from prompt_craft import (
    append_hard_locks,
    assemble_asset_prompt,
    craft_asset_prompt,
)


def _project(
    *,
    view: str = "",
    art_tokens: dict | None = None,
) -> dict:
    data: dict = {"title": "Test", "art_direction": "cozy flat"}
    if view:
        data["view"] = view
    if art_tokens:
        data["art_tokens"] = art_tokens
    return data


def _spec(*, content_class: str = "", description: str = "wooden crate") -> dict:
    return {
        "name": "crate",
        "type": "character",
        "description": description,
        "content_class": content_class,
    }


class AssembleAssetPromptTests(unittest.TestCase):
    def test_art_tokens_merge_when_fields_omit_them(self) -> None:
        prompt = assemble_asset_prompt(
            {"subject": "iron sword on white"},
            project=_project(
                art_tokens={
                    "palette": ["#112233", "#AABBCC"],
                    "forbid": ["no blur", "no watermark"],
                    "line": "2px black outline",
                }
            ),
            spec=_spec(content_class="weapon"),
        )
        self.assertIn("Palette:", prompt)
        self.assertIn("#112233", prompt)
        self.assertIn("Line:", prompt)
        self.assertIn("no blur", prompt)
        self.assertIn("Style lock:", prompt)
        self.assertIn("Negatives:", prompt)

    def test_view_side_injects_side_view_language(self) -> None:
        prompt = assemble_asset_prompt(
            {"subject": "knight idle"},
            project=_project(view="side"),
            spec=_spec(content_class="prop_static"),
        )
        self.assertIn("View:", prompt)
        self.assertIn("Side view", prompt)
        self.assertIn("facing right", prompt.lower())

    def test_floor_tile_technical_is_seamless_not_white_studio(self) -> None:
        prompt = assemble_asset_prompt(
            {"subject": "grass ground patch"},
            project=_project(),
            spec=_spec(content_class="floor_tile"),
        )
        lower = prompt.lower()
        self.assertIn("seamless", lower)
        self.assertIn("tileable", lower)
        self.assertNotIn("pure flat white background", lower)

    def test_prop_static_gets_white_background_lock(self) -> None:
        prompt = assemble_asset_prompt(
            {"subject": "wooden barrel"},
            project=_project(),
            spec=_spec(content_class="prop_static"),
        )
        lower = prompt.lower()
        self.assertIn("technical:", lower)
        self.assertIn("pure flat white background", lower)
        self.assertIn("#ffffff", lower)

    def test_labeled_order_subject_before_technical(self) -> None:
        prompt = assemble_asset_prompt(
            {
                "subject": "crate",
                "technical": "custom note",
            },
            project=_project(),
            spec=_spec(content_class="prop_static"),
        )
        self.assertLess(prompt.index("Subject:"), prompt.index("Technical:"))


class AppendHardLocksTests(unittest.TestCase):
    def test_legacy_prompt_only_gets_hard_lock_tail(self) -> None:
        out = append_hard_locks(
            "A wooden crate centered.",
            _project(view="side", art_tokens={"forbid": ["no grid"]}),
            _spec(content_class="prop_static"),
        )
        self.assertIn("A wooden crate centered.", out)
        self.assertIn("Hard locks:", out)
        self.assertIn("Side view", out)
        self.assertIn("pure flat white background", out.lower())
        self.assertIn("no grid", out.lower())


class CraftAssetPromptStructuredTests(unittest.TestCase):
    @patch("prompt_craft.chat_text_completion")
    def test_structured_json_assembles_labeled_prompt(self, chat: object) -> None:
        chat.return_value = """{
          "subject": "stone floor tile",
          "silhouette": "flat readable pattern",
          "style_lock": "warm earth palette",
          "view": "top-down fill",
          "technical": "fills frame",
          "negatives": "no characters"
        }"""
        out = craft_asset_prompt(
            context={
                "project": _project(view="top_down"),
                "asset": _spec(content_class="floor_tile"),
            },
            model="test",
            api_key="k",
            api_base="https://example.com/v1",
        )
        self.assertEqual(out["prompt_source"], "llm_structured")
        self.assertTrue(out["prompt"].startswith("Subject:"))
        self.assertIn("seamless", out["prompt"].lower())
        self.assertIn("prompt_fields", out)

    @patch("prompt_craft.chat_text_completion")
    def test_legacy_prompt_only_still_works_with_hard_locks(self, chat: object) -> None:
        chat.return_value = '{"prompt": "Single wooden barrel, game prop."}'
        out = craft_asset_prompt(
            context={
                "project": _project(view="side"),
                "asset": _spec(content_class="prop_static"),
            },
            model="test",
            api_key="k",
            api_base="https://example.com/v1",
        )
        self.assertEqual(out["prompt_source"], "llm_prose")
        self.assertIn("Single wooden barrel", out["prompt"])
        self.assertIn("Hard locks:", out["prompt"])
        self.assertIn("pure flat white background", out["prompt"].lower())


if __name__ == "__main__":
    unittest.main()
