"""Tests for project.art_tokens brief field."""

from __future__ import annotations

import unittest

from brief import (
    AssetSpec,
    ProjectContext,
    audit_art_tokens,
    audit_brief_for_export,
    normalize_art_tokens,
)
from shared_context import build_role_context, project_to_dict


def _valid_project(**overrides: object) -> ProjectContext:
    base = {
        "title": "Art Tokens Test",
        "description": "platformer test",
        "art_direction": "flat 2D",
        "dimension": "2d",
        "genre": "2d_platformer",
        "gameplay_loop": "run and jump",
        "session_goal": "demo",
        "player_asset": "hero_a",
        "controls": {"move_left": ["A"], "move_right": ["D"]},
        "viewport": {"width": 640, "height": 360},
        "camera": {"mode": "follow_player"},
    }
    base.update(overrides)
    return ProjectContext.from_dict(base)


def _minimal_asset() -> AssetSpec:
    return AssetSpec.from_dict(
        {
            "name": "hero_a",
            "id": "hero_a",
            "type": "character",
            "usage": "player_idle",
            "usage_description": "hero",
            "description": "hero",
            "display_size": {"width": 128, "height": 128},
        }
    )


class ArtTokensTests(unittest.TestCase):
    def test_absent_is_none_and_omitted_from_dict(self) -> None:
        project = _valid_project()
        self.assertIsNone(project.art_tokens)
        self.assertNotIn("art_tokens", project_to_dict(project))
        self.assertEqual(audit_art_tokens(project), [])

    def test_absent_audit_clean_for_minimal_brief(self) -> None:
        project = _valid_project()
        asset = _minimal_asset()
        errors = audit_brief_for_export(project, [asset])
        self.assertFalse(any("art_tokens" in e for e in errors))

    def test_palette_string_array_round_trip(self) -> None:
        tokens = {
            "line": "bold outline",
            "palette": ["#112233", " #AABBCC ", ""],
            "forbid": ["photorealistic"],
        }
        project = _valid_project(art_tokens=tokens)
        self.assertEqual(project.art_tokens["palette"], ["#112233", "#AABBCC"])
        out = project_to_dict(project)
        self.assertEqual(out["art_tokens"]["palette"], ["#112233", "#AABBCC"])
        reparsed = ProjectContext.from_dict(out)
        self.assertEqual(reparsed.art_tokens, project.art_tokens)

    def test_palette_string_ok(self) -> None:
        project = _valid_project(art_tokens={"palette": " warm earth tones "})
        self.assertEqual(project.art_tokens, {"palette": "warm earth tones"})
        self.assertEqual(
            project_to_dict(project)["art_tokens"]["palette"],
            "warm earth tones",
        )

    def test_forbid_non_list_audit_error(self) -> None:
        project = _valid_project(art_tokens={"forbid": "no blur"})
        errors = audit_art_tokens(project)
        self.assertTrue(any("forbid must be a list" in e for e in errors))
        self.assertNotIn("forbid", project.art_tokens or {})

    def test_art_tokens_string_audit_error(self) -> None:
        project = _valid_project(art_tokens="not-an-object")
        self.assertIsNone(project.art_tokens)
        errors = audit_art_tokens(project)
        self.assertEqual(errors, ["project.art_tokens must be an object"])

    def test_unknown_key_preserved_in_project_to_dict(self) -> None:
        project = _valid_project(
            art_tokens={
                "line": "clean vector",
                "mood": "cozy",
            }
        )
        out = project_to_dict(project)
        self.assertEqual(out["art_tokens"]["mood"], "cozy")
        self.assertEqual(out["art_tokens"]["line"], "clean vector")

    def test_build_role_context_includes_art_tokens(self) -> None:
        project = _valid_project(
            art_tokens={
                "line": "2px black outline",
                "silhouette": "readable at 32px",
            }
        )
        spec = _minimal_asset()
        ctx = build_role_context(project, spec)
        self.assertIn("art_tokens", ctx["project"])
        self.assertEqual(ctx["project"]["art_tokens"]["line"], "2px black outline")

    def test_normalize_empty_dict_returns_none(self) -> None:
        tokens, errors = normalize_art_tokens({})
        self.assertIsNone(tokens)
        self.assertEqual(errors, [])

    def test_from_dict_without_art_tokens_still_works(self) -> None:
        project = ProjectContext.from_dict(
            {
                "title": "Legacy",
                "description": "old brief",
                "art_direction": "pixel",
                "dimension": "2d",
            }
        )
        self.assertIsNone(project.art_tokens)
        self.assertEqual(project.title, "Legacy")


if __name__ == "__main__":
    unittest.main()
