"""Tests for Brief enrich draft merge helpers (DraftMergeGuard) and enrich runner."""

from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from host_chat import (
    HostChatError,
    apply_draft_replacement,
    draft_fingerprint,
    merge_asset_proposals,
    new_session,
    run_brief_enrich,
    validate_enriched_draft,
)

_THIN_DRAFT = {
    "project": {
        "title": "River Cast",
        "genre": "fishing",
        "gameplay_loop": "Cast, wait, reel, sell.",
    },
    "assets": [{"name": "player_fisher", "type": "character"}],
}


def _gaps_mock() -> dict:
    return {
        "gaps": [
            {
                "area": "main_menu",
                "description": "No menu flow or button effects described",
                "priority": "high",
            },
            {
                "area": "hud",
                "description": "Bite tension bar placement unclear",
                "priority": "medium",
            },
        ]
    }


def _enrich_mock(*, title_suffix: str = " enriched") -> dict:
    return {
        "draft_brief": {
            "project": {
                "title": f"River Cast{title_suffix}",
                "genre": "fishing",
                "gameplay_loop": "Cast, wait, reel, sell.",
                "player_flow": {
                    "main_menu": ["Start", "Collection", "Settings"],
                    "hud": {"tension_bar": "bottom center during reel minigame"},
                },
                "parameters_needed": [
                    {"name": "bite_wait_sec", "meaning": "wait before bite", "shown_in": "debug overlay"},
                ],
            },
            "assets": [{"name": "player_fisher", "type": "character"}],
        },
        "asset_proposals": [
            {"name": "ui_tension_bar", "type": "ui", "usage_description": "Reel minigame HUD"},
        ],
        "summary": "补全了主菜单流程与张力条呈现位置。",
    }


class DraftMergeGuardTests(unittest.TestCase):
    def test_validate_enriched_draft_requires_project_dict(self) -> None:
        with self.assertRaises(HostChatError):
            validate_enriched_draft(None)
        with self.assertRaises(HostChatError):
            validate_enriched_draft({"assets": []})
        with self.assertRaises(HostChatError):
            validate_enriched_draft({"project": "not-a-dict"})

        valid = {"project": {"title": "Demo"}}
        self.assertIs(validate_enriched_draft(valid), valid)

    def test_validate_does_not_require_screens_or_tuning(self) -> None:
        candidate = {
            "project": {"title": "No fixed schema"},
            "custom_flow": {"menu_order": ["start", "play"]},
        }
        self.assertEqual(validate_enriched_draft(candidate)["custom_flow"]["menu_order"], ["start", "play"])

    def test_invalid_candidate_leaves_session_unchanged(self) -> None:
        session = new_session("merge-fail")
        session["draft_brief"] = {"project": {"title": "Before"}, "assets": [{"name": "hero", "type": "character"}]}
        session["ready_to_export"] = True
        snapshot = copy.deepcopy(session)

        with self.assertRaises(HostChatError):
            apply_draft_replacement(session, {"assets": []})

        self.assertEqual(session, snapshot)

    def test_apply_sets_backup_and_clears_ready_to_export(self) -> None:
        session = new_session("merge-ok")
        old_draft = {
            "project": {"title": "Before"},
            "assets": [{"name": "hero", "type": "character"}],
        }
        session["draft_brief"] = copy.deepcopy(old_draft)
        session["ready_to_export"] = True

        candidate = {
            "project": {"title": "After", "genre": "platformer"},
            "assets": [{"name": "hero", "type": "character", "notes": "idle added"}],
        }
        summary = apply_draft_replacement(session, candidate)

        self.assertTrue(summary["ok"])
        self.assertEqual(session["draft_brief_backup"], old_draft)
        self.assertEqual(session["draft_brief"]["project"]["title"], "After")
        self.assertFalse(session["ready_to_export"])
        self.assertNotEqual(summary["fingerprint"], summary["previous_fingerprint"])

    def test_apply_fingerprint_changes(self) -> None:
        session = new_session("fp-change")
        old_draft = {"project": {"title": "Old"}}
        session["draft_brief"] = copy.deepcopy(old_draft)
        old_fp = draft_fingerprint(old_draft)

        candidate = {"project": {"title": "New"}}
        summary = apply_draft_replacement(session, candidate)

        self.assertEqual(summary["previous_fingerprint"], old_fp)
        self.assertEqual(summary["fingerprint"], draft_fingerprint(session["draft_brief"]))
        self.assertNotEqual(summary["fingerprint"], old_fp)

    def test_apply_preserves_assets_when_candidate_omits_assets(self) -> None:
        session = new_session("preserve-assets")
        session["draft_brief"] = {
            "project": {"title": "Old", "genre": "fishing"},
            "assets": [
                {"name": "hero", "type": "character"},
                {"name": "hook", "type": "prop"},
            ],
        }
        candidate = {
            "project": {"title": "Old", "player_flow": {"menu": ["start"]}},
        }
        apply_draft_replacement(
            session,
            candidate,
            asset_proposals=[{"name": "tension_ui", "type": "ui"}],
        )
        names = [a.get("name") for a in session["draft_brief"].get("assets") or []]
        self.assertEqual(names, ["hero", "hook", "tension_ui"])
        self.assertEqual(
            (session["draft_brief"].get("project") or {}).get("player_flow"),
            {"menu": ["start"]},
        )
        self.assertEqual((session["draft_brief"].get("project") or {}).get("genre"), "fishing")

    def test_apply_strips_fat_scene_bodies_keeps_base_catalog(self) -> None:
        session = new_session("strip-enrich-merge")
        session["draft_brief"] = {
            "project": {
                "title": "Old",
                "scenes": [
                    {"id": "lake", "title": "湖面", "path": "scenes/lake.json"},
                ],
            },
            "assets": [{"name": "hook", "type": "prop"}],
        }
        candidate = {
            "project": {
                "title": "New",
                "scenes": [
                    {
                        "id": "lake",
                        "title": "湖面",
                        "notes": "ENRICH_FAT_SHOULD_NOT_LAND",
                    }
                ],
            },
            "assets": [{"name": "hook", "type": "prop"}],
        }
        apply_draft_replacement(session, candidate)
        self.assertEqual(session["draft_brief"]["project"]["title"], "New")
        scenes = session["draft_brief"]["project"]["scenes"]
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0].get("path"), "scenes/lake.json")
        self.assertNotIn("notes", scenes[0])

    def test_enrich_full_draft_without_root_strips_scene_bodies(self) -> None:
        session = new_session("enrich-no-root-strip")
        session["draft_brief"] = copy.deepcopy(_THIN_DRAFT)
        session["draft_brief"]["project"]["scenes"] = [
            {"id": "lake", "title": "湖面", "path": "scenes/lake.json"},
        ]
        config = {"api_key": "k", "model": "m", "api_base": "http://x"}
        fat = {
            "draft_brief": {
                "project": {
                    "title": "River Cast enriched",
                    "genre": "fishing",
                    "gameplay_loop": "Cast, wait, reel, sell.",
                    "scenes": [
                        {
                            "id": "lake",
                            "title": "湖面",
                            "notes": "ENRICH_NO_ROOT_FAT",
                        }
                    ],
                },
                "assets": [{"name": "player_fisher", "type": "character"}],
            },
            "asset_proposals": [],
            "summary": "加厚了湖面",
        }
        with patch(
            "host_chat.chat_text_completion",
            side_effect=[
                json.dumps(_gaps_mock(), ensure_ascii=False),
                json.dumps(fat, ensure_ascii=False),
            ],
        ), patch(
            "host_chat._try_rerun_makeability_after_write",
            return_value="",
        ), patch(
            "host_chat.resolve_host_api_settings",
            return_value={
                "api_key": "k",
                "model": "m",
                "api_base": "http://x",
                "proxy": None,
            },
        ), patch(
            "host_chat._project_root_for_session",
            return_value=None,
        ):
            result = run_brief_enrich(session, config=config)
        self.assertTrue(result["ok"])
        scenes = session["draft_brief"]["project"]["scenes"]
        self.assertEqual(scenes[0].get("path"), "scenes/lake.json")
        self.assertNotIn("notes", scenes[0])
        self.assertEqual(session["draft_brief"]["project"]["title"], "River Cast enriched")

    def test_merge_asset_proposals_dedupes_by_name_case_insensitive(self) -> None:
        draft = {
            "project": {"title": "Demo"},
            "assets": [{"name": "Hero", "type": "character", "size": "32x32"}],
        }
        proposals = [
            {"name": "hero", "type": "character", "notes": "updated"},
            {"name": "bg", "type": "background"},
        ]
        merged = merge_asset_proposals(draft, proposals)

        self.assertIsNot(merged, draft)
        self.assertEqual(draft["assets"][0]["size"], "32x32")
        self.assertEqual(len(merged["assets"]), 2)
        hero = merged["assets"][0]
        self.assertEqual(hero["name"], "hero")
        self.assertEqual(hero["notes"], "updated")
        self.assertEqual(hero["size"], "32x32")
        self.assertEqual(merged["assets"][1]["name"], "bg")

    def test_apply_merges_asset_proposals(self) -> None:
        session = new_session("merge-assets")
        session["draft_brief"] = {
            "project": {"title": "Demo"},
            "assets": [{"name": "hero", "type": "character"}],
        }
        candidate = {"project": {"title": "Demo enriched"}}
        proposals = [
            {"name": "hero", "notes": "needs idle"},
            {"name": "ui_panel", "type": "ui"},
        ]
        summary = apply_draft_replacement(session, candidate, asset_proposals=proposals)

        assets = session["draft_brief"]["assets"]
        self.assertEqual(summary["asset_count"], 2)
        self.assertEqual(assets[0]["notes"], "needs idle")
        self.assertEqual(assets[1]["name"], "ui_panel")


class BriefEnrichRunnerTests(unittest.TestCase):
    def test_enrich_two_step_writes_thickened_draft(self) -> None:
        session = new_session("enrich-ok")
        session["draft_brief"] = copy.deepcopy(_THIN_DRAFT)
        session["ready_to_export"] = True
        old_fp = draft_fingerprint(_THIN_DRAFT)

        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        side_effect = [
            json.dumps(_gaps_mock()),
            json.dumps(_enrich_mock()),
        ]
        with patch("host_chat.chat_text_completion", side_effect=side_effect) as mock_llm, patch(
            "host_chat._try_rerun_makeability_after_write",
            return_value="",
        ) as mock_rerun:
            result = run_brief_enrich(session, config=config)

        self.assertTrue(result["ok"])
        self.assertEqual(mock_llm.call_count, 2)
        mock_rerun.assert_called_once()
        self.assertIn("player_flow", session["draft_brief"]["project"])
        self.assertEqual(session["draft_brief_backup"], _THIN_DRAFT)
        self.assertFalse(session["ready_to_export"])
        self.assertIsNotNone(session.get("last_enrich_at"))
        self.assertNotEqual(result["fingerprint"], old_fp)
        self.assertEqual(result["asset_count"], 2)
        assets = session["draft_brief"]["assets"]
        self.assertEqual(assets[1]["name"], "ui_tension_bar")

    def test_enrich_passes_hint_to_llm(self) -> None:
        session = new_session("enrich-hint")
        session["draft_brief"] = copy.deepcopy(_THIN_DRAFT)

        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        side_effect = [
            json.dumps(_gaps_mock()),
            json.dumps(_enrich_mock(title_suffix=" HUD focus")),
        ]
        with patch("host_chat.chat_text_completion", side_effect=side_effect) as mock_llm, patch(
            "host_chat._try_rerun_makeability_after_write",
            return_value="",
        ):
            run_brief_enrich(session, hint="只补 HUD", temperature=0.9, config=config)

        critique_user = mock_llm.call_args_list[0].kwargs["messages"][1]["content"]
        enrich_user = mock_llm.call_args_list[1].kwargs["messages"][1]["content"]
        self.assertIn("只补 HUD", critique_user)
        self.assertIn("只补 HUD", enrich_user)
        self.assertEqual(mock_llm.call_args_list[0].kwargs["temperature"], 0.9)
        self.assertEqual(mock_llm.call_args_list[1].kwargs["temperature"], 0.9)

    def test_enrich_failure_keeps_old_draft(self) -> None:
        session = new_session("enrich-fail")
        session["draft_brief"] = copy.deepcopy(_THIN_DRAFT)
        session["ready_to_export"] = True
        snapshot = copy.deepcopy(session)

        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        side_effect = [
            json.dumps(_gaps_mock()),
            "not valid enrich json",
        ]
        with patch("host_chat.chat_text_completion", side_effect=side_effect):
            with self.assertRaises(HostChatError):
                run_brief_enrich(session, config=config)

        self.assertEqual(session["draft_brief"], snapshot["draft_brief"])
        self.assertTrue(session["ready_to_export"])
        self.assertNotIn("draft_brief_backup", session)
        self.assertNotIn("last_enrich_at", session)


if __name__ == "__main__":
    unittest.main()
