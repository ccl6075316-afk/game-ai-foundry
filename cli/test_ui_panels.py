"""Tests for optional project.ui_panels brief contract."""

from __future__ import annotations

import copy
import unittest

from brief import (
    AssetSpec,
    AssetType,
    ProjectContext,
    audit_brief_for_export,
    finalize_brief_export,
    normalize_ui_panels,
    validate_brief_for_export,
)
from display_size import DisplaySize
from shared_context import project_to_dict
from test_fixtures import GAMEPLAY_PROJECT, SMOKE_BRIEF


def _minimal_valid_asset() -> AssetSpec:
    return AssetSpec(
        name="slime_hero",
        id="slime_hero",
        type=AssetType.CHARACTER,
        usage="player_idle",
        usage_description="hero",
        display_size=DisplaySize(128, 128),
        description="hero",
    )


def _minimal_valid_project(**extra: object) -> ProjectContext:
    base = {
        "title": "T",
        "description": "game",
        "art_direction": "art",
        "dimension": "2d",
        **GAMEPLAY_PROJECT,
        **extra,
    }
    return ProjectContext.from_dict(base)


class NormalizeUiPanelsTests(unittest.TestCase):
    def test_default_empty(self) -> None:
        self.assertEqual(normalize_ui_panels(None), [])
        self.assertEqual(normalize_ui_panels([]), [])
        self.assertEqual(normalize_ui_panels("bad"), [])

    def test_drops_entries_missing_id_or_title(self) -> None:
        raw = [
            {"id": "ok", "title": "OK"},
            {"id": "", "title": "No id"},
            {"title": "No id key"},
            {"id": "no_title"},
            {"id": "  ", "title": "spaces"},
            "not a dict",
        ]
        out = normalize_ui_panels(raw)
        self.assertEqual(out, [{"id": "ok", "title": "OK"}])

    def test_preserves_optional_fields(self) -> None:
        raw = [
            {
                "id": "equip_panel",
                "title": "装备面板",
                "kind": "inventory",
                "anchor": "center",
                "slots": ["武器槽", "", "防具槽"],
                "notes": "暂停时打开",
            }
        ]
        out = normalize_ui_panels(raw)
        self.assertEqual(
            out,
            [
                {
                    "id": "equip_panel",
                    "title": "装备面板",
                    "kind": "inventory",
                    "anchor": "center",
                    "slots": ["武器槽", "防具槽"],
                    "notes": "暂停时打开",
                }
            ],
        )


class ProjectContextUiPanelsTests(unittest.TestCase):
    def test_from_dict_default_empty(self) -> None:
        project = ProjectContext.from_dict({"title": "T"})
        self.assertEqual(project.ui_panels, [])

    def test_round_trip_from_dict(self) -> None:
        panels = [
            {
                "id": "menu",
                "title": "主菜单",
                "kind": "menu",
                "anchor": "center",
                "slots": ["开始"],
                "notes": "首屏",
            }
        ]
        project = _minimal_valid_project(ui_panels=panels)
        self.assertEqual(len(project.ui_panels), 1)
        self.assertEqual(project.ui_panels[0]["id"], "menu")
        self.assertEqual(project.ui_panels[0]["slots"], ["开始"])

    def test_project_to_dict_includes_ui_panels_when_present(self) -> None:
        project = _minimal_valid_project(
            ui_panels=[{"id": "hud", "title": "HUD", "kind": "hud"}]
        )
        out = project_to_dict(project)
        self.assertIn("ui_panels", out)
        self.assertEqual(out["ui_panels"][0]["id"], "hud")

    def test_project_to_dict_omits_empty_ui_panels(self) -> None:
        project = _minimal_valid_project()
        out = project_to_dict(project)
        self.assertNotIn("ui_panels", out)


class ValidateUiPanelsTests(unittest.TestCase):
    def test_validate_passes_without_ui_panels(self) -> None:
        project = _minimal_valid_project()
        asset = _minimal_valid_asset()
        gaps = audit_brief_for_export(project, [asset])
        self.assertFalse(any("ui_panels" in g for g in gaps))
        validate_brief_for_export(project, [asset])

    def test_validate_passes_with_ui_panels(self) -> None:
        project = _minimal_valid_project(
            ui_panels=[{"id": "map", "title": "地图"}]
        )
        asset = _minimal_valid_asset()
        gaps = audit_brief_for_export(project, [asset])
        self.assertFalse(any("ui_panels" in g for g in gaps))
        validate_brief_for_export(project, [asset])

    def test_finalize_export_includes_ui_panels(self) -> None:
        brief = copy.deepcopy(SMOKE_BRIEF)
        brief["project"]["ui_panels"] = [
            {"id": "equip_panel", "title": "装备面板", "kind": "inventory"}
        ]
        out = finalize_brief_export(brief, source="test")
        self.assertIn("ui_panels", out["project"])
        self.assertEqual(out["project"]["ui_panels"][0]["id"], "equip_panel")


if __name__ == "__main__":
    unittest.main()
