"""Tests for topic multi-persona brainstorm generate + apply."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brief_shards import save_json_shard
from host_chat import HostChatError, draft_fingerprint, new_session
from topic_brainstorm import apply_brainstorm_proposals, run_topic_brainstorm


def _draft() -> dict:
    return {
        "project": {
            "title": "钓鱼",
            "genre": "fishing",
            "gameplay_loop": "抛竿等待拉线",
        },
        "assets": [{"name": "hook", "type": "prop"}],
    }


def _persona_json(role: str) -> str:
    return (
        "{"
        f'"title": "{role} plan",'
        f'"bullets": ["point for {role}", "detail {role}"]'
        "}"
    )


class TopicBrainstormTests(unittest.TestCase):
    def test_generate_writes_result_not_draft(self) -> None:
        session = new_session("bs-gen")
        session["draft_brief"] = _draft()
        before_fp = draft_fingerprint(session["draft_brief"])
        config = {"api_key": "k", "model": "m", "api_base": "http://x"}

        with patch(
            "topic_brainstorm.chat_text_completion",
            side_effect=[
                _persona_json("systems"),
                _persona_json("ui_presentation"),
                _persona_json("feel_feedback"),
                _persona_json("devil_advocate"),
            ],
        ):
            with patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={"api_key": "k", "model": "m", "api_base": "http://x", "proxy": None},
            ):
                result = run_topic_brainstorm(session, "张力条怎么呈现", config=config)

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["proposal_count"], 3)
        self.assertEqual(result["mode"], "personas")
        self.assertIn("brainstorm_result", session)
        self.assertEqual(draft_fingerprint(session["draft_brief"]), before_fp)

    def test_multi_model_flag_without_config_stays_personas(self) -> None:
        session = new_session("bs-mm")
        session["draft_brief"] = _draft()
        with patch(
            "topic_brainstorm.chat_text_completion",
            side_effect=[
                _persona_json("systems"),
                _persona_json("ui_presentation"),
                _persona_json("feel_feedback"),
                _persona_json("devil_advocate"),
            ],
        ):
            with patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={"api_key": "k", "model": "m", "api_base": "http://x", "proxy": None},
            ):
                result = run_topic_brainstorm(
                    session,
                    "菜单结构",
                    multi_model=True,
                    config={"api_key": "k"},
                )
        self.assertEqual(result["mode"], "personas")
        self.assertIn("降级", result["assistant_message"])

    def test_apply_updates_draft(self) -> None:
        session = new_session("bs-apply")
        session["draft_brief"] = _draft()
        session["brainstorm_result"] = {
            "topic": "张力",
            "proposals": [
                {
                    "id": "p1",
                    "role": "ui_presentation",
                    "title": "左侧张力条",
                    "bullets": ["HUD 左上"],
                }
            ],
        }
        thickened = {
            "project": {
                "title": "钓鱼",
                "genre": "fishing",
                "gameplay_loop": "抛竿等待拉线",
                "presentation_notes": "拉线屏左侧张力条",
            },
            "assets": [{"name": "hook", "type": "prop"}],
        }
        llm_out = {
            "draft_brief": thickened,
            "asset_proposals": [{"name": "tension_bar", "type": "ui"}],
            "summary": "采用左侧张力条",
        }
        with patch(
            "topic_brainstorm.chat_text_completion",
            return_value=__import__("json").dumps(llm_out, ensure_ascii=False),
        ):
            with patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={"api_key": "k", "model": "m", "api_base": "http://x", "proxy": None},
            ):
                result = apply_brainstorm_proposals(session, ["p1"], config={"api_key": "k"})

        self.assertTrue(result["ok"])
        self.assertFalse(session.get("ready_to_export"))
        self.assertIsNotNone(session.get("draft_brief_backup"))
        self.assertEqual(
            (session["draft_brief"].get("project") or {}).get("presentation_notes"),
            "拉线屏左侧张力条",
        )
        names = [a.get("name") for a in session["draft_brief"].get("assets") or []]
        self.assertIn("tension_bar", names)

    def test_apply_unknown_id_errors(self) -> None:
        session = new_session("bs-bad")
        session["draft_brief"] = _draft()
        session["brainstorm_result"] = {"topic": "x", "proposals": [{"id": "p1", "title": "a", "bullets": []}]}
        with self.assertRaises(HostChatError):
            apply_brainstorm_proposals(session, ["p99"], config={"api_key": "k"})

    def test_generate_hydrates_catalog_scene_notes_for_personas(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scenes").mkdir()
            save_json_shard(
                root / "scenes" / "lake.json",
                {"id": "lake", "title": "湖面", "notes": "SHARD_LAKE_NOTES"},
            )
            session = new_session("bs-hydrate")
            session["draft_brief"] = {
                "project": {
                    "title": "钓鱼",
                    "genre": "fishing",
                    "gameplay_loop": "抛竿",
                    "scenes": [
                        {"id": "lake", "title": "湖面", "path": "scenes/lake.json"},
                    ],
                },
                "assets": [{"name": "hook", "type": "prop"}],
            }
            captured: list[dict] = []

            def _capture(**kwargs):
                payload = json.loads(kwargs["messages"][1]["content"])
                captured.append(payload)
                role = payload.get("role") or "systems"
                return _persona_json(str(role))

            with patch(
                "topic_brainstorm.chat_text_completion",
                side_effect=_capture,
            ), patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={
                    "api_key": "k",
                    "model": "m",
                    "api_base": "http://x",
                    "proxy": None,
                },
            ), patch(
                "topic_brainstorm._project_root_for_session",
                return_value=root,
            ):
                result = run_topic_brainstorm(session, "湖面怎么呈现", config={"api_key": "k"})
            self.assertTrue(result["ok"])
            self.assertTrue(captured)
            scenes = (captured[0].get("draft_brief") or {}).get("project", {}).get("scenes") or []
            self.assertEqual(scenes[0].get("notes"), "SHARD_LAKE_NOTES")

    def test_apply_canonicalizes_fat_scenes_to_shards(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            session = new_session("bs-canon")
            session["draft_brief"] = _draft()
            session["brainstorm_result"] = {
                "topic": "场景",
                "proposals": [
                    {
                        "id": "p1",
                        "role": "systems",
                        "title": "加湖面",
                        "bullets": ["湖面场景"],
                    }
                ],
            }
            thickened = {
                "project": {
                    "title": "钓鱼",
                    "genre": "fishing",
                    "gameplay_loop": "抛竿等待拉线",
                    "scenes": [
                        {
                            "id": "lake",
                            "title": "湖面",
                            "summary": "主钓点",
                            "notes": "CANON_NOTES",
                        }
                    ],
                },
                "assets": [{"name": "hook", "type": "prop"}],
            }
            llm_out = {
                "draft_brief": thickened,
                "asset_proposals": [],
                "summary": "加了湖面场景",
            }
            with patch(
                "topic_brainstorm.chat_text_completion",
                return_value=json.dumps(llm_out, ensure_ascii=False),
            ), patch(
                "topic_brainstorm.resolve_host_api_settings",
                return_value={
                    "api_key": "k",
                    "model": "m",
                    "api_base": "http://x",
                    "proxy": None,
                },
            ), patch(
                "topic_brainstorm._project_root_for_session",
                return_value=root,
            ):
                result = apply_brainstorm_proposals(session, ["p1"], config={"api_key": "k"})
            self.assertTrue(result["ok"])
            row = session["draft_brief"]["project"]["scenes"][0]
            self.assertEqual(row.get("id"), "lake")
            self.assertIn("path", row)
            self.assertNotIn("notes", row)
            body = json.loads((root / "scenes" / "lake.json").read_text(encoding="utf-8"))
            self.assertEqual(body.get("notes"), "CANON_NOTES")

    def test_apply_rejects_fat_scenes_without_project_root(self) -> None:
        session = new_session("bs-no-root")
        session["draft_brief"] = _draft()
        session["brainstorm_result"] = {
            "topic": "场景",
            "proposals": [
                {
                    "id": "p1",
                    "role": "systems",
                    "title": "加湖面",
                    "bullets": ["湖面场景"],
                }
            ],
        }
        thickened = {
            "project": {
                "title": "钓鱼",
                "genre": "fishing",
                "gameplay_loop": "抛竿等待拉线",
                "scenes": [
                    {
                        "id": "lake",
                        "title": "湖面",
                        "notes": "SHOULD_NOT_LAND",
                    }
                ],
            },
            "assets": [{"name": "hook", "type": "prop"}],
        }
        llm_out = {
            "draft_brief": thickened,
            "asset_proposals": [],
            "summary": "加了湖面",
        }
        with patch(
            "topic_brainstorm.chat_text_completion",
            return_value=json.dumps(llm_out, ensure_ascii=False),
        ), patch(
            "topic_brainstorm.resolve_host_api_settings",
            return_value={
                "api_key": "k",
                "model": "m",
                "api_base": "http://x",
                "proxy": None,
            },
        ), patch(
            "topic_brainstorm._project_root_for_session",
            return_value=None,
        ):
            with self.assertRaises(HostChatError) as ctx:
                apply_brainstorm_proposals(session, ["p1"], config={"api_key": "k"})
        self.assertIn("bound", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
