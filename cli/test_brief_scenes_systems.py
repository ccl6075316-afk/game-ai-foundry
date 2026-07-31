"""Tests for optional project.scenes / systems and asset scene_ids / system_ids."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from agent_turn import build_prompt, new_session
from brief import (
    AssetSpec,
    ProjectContext,
    audit_brief_for_export,
    finalize_brief_export,
    normalize_id_list,
    normalize_scenes,
    normalize_systems,
    validate_brief_for_export,
)
from shared_context import asset_to_dict, project_to_dict
from test_fixtures import GAMEPLAY_PROJECT, SMOKE_BRIEF


def _minimal_valid_asset(**extra: object) -> AssetSpec:
    data = {
        "name": "slime_hero",
        "id": "slime_hero",
        "type": "character",
        "usage": "player_idle",
        "usage_description": "hero",
        "display_size": {"width": 128, "height": 128},
        "description": "hero",
        **extra,
    }
    return AssetSpec.from_dict(data)


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


class NormalizeScenesSystemsTests(unittest.TestCase):
    def test_default_empty(self) -> None:
        self.assertEqual(normalize_scenes(None), [])
        self.assertEqual(normalize_systems([]), [])
        self.assertEqual(normalize_scenes("bad"), [])
        self.assertEqual(normalize_id_list(None), [])

    def test_scenes_drops_missing_id_or_title(self) -> None:
        raw = [
            {"id": "dock", "title": "钓场"},
            {"id": "", "title": "No id"},
            {"title": "No id key"},
            {"id": "no_title"},
            "x",
        ]
        self.assertEqual(normalize_scenes(raw), [{"id": "dock", "title": "钓场"}])

    def test_scenes_optional_fields(self) -> None:
        out = normalize_scenes(
            [
                {
                    "id": "combat",
                    "title": "搏鱼",
                    "summary": "Cast and fight.",
                    "ui_panel_ids": ["sell", "", "sell", "hud"],
                    "notes": "main loop screen",
                }
            ]
        )
        self.assertEqual(
            out,
            [
                {
                    "id": "combat",
                    "title": "搏鱼",
                    "summary": "Cast and fight.",
                    "ui_panel_ids": ["sell", "hud"],
                    "notes": "main loop screen",
                }
            ],
        )

    def test_systems_optional_fields(self) -> None:
        out = normalize_systems(
            [
                {
                    "id": "economy",
                    "title": "经济",
                    "summary": "Ticket and sell prices.",
                    "notes": "tune in prototype",
                }
            ]
        )
        self.assertEqual(out[0]["id"], "economy")
        self.assertEqual(out[0]["summary"], "Ticket and sell prices.")


class ProjectContextScenesSystemsTests(unittest.TestCase):
    def test_from_dict_default_empty(self) -> None:
        project = ProjectContext.from_dict({"title": "T"})
        self.assertEqual(project.scenes, [])
        self.assertEqual(project.systems, [])

    def test_round_trip(self) -> None:
        project = _minimal_valid_project(
            scenes=[{"id": "shop", "title": "商店", "summary": "Buy gear."}],
            systems=[{"id": "time_pool", "title": "时间池"}],
        )
        self.assertEqual(project.scenes[0]["id"], "shop")
        self.assertEqual(project.systems[0]["id"], "time_pool")

    def test_project_to_dict_includes_when_present(self) -> None:
        project = _minimal_valid_project(
            scenes=[{"id": "a", "title": "A"}],
            systems=[{"id": "b", "title": "B"}],
        )
        out = project_to_dict(project)
        self.assertEqual(out["scenes"][0]["id"], "a")
        self.assertEqual(out["systems"][0]["id"], "b")

    def test_project_to_dict_omits_empty(self) -> None:
        out = project_to_dict(_minimal_valid_project())
        self.assertNotIn("scenes", out)
        self.assertNotIn("systems", out)


class AssetSceneSystemIdsTests(unittest.TestCase):
    def test_asset_optional_ids(self) -> None:
        asset = _minimal_valid_asset(
            scene_ids=["combat", "aquarium", "combat"],
            system_ids=["encyclopedia"],
        )
        self.assertEqual(asset.scene_ids, ["combat", "aquarium"])
        self.assertEqual(asset.system_ids, ["encyclopedia"])
        data = asset_to_dict(asset)
        self.assertEqual(data["scene_ids"], ["combat", "aquarium"])
        self.assertEqual(data["system_ids"], ["encyclopedia"])

    def test_asset_to_dict_omits_empty_ids(self) -> None:
        data = asset_to_dict(_minimal_valid_asset())
        self.assertNotIn("scene_ids", data)
        self.assertNotIn("system_ids", data)


class ValidateScenesSystemsTests(unittest.TestCase):
    def test_validate_passes_without(self) -> None:
        project = _minimal_valid_project()
        asset = _minimal_valid_asset()
        gaps = audit_brief_for_export(project, [asset])
        self.assertFalse(any("scenes" in g or "systems" in g for g in gaps))
        validate_brief_for_export(project, [asset])

    def test_validate_passes_with(self) -> None:
        project = _minimal_valid_project(
            scenes=[{"id": "main", "title": "主界面"}],
            systems=[{"id": "eco", "title": "经济"}],
        )
        asset = _minimal_valid_asset(scene_ids=["main"], system_ids=["eco"])
        validate_brief_for_export(project, [asset])

    def test_finalize_export_includes(self) -> None:
        brief = copy.deepcopy(SMOKE_BRIEF)
        brief["project"]["scenes"] = [{"id": "dock", "title": "码头"}]
        brief["project"]["systems"] = [{"id": "day", "title": "日循环"}]
        brief["assets"][0]["scene_ids"] = ["dock"]
        out = finalize_brief_export(brief, source="test")
        self.assertEqual(out["project"]["scenes"][0]["id"], "dock")
        self.assertEqual(out["project"]["systems"][0]["id"], "day")
        self.assertEqual(out["assets"][0]["scene_ids"], ["dock"])


class SoftHintScenesSystemsTests(unittest.TestCase):
    def test_build_prompt_scenes_systems_soft_hint(self) -> None:
        session = new_session("programmer", "ss1")
        payload = {
            "project": {
                "scenes": [{"id": "fishing_combat", "title": "搏鱼"}],
                "systems": [{"id": "economy", "title": "经济"}],
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.json"
            brief.write_text(json.dumps(payload), encoding="utf-8")
            prompt = build_prompt(
                role_kind="programmer",
                user_message="实现日结",
                session=session,
                brief_path=brief,
            )
            self.assertIn("场景与逻辑系统", prompt)
            self.assertIn("fishing_combat", prompt)
            self.assertIn("economy", prompt)
        with tempfile.TemporaryDirectory() as tmp2:
            brief_only = Path(tmp2) / "brief.json"
            brief_only.write_text("{}", encoding="utf-8")
            prompt_empty = build_prompt(
                role_kind="programmer",
                user_message="实现日结",
                session=session,
                brief_path=brief_only,
            )
            self.assertNotIn("场景与逻辑系统", prompt_empty)


if __name__ == "__main__":
    unittest.main()
