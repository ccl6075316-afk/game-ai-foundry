"""Tests for Brief Tab host-chat helpers."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from brief_shards import save_json_shard
from host_chat import (
    HostChatError,
    _CHAR_BUDGET,
    _apply_parsed,
    _build_user_payload,
    _parse_llm_json,
    _system_prompt,
    apply_brief_patches,
    build_autofix_user_message,
    deep_merge_brief,
    draft_fingerprint,
    export_brief,
    list_sessions,
    load_project_draft_from_disk,
    load_session,
    looks_like_draft_write_claim,
    maybe_compress_session,
    new_session,
    reconcile_makeability_after_draft_write,
    resolve_mode,
    run_autofix,
    run_turn,
    save_session,
    session_path_for_id,
    session_status,
    set_session_focus,
    clear_session_focus,
    normalize_session_focus,
    focus_from_paths,
    user_requests_commit_brief,
    user_requests_commit_doc,
)


class HostChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Keep unit tests on Host LLM mocks; avoid hitting embedded Pi.
        os.environ["GAMEFACTORY_BRIEF_EXECUTOR"] = "host"

    def test_parse_llm_json_fenced(self) -> None:
        raw = 'Here:\n```json\n{"assistant_message": "hi", "choices": ["A"]}\n```'
        parsed = _parse_llm_json(raw)
        self.assertEqual(parsed["assistant_message"], "hi")

    def test_user_requests_commit_brief(self) -> None:
        self.assertTrue(user_requests_commit_brief("行，落实成 brief 吧"))
        self.assertTrue(user_requests_commit_brief("写成brief"))
        self.assertFalse(user_requests_commit_brief("先聊聊攻击手感"))

    def test_user_requests_commit_doc(self) -> None:
        self.assertTrue(user_requests_commit_doc("整理成设计说明"))
        self.assertTrue(user_requests_commit_doc("写成 markdown"))
        self.assertTrue(user_requests_commit_doc("整理成一篇完整设计说明 markdown"))
        self.assertFalse(user_requests_commit_doc("落实成 brief"))
        self.assertEqual(resolve_mode(new_session("d1"), "整理成文档"), "commit_doc")

    def test_resolve_mode(self) -> None:
        session = new_session("abc")
        self.assertEqual(resolve_mode(session, "聊聊想法"), "chat")
        self.assertEqual(resolve_mode(session, "落实成 brief"), "commit_brief")
        session["pending_mode"] = "commit_brief"
        self.assertEqual(resolve_mode(session, "好"), "commit_brief")

    def test_session_roundtrip(self) -> None:
        session = new_session("sess-demo")
        session["messages"] = [{"role": "user", "content": "hello"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = session_path_for_id("sess-demo", base_dir=Path(tmp))
            save_session(path, session)
            loaded = load_session(path)
        self.assertEqual(loaded["id"], "sess-demo")
        self.assertEqual(loaded["messages"][0]["content"], "hello")

    def test_list_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            s = new_session("one")
            s["messages"] = [{"role": "user", "content": "magic prince"}]
            save_session(session_path_for_id("one", base_dir=base), s)
            items = list_sessions(base_dir=base)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "one")
        self.assertIn("magic", items[0]["title"])

    def test_chat_turn_forces_ready_false_without_draft(self) -> None:
        session = new_session("chat1")
        llm_payload = {
            "assistant_message": "可以先聊玩法。",
            "choices": ["横版", "俯视角"],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": True,  # malicious; must be forced false
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value=json.dumps(llm_payload)):
            result = run_turn(session, user_message="我想做个游戏", config=config)
        self.assertFalse(result["ready_to_export"])
        self.assertIsNone(session.get("draft_brief"))
        self.assertEqual(session["mode"], "chat")
        self.assertEqual(len(session["messages"]), 2)

    def test_chat_turn_persists_progressive_draft(self) -> None:
        session = new_session("chat2")
        session["draft_brief"] = {
            "project": {"title": "Magic Prince", "genre": "2d_platformer"},
            "assets": [{"name": "hero", "type": "character"}],
        }
        llm_payload = {
            "assistant_message": "已把跳跃写进草稿。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "draft_brief": {
                    "project": {
                        "title": "Magic Prince",
                        "genre": "2d_platformer",
                        "controls": {"jump": ["Space"]},
                    },
                    "assets": [
                        {"name": "hero", "type": "character"},
                        {"name": "slime", "type": "character"},
                    ],
                }
            },
            "ready_to_export": True,  # chat must force false
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value=json.dumps(llm_payload)):
            result = run_turn(session, user_message="加个史莱姆和跳跃", config=config)
        self.assertFalse(result["ready_to_export"])
        self.assertFalse(session["ready_to_export"])
        self.assertEqual(session["mode"], "chat")
        draft = session["draft_brief"]
        self.assertEqual(draft["project"]["title"], "Magic Prince")
        self.assertEqual(draft["project"]["controls"]["jump"], ["Space"])
        self.assertEqual(len(draft["assets"]), 2)
        payload = _build_user_payload(session, "chat")
        self.assertIn("current_draft_brief", payload)

    def test_chat_payload_focus_excludes_other_scene_bodies(self) -> None:
        session = new_session("focus-scenes")
        dock_marker = "UNIQUE_DOCK_SCENE_BODY_XYZ"
        hall_marker = "UNIQUE_HALL_SCENE_BODY_XYZ"
        session["draft_brief"] = {
            "project": {
                "title": "Fish",
                "description": "Short intro.",
                "art_direction": "pixel",
                "dimension": "2d",
            },
            "scenes": [
                {"id": "hall", "title": "Hall", "summary": hall_marker},
                {"id": "dock", "title": "Dock", "summary": dock_marker},
            ],
            "assets": [
                {
                    "id": "rod",
                    "name": "rod",
                    "type": "texture",
                    "usage": "world_background",
                    "display_size": {"width": 32, "height": 32},
                    "usage_description": "rod",
                }
            ],
        }
        session["focus"] = {"kind": "scene", "id": "hall"}
        payload = _build_user_payload(session, "chat")
        blob = json.dumps(payload, ensure_ascii=False)
        self.assertIn(hall_marker, blob)
        self.assertNotIn(dock_marker, blob)

    def test_normalize_session_focus_requires_id_except_project(self) -> None:
        self.assertEqual(
            normalize_session_focus({"kind": "project"}),
            {"kind": "project"},
        )
        with self.assertRaises(HostChatError):
            normalize_session_focus({"kind": "scene"})
        out = normalize_session_focus(
            {"kind": "visual_target", "id": "hub", "extra": {"candidate": "a"}}
        )
        self.assertEqual(out, {"kind": "visual_target", "id": "hub", "extra": {"candidate": "a"}})

    def test_focus_from_paths_first_match(self) -> None:
        self.assertEqual(
            focus_from_paths(["project.scenes[id=main_hub].notes"]),
            {"kind": "scene", "id": "main_hub"},
        )
        self.assertEqual(
            focus_from_paths(["project.systems[id=economy].tuning", "project.scenes[id=x]"]),
            {"kind": "system", "id": "economy"},
        )
        self.assertEqual(
            focus_from_paths(["assets[name=rod_01]"]),
            {"kind": "asset", "id": "rod_01"},
        )

    def test_set_session_focus_in_status(self) -> None:
        session = new_session("focus-api")
        set_session_focus(session, {"kind": "scene", "id": "dock"})
        st = session_status(session)
        self.assertEqual(st.get("focus"), {"kind": "scene", "id": "dock"})

    def test_apply_parsed_sets_focus_from_artifact(self) -> None:
        session = new_session("focus-artifact")
        session["draft_brief"] = {"project": {"title": "T"}, "assets": []}
        parsed = {
            "assistant_message": "ok",
            "artifact": {"focus": {"kind": "system", "id": "combat"}},
        }
        _apply_parsed(session, parsed, "chat")
        self.assertEqual(session.get("focus"), {"kind": "system", "id": "combat"})

    def test_apply_parsed_drops_illegal_focus_still_writes(self) -> None:
        session = new_session("focus-drop")
        session["draft_brief"] = {
            "project": {"title": "Fish", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        parsed = {
            "assistant_message": "改了目标。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "focus": {"kind": "scene"},
                "brief_patches": [
                    {
                        "op": "set",
                        "path": "project.session_goal",
                        "value": "Catch fish.",
                    }
                ],
            },
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        self.assertEqual(session["draft_brief"]["project"]["session_goal"], "Catch fish.")
        self.assertNotEqual(session.get("focus"), {"kind": "scene"})
        self.assertNotIn("focus 未更新", out["assistant_message"])

    def test_deep_merge_brief_keeps_assets_when_project_patched(self) -> None:
        base = {
            "project": {"title": "A", "genre": "platformer"},
            "assets": [{"name": "hero"}, {"name": "coin"}],
        }
        incoming = {"project": {"title": "A", "controls": {"jump": ["Space"]}}}
        merged = deep_merge_brief(base, incoming)
        assert merged is not None
        self.assertEqual(len(merged["assets"]), 2)
        self.assertEqual(merged["project"]["genre"], "platformer")
        self.assertEqual(merged["project"]["controls"]["jump"], ["Space"])

    def test_deep_merge_brief_preserves_omitted_assets_and_long_copy(self) -> None:
        long_desc = "A " + ("detailed fishing loop. " * 20)
        base = {
            "project": {"title": "Fish", "description": long_desc, "genre": "sim"},
            "assets": [
                {"id": "rod", "name": "rod", "type": "icon_kit"},
                {"id": "lake", "name": "lake", "type": "background"},
            ],
            "animation_graphs": [{"character_asset": "carp", "edges": []}],
        }
        incoming = {
            "project": {
                "title": "Fish",
                "description": "Short rewrite.",
                "session_goal": "Catch one fish.",
            },
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit", "usage": "ui_icon"}],
        }
        merged = deep_merge_brief(base, incoming)
        assert merged is not None
        self.assertEqual(len(merged["assets"]), 2)
        self.assertEqual(merged["assets"][0].get("usage"), "ui_icon")
        self.assertEqual(merged["assets"][1].get("id"), "lake")
        self.assertEqual(merged["project"]["description"], long_desc)
        self.assertEqual(merged["project"]["session_goal"], "Catch one fish.")
        self.assertEqual(len(merged["animation_graphs"]), 1)

    def test_deep_merge_brief_preserves_omitted_scenes_and_systems(self) -> None:
        base = {
            "project": {
                "title": "Fish",
                "scenes": [
                    {"id": "lake", "title": "湖面"},
                    {"id": "shop", "title": "商店"},
                ],
                "systems": [
                    {"id": "cast", "title": "抛竿"},
                    {"id": "reel", "title": "收线"},
                ],
            },
            "assets": [],
        }
        incoming = {
            "project": {
                "title": "Fish",
                "scenes": [{"id": "lake", "title": "湖面", "summary": "主场景"}],
                "systems": [{"id": "cast", "title": "抛竿", "summary": "力度条"}],
            }
        }
        merged = deep_merge_brief(base, incoming)
        assert merged is not None
        scenes = merged["project"]["scenes"]
        systems = merged["project"]["systems"]
        # Fat structure bodies are stripped from merge; base catalog/list preserved.
        self.assertEqual(len(scenes), 2)
        self.assertNotIn("summary", scenes[0])
        self.assertEqual(scenes[1].get("id"), "shop")
        self.assertEqual(len(systems), 2)
        self.assertNotIn("summary", systems[0])
        self.assertEqual(systems[1].get("id"), "reel")

    def test_deep_merge_brief_allows_catalog_scene_refs(self) -> None:
        base = {
            "project": {
                "title": "Fish",
                "scenes": [{"id": "lake", "title": "湖面", "path": "scenes/lake.json"}],
            },
            "assets": [],
        }
        incoming = {
            "project": {
                "scenes": [
                    {"id": "lake", "title": "湖面", "path": "scenes/lake.json"},
                    {"id": "shop", "title": "商店", "path": "scenes/shop.json"},
                ]
            }
        }
        merged = deep_merge_brief(base, incoming)
        assert merged is not None
        ids = [s.get("id") for s in merged["project"]["scenes"]]
        self.assertEqual(ids, ["lake", "shop"])

    def test_deep_merge_brief_preserves_global_visual_reference(self) -> None:
        base = {
            "project": {
                "title": "Fish",
                "visual_reference": "output/global/selected.png",
            },
            "assets": [],
        }
        incoming = {
            "project": {
                "title": "Fish",
                "visual_reference": "",
                "description": "updated",
            }
        }
        merged = deep_merge_brief(base, incoming)
        assert merged is not None
        self.assertEqual(
            merged["project"]["visual_reference"],
            "output/global/selected.png",
        )
        self.assertEqual(merged["project"]["description"], "updated")

    def test_deep_merge_brief_preserves_scene_visual_reference(self) -> None:
        base = {
            "project": {
                "title": "Fish",
                "scenes": [
                    {
                        "id": "lake",
                        "title": "湖面",
                        "visual_reference": "output/lake/selected.png",
                    }
                ],
            },
            "assets": [],
        }
        incoming = {
            "project": {
                "scenes": [
                    {"id": "lake", "title": "湖面", "summary": "主场景", "visual_reference": ""}
                ]
            }
        }
        merged = deep_merge_brief(base, incoming)
        assert merged is not None
        self.assertEqual(
            merged["project"]["scenes"][0]["visual_reference"],
            "output/lake/selected.png",
        )
        # Fat incoming scenes are stripped; summary must not land via deep_merge.
        self.assertNotIn("summary", merged["project"]["scenes"][0])

    def test_apply_brief_patches_sets_nested_project_fields(self) -> None:
        draft = {
            "project": {
                "title": "Fish",
                "description": "Long established description about tug-of-war.",
                "genre": "sim",
            },
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {"op": "set", "path": "project.session_goal", "value": "Land one fish today."},
                {"op": "set", "path": "project.controls.cast", "value": ["Click"]},
            ],
        )
        self.assertEqual(out["project"]["session_goal"], "Land one fish today.")
        self.assertEqual(out["project"]["controls"]["cast"], ["Click"])
        self.assertEqual(
            out["project"]["description"],
            "Long established description about tug-of-war.",
        )
        self.assertEqual(len(out["assets"]), 1)

    def test_apply_brief_patches_upserts_asset_without_dropping_others(self) -> None:
        draft = {
            "project": {"title": "Fish"},
            "assets": [
                {"id": "rod", "name": "rod", "type": "icon_kit"},
                {"id": "lake", "name": "lake", "type": "background"},
            ],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"id": "rod"},
                    "set": {"usage": "ui_icon", "description": "Basic rod"},
                },
                {
                    "op": "add_asset",
                    "value": {"id": "bait", "name": "bait", "type": "icon_kit"},
                },
            ],
        )
        self.assertEqual(len(out["assets"]), 3)
        rod = next(a for a in out["assets"] if a.get("id") == "rod")
        self.assertEqual(rod.get("usage"), "ui_icon")
        self.assertEqual(rod.get("description"), "Basic rod")
        self.assertTrue(any(a.get("id") == "lake" for a in out["assets"]))
        self.assertTrue(any(a.get("id") == "bait" for a in out["assets"]))

    def test_apply_brief_patches_upsert_system_scene_panel(self) -> None:
        draft = {
            "project": {
                "title": "Fish",
                "systems": [
                    {"id": "aquarium", "title": "Aquarium", "notes": "locked until purchased"},
                ],
                "scenes": [
                    {"id": "main_hub", "title": "Hub", "notes": "Aquarium locked"},
                ],
                "ui_panels": [
                    {"id": "main_hub_buildings", "title": "Buildings", "notes": "锁定态"},
                ],
            },
            "assets": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {
                        "notes": "unlocked from the start with no building purchase",
                    },
                },
                {
                    "op": "upsert_scene",
                    "match": {"id": "main_hub"},
                    "set": {"notes": "enterable from the start"},
                },
                {
                    "op": "upsert_ui_panel",
                    "match": {"id": "main_hub_buildings"},
                    "set": {"notes": "开局即可进入"},
                },
            ],
        )
        self.assertIn("unlocked from the start", out["project"]["systems"][0]["notes"])
        self.assertIn("enterable from the start", out["project"]["scenes"][0]["notes"])
        self.assertIn("开局即可进入", out["project"]["ui_panels"][0]["notes"])

    def test_apply_brief_patches_set_ui_panel_selector_path(self) -> None:
        draft = {
            "project": {
                "title": "Fish",
                "ui_panels": [
                    {
                        "id": "catch_result_popup",
                        "title": "收获展示",
                        "notes": "old",
                    }
                ],
            },
            "assets": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "set",
                    "path": "project.ui_panels[id=catch_result_popup].notes",
                    "value": "捕获/逃脱均弹出；一侧操作，一侧挂鱼动画。",
                }
            ],
        )
        self.assertEqual(
            out["project"]["ui_panels"][0]["notes"],
            "捕获/逃脱均弹出；一侧操作，一侧挂鱼动画。",
        )

    def test_apply_brief_patches_set_ui_panel_chinese_title_selector(self) -> None:
        draft = {
            "project": {
                "title": "Fish",
                "ui_panels": [
                    {"id": "catch_result_popup", "title": "收获展示", "notes": "old"},
                ],
            },
            "assets": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "set",
                    "path": "project.ui_panels[id=收获展示].notes",
                    "value": "卖或存仓。",
                }
            ],
        )
        self.assertEqual(out["project"]["ui_panels"][0]["notes"], "卖或存仓。")

    def test_apply_brief_patches_catalog_upsert_writes_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard_path = root / "scenes" / "hall.json"
            shard_path.parent.mkdir(parents=True)
            save_json_shard(
                shard_path,
                {"id": "hall", "title": "Hall", "notes": "old"},
            )
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {"id": "hall", "title": "Hall", "path": "scenes/hall.json"},
                    ],
                },
                "assets": [{"id": "a", "name": "a", "type": "prop", "usage": "x"}],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "hall"},
                        "set": {"notes": "updated notes"},
                    },
                ],
                project_root=root,
            )
            row = out["project"]["scenes"][0]
            self.assertEqual(row, {"id": "hall", "title": "Hall", "path": "scenes/hall.json"})
            body = json.loads(shard_path.read_text(encoding="utf-8"))
            self.assertEqual(body["notes"], "updated notes")

    def test_apply_brief_patches_no_focus_allows_scene_upsert(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "hall", "title": "Hall", "summary": "x"}],
            },
            "assets": [{"id": "a", "name": "a", "type": "prop", "usage": "x"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_scene",
                    "match": {"id": "hall"},
                    "set": {"notes": "updated without focus"},
                },
            ],
        )
        self.assertEqual(
            out["project"]["scenes"][0]["notes"], "updated without focus"
        )

    def test_apply_brief_patches_allows_cross_scene_upsert(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [
                    {"id": "hall", "title": "Hall"},
                    {"id": "dock", "title": "Dock"},
                ],
            },
            "assets": [{"id": "a", "name": "a", "type": "prop", "usage": "x"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_scene",
                    "match": {"id": "dock"},
                    "set": {"notes": "related update"},
                },
            ],
        )
        self.assertEqual(out["project"]["scenes"][1]["notes"], "related update")

    def test_cross_scene_patch_writes_catalog_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "scenes" / "hall.json",
                {"id": "hall", "title": "Hall", "notes": "Mentions dock entrance."},
            )
            save_json_shard(
                root / "scenes" / "dock.json",
                {"id": "dock", "title": "Dock", "notes": "old"},
            )
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {"id": "hall", "title": "Hall", "path": "scenes/hall.json"},
                        {"id": "dock", "title": "Dock", "path": "scenes/dock.json"},
                    ],
                },
                "assets": [],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "dock"},
                        "set": {"notes": "updated across focus"},
                    },
                ],
                project_root=root,
            )
            body = json.loads(
                (root / "scenes" / "dock.json").read_text(encoding="utf-8")
            )
            self.assertEqual(body["notes"], "updated across focus")
            self.assertEqual(out["project"]["scenes"][1]["path"], "scenes/dock.json")

    def test_apply_brief_patches_no_focus_allows_asset_upsert(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [{"id": "fish", "name": "鱼", "type": "character"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"id": "fish"},
                    "set": {"display_size": {"width": 1536, "height": 1024}},
                },
            ],
        )
        self.assertEqual(
            out["assets"][0]["display_size"], {"width": 1536, "height": 1024}
        )

    def test_apply_brief_patches_rejects_destructive_collection_set(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "hall", "title": "Hall"}],
            },
            "assets": [{"id": "fish", "name": "鱼", "type": "character"}],
        }
        for path, value in (
            ("project", {}),
            ("project.scenes", []),
            ("project.scenes.invalid", "x"),
            ("project..scenes", []),
            (".project.scenes", []),
        ):
            with self.subTest(path=path):
                with self.assertRaisesRegex(HostChatError, "受保护|空路径段"):
                    apply_brief_patches(
                        draft,
                        [{"op": "set", "path": path, "value": value}],
                    )

    def test_apply_brief_patches_rejects_stable_catalog_key_changes(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [
                    {
                        "id": "hall",
                        "title": "Hall",
                        "path": "scenes/hall.json",
                    }
                ],
            },
            "assets": [{"id": "fish", "name": "鱼", "type": "character"}],
        }
        for path, value in (
            ("project.scenes[id=hall].id", "dock"),
            ("project.scenes[id=hall].path", "../escape.json"),
            ("project.scenes[id=hall]..id", "dock"),
            ("project.scenes[id=hall]..path", "../escape.json"),
        ):
            with self.subTest(path=path):
                with self.assertRaisesRegex(HostChatError, "稳定字段|空路径段"):
                    apply_brief_patches(
                        draft,
                        [
                            {
                                "op": "set",
                                "path": path,
                                "value": value,
                            }
                        ],
                    )

    def test_apply_brief_patches_rejects_typed_upsert_path_mismatch(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "hall", "title": "Hall"}],
                "systems": [],
            },
            "assets": [{"id": "fish", "name": "鱼", "type": "character"}],
        }
        with self.assertRaisesRegex(HostChatError, "path"):
            apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_scene",
                        "path": "project.systems",
                        "match": {"id": "hall"},
                        "set": {"notes": "wrong section"},
                    }
                ],
            )

    def test_invalid_asset_patch_does_not_mutate_catalog_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "assets" / "fish.spec.json"
            save_json_shard(
                shard,
                {"id": "fish", "name": "鱼", "type": "character"},
            )
            before = shard.read_bytes()
            draft = {
                "project": {"title": "T"},
                "assets": [
                    {
                        "id": "fish",
                        "name": "鱼",
                        "path": "assets/fish.spec.json",
                    }
                ],
            }
            with self.assertRaisesRegex(HostChatError, "Unknown asset type"):
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_asset",
                            "match": {"id": "fish"},
                            "set": {"type": "not_a_real_type"},
                        }
                    ],
                    project_root=root,
                )
            self.assertEqual(shard.read_bytes(), before)

    def test_invalid_content_class_does_not_mutate_catalog_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "assets" / "fish.spec.json"
            save_json_shard(
                shard,
                {"id": "fish", "name": "鱼", "type": "character"},
            )
            before = shard.read_bytes()
            draft = {
                "project": {"title": "T"},
                "assets": [
                    {
                        "id": "fish",
                        "name": "鱼",
                        "path": "assets/fish.spec.json",
                    }
                ],
            }
            with self.assertRaisesRegex(HostChatError, "content_class"):
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_asset",
                            "match": {"id": "fish"},
                            "set": {"content_class": "bogus"},
                        }
                    ],
                    project_root=root,
                )
            self.assertEqual(shard.read_bytes(), before)

    def test_add_asset_rejects_invalid_content_class(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [{"id": "fish", "name": "鱼", "type": "character"}],
        }
        with self.assertRaisesRegex(HostChatError, "content_class"):
            apply_brief_patches(
                draft,
                [
                    {
                        "op": "add_asset",
                        "value": {
                            "id": "rock",
                            "name": "石头",
                            "type": "texture",
                            "content_class": "bogus",
                        },
                    }
                ],
            )

    def test_add_asset_heals_missing_type_and_chinese_id(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [{"id": "seed", "name": "种子", "type": "texture"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "add_asset",
                    "value": {"name": "主界面_建筑_钓具店"},
                }
            ],
        )
        added = next(item for item in out["assets"] if item.get("name") == "主界面_建筑_钓具店")
        self.assertEqual(added["type"], "texture")
        self.assertRegex(str(added["id"]), r"^tex_[a-z0-9_]+$")

    def test_add_asset_heals_pose_and_background_hints(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [{"id": "seed", "name": "种子", "type": "texture"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {"op": "add_asset", "value": {"name": "鱼_鲫鱼_角色"}},
                {"op": "add_asset", "value": {"name": "鱼_鲫鱼_游动"}},
                {"op": "add_asset", "value": {"name": "水族馆_小型缸_观赏背景"}},
            ],
        )
        by_name = {item["name"]: item for item in out["assets"] if isinstance(item, dict)}
        self.assertEqual(by_name["鱼_鲫鱼_角色"]["type"], "character")
        self.assertRegex(str(by_name["鱼_鲫鱼_角色"]["id"]), r"^char_")
        self.assertEqual(by_name["鱼_鲫鱼_游动"]["type"], "character_pose")
        self.assertRegex(str(by_name["鱼_鲫鱼_游动"]["id"]), r"^pose_")
        self.assertEqual(by_name["水族馆_小型缸_观赏背景"]["type"], "background")
        self.assertRegex(str(by_name["水族馆_小型缸_观赏背景"]["id"]), r"^bg_")

    def test_add_asset_still_rejects_untyped_opaque_name(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [{"id": "seed", "name": "种子", "type": "texture"}],
        }
        with self.assertRaisesRegex(HostChatError, "缺少 type"):
            apply_brief_patches(
                draft,
                [{"op": "add_asset", "value": {"name": "未分类物件"}}],
            )

    def test_asset_name_match_preserves_existing_catalog_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original_shard = root / "assets" / "fish_01.spec.json"
            save_json_shard(
                original_shard,
                {"id": "fish_01", "name": "鱼", "type": "character"},
            )
            draft = {
                "project": {"title": "T"},
                "assets": [
                    {
                        "id": "fish_01",
                        "name": "鱼",
                        "path": "assets/fish_01.spec.json",
                    }
                ],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_asset",
                        "match": {"name": "鱼"},
                        "set": {"description": "updated"},
                    }
                ],
                project_root=root,
            )
            self.assertEqual(out["assets"][0]["id"], "fish_01")
            self.assertEqual(out["assets"][0]["path"], "assets/fish_01.spec.json")
            self.assertEqual(
                json.loads(original_shard.read_text(encoding="utf-8"))["description"],
                "updated",
            )
            self.assertFalse((root / "assets" / "鱼.spec.json").exists())

    def test_generic_scene_upsert_writes_catalog_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "scenes" / "hall.json"
            save_json_shard(
                shard,
                {"id": "hall", "title": "Hall", "notes": "old"},
            )
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_list",
                        "path": "project.scenes",
                        "match": {"id": "hall"},
                        "set": {"notes": "new"},
                    }
                ],
                project_root=root,
            )
            self.assertNotIn("notes", out["project"]["scenes"][0])
            self.assertEqual(
                json.loads(shard.read_text(encoding="utf-8"))["notes"], "new"
            )

    def test_invalid_later_catalog_path_prevents_earlier_shard_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / "scenes" / "hall.json"
            save_json_shard(first, {"id": "hall", "title": "Hall", "notes": "old"})
            before = first.read_bytes()
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        },
                        {
                            "id": "dock",
                            "title": "Dock",
                            "path": "../escape.json",
                        },
                    ],
                },
                "assets": [],
            }
            with self.assertRaises(HostChatError):
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_scene",
                            "match": {"id": "hall"},
                            "set": {"notes": "must not persist"},
                        },
                        {
                            "op": "upsert_scene",
                            "match": {"id": "dock"},
                            "set": {"notes": "invalid target"},
                        },
                    ],
                    project_root=root,
                )
            self.assertEqual(first.read_bytes(), before)

    def test_runtime_write_failure_rolls_back_earlier_shard(self) -> None:
        from brief_shards import upsert_shard_body as real_upsert_shard_body

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hall = root / "scenes" / "hall.json"
            dock = root / "scenes" / "dock.json"
            save_json_shard(hall, {"id": "hall", "title": "Hall", "notes": "old hall"})
            save_json_shard(dock, {"id": "dock", "title": "Dock", "notes": "old dock"})
            before = hall.read_bytes()
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        },
                        {
                            "id": "dock",
                            "title": "Dock",
                            "path": "scenes/dock.json",
                        },
                    ],
                },
                "assets": [],
            }
            calls = 0

            def fail_second_write(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated write failure")
                return real_upsert_shard_body(*args, **kwargs)

            with patch("host_chat.upsert_shard_body", side_effect=fail_second_write):
                with self.assertRaises(OSError):
                    apply_brief_patches(
                        draft,
                        [
                            {
                                "op": "upsert_scene",
                                "match": {"id": "hall"},
                                "set": {"notes": "new hall"},
                            },
                            {
                                "op": "upsert_scene",
                                "match": {"id": "dock"},
                                "set": {"notes": "new dock"},
                            },
                        ],
                        project_root=root,
                    )
            self.assertEqual(hall.read_bytes(), before)

    def test_asset_batch_validates_final_candidate_state(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [{"id": "switch", "name": "开关", "type": "texture"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"id": "switch"},
                    "set": {"states": ["on", "off"]},
                },
                {
                    "op": "upsert_asset",
                    "match": {"id": "switch"},
                    "set": {"content_class": "prop_stateful"},
                },
            ],
        )
        self.assertEqual(out["assets"][0]["states"], ["on", "off"])
        self.assertEqual(out["assets"][0]["content_class"], "prop_stateful")

    def test_dynamic_asset_target_is_rolled_back_after_later_failure(self) -> None:
        from brief_shards import upsert_shard_body as real_upsert_shard_body

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            existing_asset = root / "assets" / "seed.spec.json"
            scene = root / "scenes" / "hall.json"
            save_json_shard(
                existing_asset,
                {"id": "seed", "name": "种子", "type": "texture"},
            )
            save_json_shard(scene, {"id": "hall", "title": "Hall"})
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [
                    {
                        "id": "seed",
                        "name": "种子",
                        "path": "assets/seed.spec.json",
                    }
                ],
            }
            calls = 0

            def fail_scene_write(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("simulated scene failure")
                return real_upsert_shard_body(*args, **kwargs)

            with patch("host_chat.upsert_shard_body", side_effect=fail_scene_write):
                with self.assertRaises(OSError):
                    apply_brief_patches(
                        draft,
                        [
                            {
                                "op": "add_asset",
                                "value": {
                                    "id": "a",
                                    "name": "N",
                                    "type": "texture",
                                },
                            },
                            {
                                "op": "upsert_asset",
                                "match": {"name": "N"},
                                "set": {"usage": "ui"},
                            },
                            {
                                "op": "upsert_scene",
                                "match": {"id": "hall"},
                                "set": {"notes": "fail"},
                            },
                        ],
                        project_root=root,
                    )
            self.assertFalse((root / "assets" / "a.spec.json").exists())
            self.assertFalse((root / "assets" / "N.spec.json").exists())

    def test_batch_asset_name_collision_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a_shard = root / "assets" / "a.spec.json"
            b_shard = root / "assets" / "b.spec.json"
            save_json_shard(a_shard, {"id": "a", "name": "A", "type": "texture"})
            save_json_shard(b_shard, {"id": "b", "name": "B", "type": "texture"})
            before_a = a_shard.read_bytes()
            draft = {
                "project": {"title": "T"},
                "assets": [
                    {"id": "a", "name": "A", "path": "assets/a.spec.json"},
                    {"id": "b", "name": "B", "path": "assets/b.spec.json"},
                ],
            }
            with self.assertRaisesRegex(HostChatError, "歧义|冲突"):
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_asset",
                            "match": {"id": "a"},
                            "set": {"name": "B"},
                        },
                        {
                            "op": "upsert_asset",
                            "match": {"name": "B"},
                            "set": {"states": ["on", "off"]},
                        },
                    ],
                    project_root=root,
                )
            self.assertEqual(a_shard.read_bytes(), before_a)

    def test_catalog_add_asset_creates_shard_and_thin_ref(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "assets" / "seed.spec.json",
                {"id": "seed", "name": "种子", "type": "texture"},
            )
            draft = {
                "project": {"title": "T"},
                "assets": [
                    {
                        "id": "seed",
                        "name": "种子",
                        "path": "assets/seed.spec.json",
                    }
                ],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "add_asset",
                        "value": {
                            "id": "rock",
                            "name": " 石头 ",
                            "type": "texture",
                            "description": "new asset",
                        },
                    }
                ],
                project_root=root,
            )
            added = next(item for item in out["assets"] if item["id"] == "rock")
            self.assertEqual(
                added,
                {
                    "id": "rock",
                    "name": "石头",
                    "path": "assets/rock.spec.json",
                },
            )
            body = json.loads(
                (root / "assets" / "rock.spec.json").read_text(encoding="utf-8")
            )
            self.assertEqual(body["description"], "new asset")
            self.assertEqual(body["name"], "石头")

    def test_catalog_add_then_incremental_upsert_validates_final_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "assets" / "seed.spec.json",
                {"id": "seed", "name": "种子", "type": "texture"},
            )
            draft = {
                "project": {"title": "T"},
                "assets": [
                    {
                        "id": "seed",
                        "name": "种子",
                        "path": "assets/seed.spec.json",
                    }
                ],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "add_asset",
                        "value": {
                            "id": "rock",
                            "name": "石头",
                            "type": "texture",
                        },
                    },
                    {
                        "op": "upsert_asset",
                        "match": {"name": "石头"},
                        "set": {"usage": "decoration"},
                    },
                ],
                project_root=root,
            )
            added = next(item for item in out["assets"] if item["id"] == "rock")
            self.assertNotIn("usage", added)
            body = json.loads(
                (root / "assets" / "rock.spec.json").read_text(encoding="utf-8")
            )
            self.assertEqual(body["usage"], "decoration")

    def test_generic_scene_upsert_resolves_match_name_to_id(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "hall", "title": "Hall"}],
            },
            "assets": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_list",
                    "path": "project.scenes",
                    "match": {"name": "hall"},
                    "set": {"notes": "x"},
                }
            ],
        )
        self.assertEqual(out["project"]["scenes"][0]["id"], "hall")
        self.assertEqual(out["project"]["scenes"][0]["notes"], "x")

    def test_invalid_new_catalog_id_mints_stable_scene_without_escape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hall = root / "scenes" / "hall.json"
            save_json_shard(hall, {"id": "hall", "title": "Hall"})
            before = hall.read_bytes()
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "../escape"},
                        "set": {"title": "Escape"},
                    }
                ],
                project_root=root,
            )
            rows = out["project"]["scenes"]
            self.assertEqual(len(rows), 2)
            added = next(item for item in rows if item["id"] != "hall")
            self.assertRegex(str(added["id"]), r"^scene_[a-z0-9_]+$")
            self.assertNotIn("/", str(added["id"]))
            self.assertNotIn("..", str(added["id"]))
            self.assertEqual(added["title"], "Escape")
            self.assertEqual(hall.read_bytes(), before)
            for path in root.rglob("*"):
                if path.is_file():
                    self.assertTrue(path.resolve().is_relative_to(root.resolve()))

    def test_asset_identity_conflicts_are_case_insensitive(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {
                    "id": "rod",
                    "name": "Rod",
                    "type": "texture",
                    "description": "original",
                }
            ],
        }
        for value in (
            {"id": "ROD", "name": "Other", "type": "character"},
            {"id": "other", "name": "rod", "type": "character"},
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(HostChatError, "冲突|稳定 id"):
                    apply_brief_patches(
                        draft,
                        [{"op": "add_asset", "value": value}],
                    )

    def test_new_asset_upsert_preserves_match_name(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {"id": "seed", "name": "Seed", "type": "texture"},
            ],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"id": "new", "name": "Display"},
                    "set": {"type": "texture"},
                }
            ],
        )
        added = next(item for item in out["assets"] if item["id"] == "new")
        self.assertEqual(added["name"], "Display")

    def test_asset_identity_rejects_cross_field_conflicts(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {"id": "rod", "name": "bait", "type": "texture"},
                {"id": "hook", "name": "worm", "type": "texture"},
            ],
        }
        conflicting_patches = (
            {
                "op": "add_asset",
                "value": {"id": "bait", "name": "hook", "type": "texture"},
            },
            {
                "op": "add_asset",
                "value": {"id": "hook", "name": "ROD", "type": "texture"},
            },
            {
                "op": "upsert_asset",
                "match": {"id": "rod"},
                "set": {"name": "HOOK"},
            },
        )
        for patch_value in conflicting_patches:
            with self.subTest(patch=patch_value):
                with self.assertRaisesRegex(HostChatError, "冲突|歧义"):
                    apply_brief_patches(draft, [patch_value])

    def test_new_asset_upsert_heals_noncanonical_id_without_escape_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "assets" / "seed.spec.json",
                {"id": "seed", "name": "Seed", "type": "texture"},
            )
            draft = {
                "project": {"title": "T"},
                "assets": [
                    {
                        "id": "seed",
                        "name": "Seed",
                        "path": "assets/seed.spec.json",
                    }
                ],
            }
            for invalid_id in ("A", "a/b", "two words", "../escape"):
                with self.subTest(asset_id=invalid_id):
                    local = copy.deepcopy(draft)
                    out = apply_brief_patches(
                        local,
                        [
                            {
                                "op": "upsert_asset",
                                "match": {
                                    "id": invalid_id,
                                    "name": f"Item {invalid_id}",
                                },
                                "set": {"type": "texture"},
                            }
                        ],
                        project_root=root,
                    )
                    added = next(
                        item
                        for item in out["assets"]
                        if isinstance(item, dict) and item.get("id") != "seed"
                    )
                    self.assertRegex(str(added["id"]), r"^[a-z][a-z0-9_]*$")
                    self.assertNotIn("/", str(added["id"]))
                    self.assertNotIn("..", str(added["id"]))
            self.assertFalse((root / "assets" / "escape.spec.json").is_file())
            self.assertTrue((root / "assets" / "seed.spec.json").is_file())

    def test_upsert_asset_heals_new_chinese_name_without_type(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [{"id": "seed", "name": "种子", "type": "texture"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"name": "主界面_建筑_钓具店"},
                    "set": {"description": "shop"},
                }
            ],
        )
        added = next(
            item
            for item in out["assets"]
            if isinstance(item, dict) and item.get("name") == "主界面_建筑_钓具店"
        )
        self.assertEqual(added["type"], "texture")
        self.assertRegex(str(added["id"]), r"^tex_[a-z0-9_]+$")

    def test_upsert_scene_resolves_chinese_title_to_existing_id(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "main_hub", "title": "主界面", "notes": "old"}],
            },
            "assets": [{"id": "a", "name": "a", "type": "texture"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_scene",
                    "match": {"id": "主界面"},
                    "set": {"notes": "new"},
                }
            ],
        )
        self.assertEqual(len(out["project"]["scenes"]), 1)
        self.assertEqual(out["project"]["scenes"][0]["id"], "main_hub")
        self.assertEqual(out["project"]["scenes"][0]["notes"], "new")

    def test_upsert_scene_mints_id_for_unknown_chinese_name(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "main_hub", "title": "主界面"}],
            },
            "assets": [{"id": "a", "name": "a", "type": "texture"}],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_scene",
                    "match": {"id": "图鉴亭"},
                    "set": {"summary": "codex pavilion"},
                }
            ],
        )
        rows = out["project"]["scenes"]
        self.assertEqual(len(rows), 2)
        added = next(item for item in rows if item["id"] != "main_hub")
        self.assertRegex(str(added["id"]), r"^scene_[a-z0-9_]+$")
        self.assertEqual(added["title"], "图鉴亭")
        self.assertEqual(added["summary"], "codex pavilion")

    def test_inline_asset_nested_updates_use_deep_merge(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {
                    "id": "panel",
                    "name": "Panel",
                    "type": "texture",
                    "display_size": {"width": 100, "height": 200},
                }
            ],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"id": "panel"},
                    "set": {"display_size": {"width": 300}},
                },
                {
                    "op": "upsert_asset",
                    "match": {"id": "panel"},
                    "set": {"display_size": {"height": 400}},
                },
            ],
        )
        self.assertEqual(
            out["assets"][0]["display_size"],
            {"width": 300, "height": 400},
        )

    def test_new_asset_upsert_rejects_conflicting_or_blank_name(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {"id": "rod", "name": "bait", "type": "texture"},
            ],
        }
        patches = (
            {
                "op": "upsert_asset",
                "match": {"id": "hook"},
                "set": {"name": "BAIT", "type": "texture"},
            },
            {
                "op": "upsert_asset",
                "match": {"id": "hook"},
                "set": {"name": "   ", "type": "texture"},
            },
            {
                "op": "add_asset",
                "value": {"id": "hook", "name": "   ", "type": "texture"},
            },
            {
                "op": "upsert_asset",
                "match": {"id": "hook", "name": "   "},
                "set": {"type": "texture"},
            },
        )
        for patch_value in patches:
            with self.subTest(patch=patch_value):
                with self.assertRaisesRegex(HostChatError, "冲突|不能为空"):
                    apply_brief_patches(draft, [patch_value])

    def test_id_only_new_asset_upsert_uses_id_as_name(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {"id": "seed", "name": "Seed", "type": "texture"},
            ],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"id": "hook"},
                    "set": {"type": "texture"},
                }
            ],
        )
        added = next(item for item in out["assets"] if item["id"] == "hook")
        self.assertEqual(added["name"], "hook")

    def test_inline_add_asset_trims_name(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {"id": "seed", "name": "Seed", "type": "texture"},
            ],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "add_asset",
                    "value": {
                        "id": "hook",
                        "name": " Hook ",
                        "type": "texture",
                    },
                }
            ],
        )
        added = next(item for item in out["assets"] if item["id"] == "hook")
        self.assertEqual(added["name"], "Hook")

    def test_inline_asset_rename_trims_name(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {"id": "seed", "name": "Seed", "type": "texture"},
            ],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_asset",
                    "match": {"id": "seed"},
                    "set": {"name": " Renamed "},
                }
            ],
        )
        self.assertEqual(out["assets"][0]["name"], "Renamed")

    def test_scene_upsert_heals_case_variant_id_to_existing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "scenes" / "hall.json"
            save_json_shard(
                shard,
                {"id": "hall", "title": "Hall", "notes": "old"},
            )
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "HALL"},
                        "set": {"notes": "updated"},
                    }
                ],
                project_root=root,
            )
            self.assertEqual(len(out["project"]["scenes"]), 1)
            self.assertEqual(out["project"]["scenes"][0]["id"], "hall")
            body = json.loads(shard.read_text(encoding="utf-8"))
            self.assertEqual(body["notes"], "updated")

    def test_scene_upsert_mints_id_for_noncanonical_new_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "scenes" / "hall.json"
            save_json_shard(
                shard,
                {"id": "hall", "title": "Hall", "notes": "old"},
            )
            before = shard.read_bytes()
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            for scene_id in ("two words", "../escape"):
                with self.subTest(scene_id=scene_id):
                    local = copy.deepcopy(draft)
                    out = apply_brief_patches(
                        local,
                        [
                            {
                                "op": "upsert_scene",
                                "match": {"id": scene_id},
                                "set": {"notes": "minted"},
                            }
                        ],
                        project_root=root,
                    )
                    rows = out["project"]["scenes"]
                    self.assertEqual(len(rows), 2)
                    added = next(item for item in rows if item["id"] != "hall")
                    added_id = str(added["id"])
                    self.assertRegex(added_id, r"^scene_[a-z0-9_]+$")
                    self.assertNotIn("/", added_id)
                    self.assertEqual(shard.read_bytes(), before)
                    new_shard = root / "scenes" / f"{added_id}.json"
                    self.assertTrue(new_shard.is_file())
                    body = json.loads(new_shard.read_text(encoding="utf-8"))
                    self.assertEqual(body.get("notes"), "minted")

    def test_scene_set_rejects_nested_index_fields(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "hall", "title": "Hall"}],
            },
            "assets": [],
        }
        for field in ("id.value", "title.text", "path.value"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(HostChatError, "稳定字段|子路径"):
                    apply_brief_patches(
                        draft,
                        [
                            {
                                "op": "set",
                                "path": f"project.scenes[id=hall].{field}",
                                "value": "broken",
                            }
                        ],
                    )

    def test_scene_set_heals_case_variant_selector_id(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "hall", "title": "Hall"}],
            },
            "assets": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "set",
                    "path": "project.scenes[id=HALL].notes",
                    "value": "updated",
                }
            ],
        )
        self.assertEqual(len(out["project"]["scenes"]), 1)
        self.assertEqual(out["project"]["scenes"][0]["id"], "hall")
        self.assertEqual(out["project"]["scenes"][0]["notes"], "updated")

    def test_scene_set_resolves_chinese_title_selector(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "main_hub", "title": "主界面"}],
            },
            "assets": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "set",
                    "path": "project.scenes[id=主界面].notes",
                    "value": "hub notes",
                }
            ],
        )
        self.assertEqual(len(out["project"]["scenes"]), 1)
        self.assertEqual(out["project"]["scenes"][0]["id"], "main_hub")
        self.assertEqual(out["project"]["scenes"][0]["notes"], "hub notes")

    def test_scene_set_unknown_chinese_selector_does_not_mint(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [{"id": "main_hub", "title": "主界面"}],
            },
            "assets": [],
        }
        with self.assertRaisesRegex(HostChatError, "set 只改现有|找不到"):
            apply_brief_patches(
                draft,
                [
                    {
                        "op": "set",
                        "path": "project.scenes[id=图鉴亭].notes",
                        "value": "should not mint",
                    }
                ],
            )

    def test_upsert_graph_resolves_chinese_character_name(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {
                    "id": "char_carp",
                    "name": "鲫鱼",
                    "type": "character",
                }
            ],
            "animation_graphs": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_graph",
                    "match": {"character_asset": "鲫鱼"},
                    "set": {"clips": ["swim"]},
                }
            ],
        )
        graphs = out["animation_graphs"]
        self.assertEqual(len(graphs), 1)
        self.assertEqual(graphs[0]["character_asset"], "char_carp")
        self.assertEqual(graphs[0]["clips"], ["swim"])

    def test_upsert_graph_unknown_chinese_character_fails(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {"id": "char_carp", "name": "鲫鱼", "type": "character"},
            ],
            "animation_graphs": [],
        }
        with self.assertRaisesRegex(HostChatError, "upsert_graph 找不到角色"):
            apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_graph",
                        "match": {"character_asset": "真鲷"},
                        "set": {"clips": ["swim"]},
                    }
                ],
            )

    def test_inline_scene_nested_updates_use_deep_merge(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [
                    {
                        "id": "hall",
                        "title": "Hall",
                        "camera": {"zoom": 1, "pan": 2},
                    }
                ],
            },
            "assets": [],
        }
        out = apply_brief_patches(
            draft,
            [
                {
                    "op": "upsert_scene",
                    "match": {"id": "hall"},
                    "set": {"camera": {"zoom": 3}},
                }
            ],
        )
        self.assertEqual(
            out["project"]["scenes"][0]["camera"],
            {"zoom": 3, "pan": 2},
        )

    def test_catalog_new_asset_upsert_requires_project_root(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {
                    "id": "seed",
                    "name": "Seed",
                    "path": "assets/seed.spec.json",
                }
            ],
        }
        with self.assertRaisesRegex(HostChatError, "project_root"):
            apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_asset",
                        "match": {"id": "rock"},
                        "set": {"type": "texture"},
                    }
                ],
            )

    def test_catalog_scene_upsert_requires_project_root(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "scenes": [
                    {
                        "id": "hall",
                        "title": "Hall",
                        "path": "scenes/hall.json",
                    }
                ],
            },
            "assets": [],
        }
        with self.assertRaisesRegex(HostChatError, "project_root"):
            apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "hall"},
                        "set": {"notes": "new"},
                    }
                ],
            )

    def test_catalog_scene_title_set_updates_index_and_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "scenes" / "hall.json"
            save_json_shard(shard, {"id": "hall", "title": "Old"})
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Old",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "set",
                        "path": "project.scenes[id=hall].title",
                        "value": "New",
                    }
                ],
                project_root=root,
            )
            self.assertEqual(out["project"]["scenes"][0]["title"], "New")
            self.assertEqual(
                json.loads(shard.read_text(encoding="utf-8"))["title"],
                "New",
            )

    def test_stale_catalog_draft_does_not_revert_committed_title(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "scenes" / "hall.json"
            save_json_shard(
                shard,
                {"id": "hall", "title": "Hall", "notes": "old"},
            )
            stale_draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            apply_brief_patches(
                stale_draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "hall"},
                        "set": {"title": "Renamed"},
                    }
                ],
                project_root=root,
            )
            out = apply_brief_patches(
                stale_draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "hall"},
                        "set": {"notes": "second"},
                    }
                ],
                project_root=root,
            )
            body = json.loads(shard.read_text(encoding="utf-8"))
            self.assertEqual(body["title"], "Renamed")
            self.assertEqual(out["project"]["scenes"][0]["title"], "Renamed")

    def test_stale_mixed_catalog_inline_entry_preserves_committed_title(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "scenes" / "dock.json",
                {"id": "dock", "title": "Dock"},
            )
            stale_draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "notes": "old",
                        },
                        {
                            "id": "dock",
                            "title": "Dock",
                            "path": "scenes/dock.json",
                        },
                    ],
                },
                "assets": [],
            }
            apply_brief_patches(
                stale_draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "hall"},
                        "set": {"title": "Renamed"},
                    }
                ],
                project_root=root,
            )
            out = apply_brief_patches(
                stale_draft,
                [
                    {
                        "op": "upsert_scene",
                        "match": {"id": "hall"},
                        "set": {"notes": "second"},
                    }
                ],
                project_root=root,
            )
            body = json.loads(
                (root / "scenes" / "hall.json").read_text(encoding="utf-8")
            )
            self.assertEqual(body["title"], "Renamed")
            self.assertEqual(out["project"]["scenes"][0]["title"], "Renamed")

    def test_asset_schema_preflight_uses_existing_default_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "scenes" / "hall.json",
                {"id": "hall", "title": "Hall"},
            )
            orphan = root / "assets" / "rock.spec.json"
            save_json_shard(
                orphan,
                {
                    "id": "rock",
                    "name": "Rock",
                    "type": "texture",
                    "content_class": "bogus",
                },
            )
            before = orphan.read_bytes()
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            with self.assertRaisesRegex(HostChatError, "content_class"):
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_asset",
                            "match": {"id": "rock", "name": "Rock"},
                            "set": {"type": "texture"},
                        }
                    ],
                    project_root=root,
                )
            self.assertEqual(orphan.read_bytes(), before)

    def test_mixed_asset_write_preserves_inline_name_when_shard_lacks_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "scenes" / "hall.json",
                {"id": "hall", "title": "Hall"},
            )
            asset_shard = root / "assets" / "rock.spec.json"
            save_json_shard(asset_shard, {"id": "rock", "type": "texture"})
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [
                    {
                        "id": "rock",
                        "name": "Current Rock",
                        "type": "texture",
                    }
                ],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_asset",
                        "match": {"id": "rock"},
                        "set": {"usage": "decor"},
                    }
                ],
                project_root=root,
            )
            body = json.loads(asset_shard.read_text(encoding="utf-8"))
            self.assertEqual(body["name"], "Current Rock")
            self.assertEqual(out["assets"][0]["name"], "Current Rock")

    def test_stale_catalog_asset_names_refresh_before_identity_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "assets" / "a.spec.json",
                {"id": "a", "name": "B", "type": "texture"},
            )
            save_json_shard(
                root / "assets" / "b.spec.json",
                {"id": "b", "name": "C", "type": "texture"},
            )
            stale_draft = {
                "project": {"title": "T"},
                "assets": [
                    {"id": "a", "name": "A", "path": "assets/a.spec.json"},
                    {"id": "b", "name": "B", "path": "assets/b.spec.json"},
                ],
            }
            out = apply_brief_patches(
                stale_draft,
                [
                    {
                        "op": "upsert_asset",
                        "match": {"id": "a"},
                        "set": {"usage": "updated"},
                    }
                ],
                project_root=root,
            )
            self.assertEqual(
                [(item["id"], item["name"]) for item in out["assets"]],
                [("a", "B"), ("b", "C")],
            )

    def test_id_only_upsert_preserves_existing_orphan_shard_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_json_shard(
                root / "scenes" / "hall.json",
                {"id": "hall", "title": "Hall"},
            )
            asset_shard = root / "assets" / "rock.spec.json"
            save_json_shard(
                asset_shard,
                {"id": "rock", "name": "Display Rock", "type": "texture"},
            )
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            out = apply_brief_patches(
                draft,
                [
                    {
                        "op": "upsert_asset",
                        "match": {"id": "rock"},
                        "set": {"usage": "decor"},
                    }
                ],
                project_root=root,
            )
            body = json.loads(asset_shard.read_text(encoding="utf-8"))
            self.assertEqual(body["name"], "Display Rock")
            self.assertEqual(out["assets"][0]["name"], "Display Rock")

    def test_catalog_shard_id_mismatch_is_rejected_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "scenes" / "hall.json"
            save_json_shard(
                shard,
                {"id": "other", "title": "Other", "notes": "foreign"},
            )
            before = shard.read_bytes()
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [],
            }
            with self.assertRaisesRegex(HostChatError, "shard id|身份"):
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_scene",
                            "match": {"id": "hall"},
                            "set": {"notes": "patched"},
                        }
                    ],
                    project_root=root,
                )
            self.assertEqual(shard.read_bytes(), before)

    def test_generic_set_rejects_traversing_existing_non_object(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "controls": {"cast": ["Click", "Space"]},
            },
            "assets": [],
        }
        with self.assertRaisesRegex(HostChatError, "非对象|non-object"):
            apply_brief_patches(
                draft,
                [
                    {
                        "op": "set",
                        "path": "project.controls.cast.primary",
                        "value": "Click",
                    }
                ],
            )
        self.assertEqual(draft["project"]["controls"]["cast"], ["Click", "Space"])

    def test_generic_set_batch_rejects_traversing_new_non_object(self) -> None:
        draft = {"project": {"title": "T"}, "assets": []}
        with self.assertRaises(HostChatError):
            apply_brief_patches(
                draft,
                [
                    {"op": "set", "path": "project.mode", "value": []},
                    {
                        "op": "set",
                        "path": "project.mode.primary",
                        "value": "x",
                    },
                ],
            )

    def test_same_project_patch_transactions_are_serialized(self) -> None:
        from brief_shards import upsert_shard_body as real_upsert_shard_body

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hall = root / "scenes" / "hall.json"
            dock = root / "scenes" / "dock.json"
            save_json_shard(hall, {"id": "hall", "title": "Hall", "notes": "old"})
            save_json_shard(dock, {"id": "dock", "title": "Dock", "notes": "old"})
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        },
                        {
                            "id": "dock",
                            "title": "Dock",
                            "path": "scenes/dock.json",
                        },
                    ],
                },
                "assets": [],
            }
            a_wrote = threading.Event()
            allow_a_failure = threading.Event()
            b_entered_write = threading.Event()
            errors: list[Exception] = []

            def controlled_upsert(*args, **kwargs):
                entry_id = str(args[3])
                if threading.current_thread().name == "patch-a":
                    if entry_id == "hall":
                        result = real_upsert_shard_body(*args, **kwargs)
                        a_wrote.set()
                        allow_a_failure.wait(timeout=2)
                        return result
                    raise OSError("simulated later failure")
                b_entered_write.set()
                return real_upsert_shard_body(*args, **kwargs)

            def run_a() -> None:
                try:
                    apply_brief_patches(
                        draft,
                        [
                            {
                                "op": "upsert_scene",
                                "match": {"id": "hall"},
                                "set": {"notes": "A"},
                            },
                            {
                                "op": "upsert_scene",
                                "match": {"id": "dock"},
                                "set": {"notes": "fail"},
                            },
                        ],
                        project_root=root,
                    )
                except Exception as exc:
                    errors.append(exc)

            def run_b() -> None:
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_scene",
                            "match": {"id": "hall"},
                            "set": {"notes": "B committed"},
                        }
                    ],
                    project_root=root,
                )

            with patch("host_chat.upsert_shard_body", side_effect=controlled_upsert):
                thread_a = threading.Thread(target=run_a, name="patch-a")
                thread_a.start()
                self.assertTrue(a_wrote.wait(timeout=2))
                thread_b = threading.Thread(target=run_b, name="patch-b")
                thread_b.start()
                b_started_before_release = b_entered_write.wait(timeout=0.1)
                allow_a_failure.set()
                thread_a.join(timeout=2)
                thread_b.join(timeout=2)

            self.assertFalse(b_started_before_release)
            self.assertTrue(errors)
            self.assertEqual(
                json.loads(hall.read_text(encoding="utf-8"))["notes"],
                "B committed",
            )

    def test_later_invalid_patch_prevents_earlier_shard_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scene_shard = root / "scenes" / "hall.json"
            asset_shard = root / "assets" / "fish.spec.json"
            save_json_shard(
                scene_shard,
                {"id": "hall", "title": "Hall", "notes": "old"},
            )
            save_json_shard(
                asset_shard,
                {"id": "fish", "name": "鱼", "type": "character"},
            )
            before = scene_shard.read_bytes()
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {
                            "id": "hall",
                            "title": "Hall",
                            "path": "scenes/hall.json",
                        }
                    ],
                },
                "assets": [
                    {
                        "id": "fish",
                        "name": "鱼",
                        "path": "assets/fish.spec.json",
                    }
                ],
            }
            with self.assertRaises(HostChatError):
                apply_brief_patches(
                    draft,
                    [
                        {
                            "op": "upsert_scene",
                            "match": {"id": "hall"},
                            "set": {"notes": "must not persist"},
                        },
                        {
                            "op": "upsert_asset",
                            "match": {"id": "fish"},
                            "set": {"type": "not_a_real_type"},
                        },
                    ],
                    project_root=root,
                )
            self.assertEqual(scene_shard.read_bytes(), before)

    def test_load_project_draft_prefers_draft_json_over_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "fish"
            proj.mkdir(parents=True)
            (proj / "brief.json").write_text(
                json.dumps(
                    {
                        "project": {"title": "Exported Locked", "genre": "sim"},
                        "assets": [{"name": "old", "type": "prop", "usage": "x"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (proj / "brief.draft.json").write_text(
                json.dumps(
                    {
                        "project": {"title": "Working Draft Open", "genre": "sim"},
                        "assets": [{"name": "new", "type": "prop", "usage": "x"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            loaded = load_project_draft_from_disk(
                "projects/fish/brief.json",
                repo_root=root,
                workspace=root,
            )
            assert loaded is not None
            self.assertEqual(loaded["project"]["title"], "Working Draft Open")
            self.assertEqual(loaded["assets"][0]["name"], "new")

    def test_reconcile_makeability_closes_gaps_and_stales_review(self) -> None:
        session = new_session("close-gaps")
        draft = {
            "project": {
                "title": "Fish",
                "description": "desc",
                "genre": "sim",
                "gameplay_loop": "cast",
                "session_goal": "endless",
            },
            "assets": [{"name": "rod", "type": "prop", "usage": "player"}],
        }
        session["draft_brief"] = draft
        session["makeability_review"] = {
            "schema_version": 1,
            "reviewed_at": "2026-08-04T00:00:00+00:00",
            "draft_fingerprint": draft_fingerprint(draft),
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "question": "如何解锁水族馆？",
                    "why_blocking": "入口不明",
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        closed, msg = reconcile_makeability_after_draft_write(
            session,
            closed_ids=["aquarium_unlock_flow"],
            assistant_message="好，aquarium_unlock_flow 按 B 拍板关闭。",
        )
        self.assertEqual(closed, ["aquarium_unlock_flow"])
        self.assertEqual(session["makeability_review"]["intent_gaps"], [])
        self.assertFalse(session["ready_to_export"])
        self.assertIn("制作审查", msg)
        st = session_status(session)
        self.assertFalse(st["makeability_fingerprint_match"])
        self.assertEqual(st["intent_count"], 0)
        payload = _build_user_payload(session, "chat")
        latest = payload["latest_makeability_review"]
        self.assertFalse(latest["fingerprint_match"])
        self.assertEqual(latest["intent_gaps"], [])

    def test_apply_parsed_closes_single_intent_gap_on_patch(self) -> None:
        session = new_session("patch-close")
        draft = {
            "project": {
                "title": "Fish",
                "description": "A fishing sim.",
                "genre": "sim",
                "gameplay_loop": "cast sell",
                "session_goal": "endless",
                "systems": [
                    {"id": "aquarium", "title": "Aquarium", "notes": "locked until purchased"},
                ],
            },
            "assets": [{"name": "rod", "type": "prop", "usage": "player"}],
        }
        session["draft_brief"] = draft
        session["makeability_review"] = {
            "schema_version": 1,
            "reviewed_at": "2026-08-04T00:00:00+00:00",
            "draft_fingerprint": draft_fingerprint(draft),
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "question": "如何解锁？",
                    "why_blocking": "x",
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [{"id": "economy", "topic": "numbers"}],
            "suggested_defaults": [],
        }
        set_session_focus(session, {"kind": "intent_gap", "id": "aquarium_unlock_flow"})
        parsed = {
            "assistant_message": "已拍板写进草稿：水族馆开局可进。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {
                        "op": "upsert_system",
                        "match": {"id": "aquarium"},
                        "set": {"notes": "unlocked from the start"},
                    }
                ],
                "closed_intent_gap_ids": ["aquarium_unlock_flow"],
            },
            "ready_to_export": False,
        }
        _apply_parsed(session, parsed, "chat")
        self.assertIn(
            "unlocked from the start",
            session["draft_brief"]["project"]["systems"][0]["notes"],
        )
        self.assertEqual(session["makeability_review"]["intent_gaps"], [])
        self.assertEqual(session_status(session)["intent_count"], 0)

    def test_answer_makeability_gaps_applies_closer_patches(self) -> None:
        from host_chat import answer_makeability_gaps

        session = new_session("gap-answer")
        draft = {
            "project": {
                "title": "Fish",
                "description": "d",
                "genre": "sim",
                "gameplay_loop": "cast",
                "session_goal": "endless",
                "systems": [{"id": "aquarium", "notes": "locked until purchased"}],
            },
            "assets": [{"name": "rod", "type": "prop", "usage": "player"}],
        }
        session["draft_brief"] = draft
        session["makeability_review"] = {
            "schema_version": 1,
            "reviewed_at": "t",
            "draft_fingerprint": draft_fingerprint(draft),
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "question": "如何解锁？",
                    "why_blocking": "x",
                    "choices": ["A", "B 开局可进"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        closer = {
            "assistant_message": "已按 B 写入。",
            "brief_patches": [
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {"notes": "unlocked from the start"},
                }
            ],
        }
        verifier = {
            "decision_checks": [
                {
                    "decision_key": "gap.aquarium_unlock_flow",
                    "gap_id": "aquarium_unlock_flow",
                    "status": "satisfied",
                    "evidence_paths": ["project.systems[id=aquarium].notes"],
                }
            ]
        }

        def _side(**kwargs):
            messages = kwargs["messages"]
            if "Makeability Verifier" in messages[0]["content"]:
                return json.dumps(verifier, ensure_ascii=False)
            return json.dumps(closer, ensure_ascii=False)

        with patch(
            "host_chat.chat_text_completion",
            side_effect=_side,
        ), patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(
                session,
                [{"gap_id": "aquarium_unlock_flow", "choice": "B 开局可进"}],
                config={},
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["closed_ids"], ["aquarium_unlock_flow"])
        self.assertIn(
            "unlocked from the start",
            session["draft_brief"]["project"]["systems"][0]["notes"],
        )
        self.assertEqual(session["makeability_review"]["intent_gaps"], [])

    def test_answer_makeability_closer_and_verifier_see_catalog_shard_notes(self) -> None:
        """Catalog systems live in shards; closer/verifier must hydrate before LLM."""
        from host_chat import answer_makeability_gaps

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "systems").mkdir()
            save_json_shard(
                root / "systems" / "aquarium.json",
                {
                    "id": "aquarium",
                    "title": "Aquarium",
                    "notes": "SHARD_LOCKED_UNTIL_PURCHASE",
                },
            )
            draft = {
                "project": {
                    "title": "Fish",
                    "description": "d",
                    "genre": "sim",
                    "gameplay_loop": "cast",
                    "session_goal": "endless",
                    "systems": [
                        {
                            "id": "aquarium",
                            "title": "Aquarium",
                            "path": "systems/aquarium.json",
                        }
                    ],
                },
                "assets": [{"name": "rod", "type": "prop", "usage": "player"}],
            }
            session = new_session("gap-hydrate")
            session["draft_brief"] = draft
            session["makeability_review"] = {
                "schema_version": 1,
                "reviewed_at": "t",
                "draft_fingerprint": draft_fingerprint(draft),
                "intent_gaps": [
                    {
                        "id": "aquarium_unlock_flow",
                        "question": "如何解锁？",
                        "why_blocking": "x",
                        "choices": ["A", "B 开局可进"],
                        "write_paths": ["project.systems[id=aquarium].notes"],
                    }
                ],
                "detail_gaps": [],
                "suggested_defaults": [],
            }
            closer = {
                "assistant_message": "已按 B 写入。",
                "brief_patches": [
                    {
                        "op": "upsert_system",
                        "match": {"id": "aquarium"},
                        "set": {"notes": "unlocked from the start"},
                    }
                ],
            }
            verifier = {
                "decision_checks": [
                    {
                        "decision_key": "gap.aquarium_unlock_flow",
                        "gap_id": "aquarium_unlock_flow",
                        "status": "satisfied",
                        "evidence_paths": ["project.systems[id=aquarium].notes"],
                    }
                ]
            }
            seen: list[dict] = []

            def _side(**kwargs):
                messages = kwargs["messages"]
                user = json.loads(messages[1]["content"])
                seen.append(user)
                if "Makeability Verifier" in messages[0]["content"]:
                    return json.dumps(verifier, ensure_ascii=False)
                return json.dumps(closer, ensure_ascii=False)

            with patch(
                "host_chat.chat_text_completion",
                side_effect=_side,
            ), patch(
                "host_chat.resolve_host_api_settings",
                return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
            ), patch(
                "host_chat._project_root_for_session",
                return_value=root,
            ):
                result = answer_makeability_gaps(
                    session,
                    [{"gap_id": "aquarium_unlock_flow", "choice": "B 开局可进"}],
                    config={},
                )
            self.assertTrue(result["ok"])
            self.assertGreaterEqual(len(seen), 2)
            closer_draft = seen[0].get("current_draft_brief") or {}
            closer_systems = (closer_draft.get("project") or {}).get("systems") or []
            self.assertEqual(closer_systems[0].get("notes"), "SHARD_LOCKED_UNTIL_PURCHASE")
            verifier_draft = seen[1].get("candidate_draft_brief") or {}
            verifier_systems = (verifier_draft.get("project") or {}).get("systems") or []
            self.assertEqual(verifier_systems[0].get("notes"), "unlocked from the start")
            # Session catalog stays thin; body lives on disk.
            self.assertNotIn("notes", session["draft_brief"]["project"]["systems"][0])
            body = json.loads((root / "systems" / "aquarium.json").read_text(encoding="utf-8"))
            self.assertEqual(body["notes"], "unlocked from the start")

    def test_apply_parsed_prefers_patches_over_thin_full_draft(self) -> None:
        session = new_session("patch-chat")
        session["draft_brief"] = {
            "project": {
                "title": "Fish",
                "description": "A " + ("rich loop. " * 30),
                "genre": "sim",
            },
            "assets": [
                {"id": "rod", "name": "rod", "type": "icon_kit"},
                {"id": "lake", "name": "lake", "type": "background"},
            ],
        }
        long_desc = session["draft_brief"]["project"]["description"]
        set_session_focus(session, {"kind": "asset", "id": "rod"})
        parsed = {
            "assistant_message": "已把审查的两点写进草稿。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "draft_brief": {
                    "project": {"title": "Fish", "description": "thin"},
                    "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
                },
                "brief_patches": [
                    {"op": "set", "path": "project.session_goal", "value": "Catch fish."},
                    {
                        "op": "upsert_asset",
                        "match": {"id": "rod"},
                        "set": {"usage": "ui_icon"},
                    },
                ],
            },
            "ready_to_export": False,
        }
        _apply_parsed(session, parsed, "chat")
        draft = session["draft_brief"]
        self.assertEqual(draft["project"]["description"], long_desc)
        self.assertEqual(draft["project"]["session_goal"], "Catch fish.")
        self.assertEqual(len(draft["assets"]), 2)
        self.assertEqual(draft["assets"][0].get("usage"), "ui_icon")
        self.assertFalse(session.get("_talk_without_write"))
        self.assertNotIn("只说不写", session["messages"][-1]["content"])

    def test_apply_parsed_strips_scene_bodies_on_full_merge(self) -> None:
        session = new_session("strip-struct-merge")
        session["draft_brief"] = {
            "project": {
                "title": "Fish",
                "scenes": [
                    {"id": "lake", "title": "湖面", "path": "scenes/lake.json"},
                ],
            },
            "assets": [],
        }
        parsed = {
            "assistant_message": "更新了标题。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "draft_brief": {
                    "project": {
                        "title": "Fish 2",
                        "scenes": [
                            {
                                "id": "lake",
                                "title": "湖面",
                                "summary": "模型塞进来的场景正文",
                            }
                        ],
                    }
                }
            },
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        self.assertEqual(session["draft_brief"]["project"]["title"], "Fish 2")
        scenes = session["draft_brief"]["project"]["scenes"]
        self.assertEqual(len(scenes), 1)
        self.assertNotIn("summary", scenes[0])
        self.assertTrue(session.get("_rewrite_needs_patches"))
        self.assertFalse(session.get("_rewrite_retry_now"))
        self.assertNotIn("整稿合并已忽略结构正文", out["assistant_message"])
        self.assertNotIn("请改用 brief_patches", out["assistant_message"])

    def test_apply_parsed_commit_brief_strips_scene_bodies(self) -> None:
        session = new_session("strip-commit")
        session["draft_brief"] = {
            "project": {
                "title": "Fish",
                "description": "d",
                "genre": "sim",
                "gameplay_loop": "cast",
                "session_goal": "g",
                "scenes": [
                    {"id": "lake", "title": "湖面", "path": "scenes/lake.json"},
                ],
            },
            "assets": [{"id": "rod", "name": "rod", "type": "prop", "usage": "player"}],
        }
        parsed = {
            "assistant_message": "落实稿。",
            "choices": [],
            "mode": "commit_brief",
            "intent_hint": "none",
            "artifact": {
                "draft_brief": {
                    "project": {
                        "title": "Fish",
                        "description": "d",
                        "genre": "sim",
                        "gameplay_loop": "cast",
                        "session_goal": "g",
                        "scenes": [
                            {
                                "id": "lake",
                                "title": "湖面",
                                "notes": "COMMIT_FAT_BODY",
                            }
                        ],
                    },
                    "assets": [
                        {"id": "rod", "name": "rod", "type": "prop", "usage": "player"}
                    ],
                }
            },
            "ready_to_export": False,
        }
        _apply_parsed(session, parsed, "commit_brief")
        scenes = session["draft_brief"]["project"]["scenes"]
        self.assertEqual(len(scenes), 1)
        self.assertNotIn("notes", scenes[0])
        self.assertEqual(scenes[0].get("path"), "scenes/lake.json")

    def test_looks_like_draft_write_claim(self) -> None:
        self.assertTrue(looks_like_draft_write_claim("6 条意图缺口全部收到，我已按你的拍板关掉并写进草稿："))
        self.assertTrue(looks_like_draft_write_claim("我刚用补丁把这 7 条的拍板真写进去了。"))
        self.assertTrue(looks_like_draft_write_claim("以上已同步到 description 和 scenes。"))
        self.assertFalse(looks_like_draft_write_claim("这是草稿，落实后才定稿。"))
        self.assertFalse(looks_like_draft_write_claim("不可声称已写入 brief.json。"))

    def test_apply_parsed_warns_on_talk_without_write(self) -> None:
        session = new_session("talk-no-write")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        parsed = {
            "assistant_message": "收到，3 条意图缺口按你的拍板关掉，我这轮用补丁真正落到草稿里。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        self.assertEqual(session["draft_brief"]["project"]["description"], "old")
        self.assertTrue(session.get("_talk_without_write"))
        self.assertNotIn("只说不写", out["assistant_message"])
        self.assertNotIn("宿主拦截", out["assistant_message"])
        payload = _build_user_payload(session, "chat")
        self.assertIn("只说不写", str(payload.get("host_nudge") or ""))
        self.assertIn("策划", str(payload.get("host_nudge") or ""))
        self.assertIn("外挂", str(payload.get("host_nudge") or ""))

    def test_apply_parsed_idempotent_patches_not_talk_without_write(self) -> None:
        session = new_session("idempotent-patch")
        session["draft_brief"] = {
            "project": {
                "title": "Fish",
                "description": "old",
                "genre": "sim",
                "session_goal": "Catch fish.",
            },
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        parsed = {
            "assistant_message": "补丁已随本轮 JSON 提交，侧栏可预览 diff。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {
                        "op": "set",
                        "path": "project.session_goal",
                        "value": "Catch fish.",
                    }
                ]
            },
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        self.assertEqual(session["draft_brief"]["project"]["session_goal"], "Catch fish.")
        self.assertFalse(session.get("_talk_without_write"))
        self.assertNotIn("只说不写", out["assistant_message"])

    def test_run_turn_retries_talk_without_write_once(self) -> None:
        session = new_session("retry-write")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        claim = {
            "assistant_message": "四项已用补丁真正落到草稿里。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": False,
        }
        write = {
            "assistant_message": "已把 session_goal 写入草稿。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {
                        "op": "set",
                        "path": "project.session_goal",
                        "value": "Catch fish.",
                    }
                ]
            },
            "ready_to_export": False,
        }
        config = {
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}
        }
        with patch("host_chat._call_llm", side_effect=[claim, write]) as mocked:
            result = run_turn(session, user_message="鱼改成宽图", config=config)
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(session["draft_brief"]["project"]["session_goal"], "Catch fish.")
        self.assertFalse(session.get("_talk_without_write"))
        self.assertNotIn("只说不写", result["assistant_message"])
        self.assertIn("已自动改正", result["assistant_message"])
        self.assertEqual(
            sum(1 for m in session["messages"] if m["role"] == "assistant"),
            1,
        )

    def test_run_turn_retry_still_fails_keeps_intercept(self) -> None:
        session = new_session("retry-fail")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        claim = {
            "assistant_message": "四项已用补丁真正落到草稿里。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": False,
        }
        config = {
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}
        }
        with patch("host_chat._call_llm", side_effect=[claim, claim, claim]) as mocked:
            result = run_turn(session, user_message="鱼改成宽图", config=config)
        self.assertEqual(mocked.call_count, 3)
        self.assertTrue(session.get("_talk_without_write"))
        self.assertNotIn("宿主拦截", result["assistant_message"])
        self.assertIn("还没写进侧栏", result["assistant_message"])
        self.assertIn("不用重复需求", result["assistant_message"])
        payload = _build_user_payload(session, "chat")
        self.assertIn("鱼改成宽图", str(payload.get("host_nudge") or ""))

    def test_apply_parsed_no_warn_when_quiet_no_claim(self) -> None:
        session = new_session("quiet-chat")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        parsed = {
            "assistant_message": "咬钩是 0–3 秒随机，没有超时失败。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        self.assertFalse(session.get("_talk_without_write"))
        self.assertNotIn("只说不写", out["assistant_message"])

    def test_apply_parsed_heals_add_asset_instead_of_talk_without_write(self) -> None:
        session = new_session("heal-add-asset")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        parsed = {
            "assistant_message": "定点补丁已落进侧栏草稿：新增钓具店建筑。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {"op": "add_asset", "value": {"name": "主界面_建筑_钓具店"}},
                ]
            },
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        added = next(
            item
            for item in session["draft_brief"]["assets"]
            if item.get("name") == "主界面_建筑_钓具店"
        )
        self.assertEqual(added["type"], "texture")
        self.assertFalse(session.get("_talk_without_write"))
        self.assertNotIn("只说不写", out["assistant_message"])
        self.assertNotIn("草稿补丁未应用", out["assistant_message"])

    def test_apply_parsed_schema_error_nudges_without_talk_without_write(self) -> None:
        session = new_session("schema-fail")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        parsed = {
            "assistant_message": "补丁已随本轮 JSON 提交，侧栏可预览 diff。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {"op": "add_asset", "value": {"name": "未分类物件"}},
                ]
            },
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        self.assertNotIn("草稿补丁未应用", out["assistant_message"])
        self.assertFalse(session.get("_talk_without_write"))
        self.assertNotIn("只说不写", out["assistant_message"])
        self.assertIn("缺少 type", str(session.get("_patch_schema_error") or ""))
        payload = _build_user_payload(session, "chat")
        self.assertIn("校验失败", str(payload.get("host_nudge") or ""))
        self.assertIn("策划", str(payload.get("host_nudge") or ""))
        self.assertIn("外挂", str(payload.get("host_nudge") or ""))

    def test_run_turn_stripped_scene_merge_does_not_retry(self) -> None:
        session = new_session("strip-no-retry")
        session["draft_brief"] = {
            "project": {
                "title": "Fish",
                "scenes": [{"id": "lake", "title": "湖面", "path": "scenes/lake.json"}],
            },
            "assets": [],
        }
        parsed = {
            "assistant_message": "更新了标题。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "draft_brief": {
                    "project": {
                        "title": "Fish 2",
                        "scenes": [
                            {
                                "id": "lake",
                                "title": "湖面",
                                "summary": "模型塞进来的场景正文",
                            }
                        ],
                    }
                }
            },
            "ready_to_export": False,
        }
        config = {
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}
        }
        with patch("host_chat._call_llm", return_value=parsed) as mocked:
            result = run_turn(session, user_message="改标题", config=config)
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(session["draft_brief"]["project"]["title"], "Fish 2")
        self.assertTrue(session.get("_rewrite_needs_patches"))
        self.assertFalse(session.get("_rewrite_retry_now"))
        self.assertIn("更新了标题", result["assistant_message"])
        self.assertNotIn("还没写进侧栏", result["assistant_message"])
        payload = _build_user_payload(session, "chat")
        self.assertIn("upsert_scene", str(payload.get("host_nudge") or ""))

    def test_apply_parsed_bootstraps_draft_for_patches(self) -> None:
        session = new_session("boot-patch")
        parsed = {
            "assistant_message": "先写下钓具店。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {
                        "op": "add_asset",
                        "value": {"name": "主界面_建筑_钓具店"},
                    }
                ]
            },
            "ready_to_export": False,
        }
        out = _apply_parsed(session, parsed, "chat")
        assets = (session.get("draft_brief") or {}).get("assets") or []
        added = next(item for item in assets if item.get("name") == "主界面_建筑_钓具店")
        self.assertEqual(added["type"], "texture")
        self.assertNotIn("还没有草稿", out["assistant_message"])

    def test_run_turn_retries_broken_json_then_writes(self) -> None:
        session = new_session("retry-broken-json")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        write = {
            "assistant_message": "已把 session_goal 写入草稿。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {
                        "op": "set",
                        "path": "project.session_goal",
                        "value": "Catch fish.",
                    }
                ]
            },
            "ready_to_export": False,
        }
        config = {
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}
        }
        with patch(
            "host_chat.chat_text_completion",
            side_effect=[
                "{assistant_message: 还在扩写, draft_brief: <<<broken>>>",
                json.dumps(write, ensure_ascii=False),
            ],
        ) as mocked:
            result = run_turn(session, user_message="目标改成钓鱼", config=config)
        self.assertGreaterEqual(mocked.call_count, 2)
        self.assertEqual(session["draft_brief"]["project"]["session_goal"], "Catch fish.")
        self.assertIn("已自动改正", result["assistant_message"])
        self.assertNotIn("请再发一句", result["assistant_message"])

    def test_run_turn_retries_empty_llm_then_writes(self) -> None:
        session = new_session("retry-empty")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        empty = {
            "assistant_message": "",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": False,
        }
        write = {
            "assistant_message": "已把 session_goal 写入草稿。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {
                        "op": "set",
                        "path": "project.session_goal",
                        "value": "Catch fish.",
                    }
                ]
            },
            "ready_to_export": False,
        }
        config = {
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}
        }
        with patch("host_chat._call_llm", side_effect=[empty, write]) as mocked:
            result = run_turn(session, user_message="目标改成钓鱼", config=config)
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(session["draft_brief"]["project"]["session_goal"], "Catch fish.")
        self.assertFalse(session.get("_empty_model_turn"))
        self.assertIn("已自动改正", result["assistant_message"])
        self.assertNotIn("请再发一句", result["assistant_message"])

    def test_run_turn_retries_commit_brief_when_empty(self) -> None:
        session = new_session("retry-commit")
        session["messages"] = [
            {"role": "user", "content": "横版魔法王子，能走跳砍"},
            {"role": "assistant", "content": "好的，我们先聊手感。"},
        ]
        empty = {
            "assistant_message": "落实中。",
            "choices": [],
            "mode": "commit_brief",
            "intent_hint": "none",
            "artifact": None,
            "ready_to_export": False,
        }
        good = {
            "assistant_message": "已按对话落实草案。",
            "choices": ["导出"],
            "mode": "commit_brief",
            "intent_hint": "none",
            "artifact": {
                "kind": "brief",
                "draft_brief": {
                    "project": {
                        "title": "Magic Prince",
                        "description": "2D platformer",
                        "art_direction": "painterly fantasy",
                        "dimension": "2d",
                        "genre": "2d_platformer",
                        "gameplay_loop": "Run jump slash through levels.",
                        "session_goal": "Demo move jump attack.",
                        "player_asset": "hero",
                        "controls": {
                            "move_left": ["A"],
                            "move_right": ["D"],
                            "jump": ["Space"],
                        },
                        "viewport": {"width": 1280, "height": 720},
                        "camera": {"mode": "follow_player"},
                    },
                    "assets": [
                        {
                            "id": "hero",
                            "name": "hero",
                            "type": "character",
                            "usage": "player_idle",
                            "usage_description": "Hero idle",
                            "description": "A prince",
                            "display_size": "128x128 px",
                            "generate_method": "image",
                        }
                    ],
                },
            },
            "ready_to_export": True,
        }
        config = {
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}
        }
        with patch("host_chat._call_llm", side_effect=[empty, good]) as mocked:
            result = run_turn(session, user_message="落实成 brief", config=config)
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(session["draft_brief"]["project"]["title"], "Magic Prince")
        self.assertFalse(session.get("_commit_body_missing"))
        self.assertIn("已自动改正", result["assistant_message"])
        self.assertNotIn("请再说明", result["assistant_message"])

    def test_run_turn_retries_schema_error_and_writes(self) -> None:
        session = new_session("retry-schema")
        session["draft_brief"] = {
            "project": {"title": "Fish", "description": "old", "genre": "sim"},
            "assets": [{"id": "rod", "name": "rod", "type": "icon_kit"}],
        }
        bad = {
            "assistant_message": "已新增未分类物件。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {"op": "add_asset", "value": {"name": "未分类物件"}},
                ]
            },
            "ready_to_export": False,
        }
        good = {
            "assistant_message": "已新增钓具店建筑。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "brief_patches": [
                    {"op": "add_asset", "value": {"name": "主界面_建筑_钓具店"}},
                ]
            },
            "ready_to_export": False,
        }
        config = {
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}
        }
        with patch("host_chat._call_llm", side_effect=[bad, good]) as mocked:
            result = run_turn(session, user_message="主界面加钓具店", config=config)
        self.assertEqual(mocked.call_count, 2)
        added = next(
            item
            for item in session["draft_brief"]["assets"]
            if item.get("name") == "主界面_建筑_钓具店"
        )
        self.assertEqual(added["type"], "texture")
        self.assertFalse(session.get("_patch_schema_error"))
        self.assertFalse(session.get("_talk_without_write"))
        self.assertIn("已自动改正", result["assistant_message"])
        self.assertNotIn("还没写进侧栏", result["assistant_message"])

    def test_commit_keyword_uses_commit_skill(self) -> None:
        session = new_session("c1")
        session["messages"] = [
            {"role": "user", "content": "横版魔法王子，能走跳砍"},
            {"role": "assistant", "content": "好的，我们先聊手感。"},
        ]
        commit_payload = {
            "assistant_message": "已按对话落实草案。",
            "choices": ["导出"],
            "mode": "commit_brief",
            "intent_hint": "none",
            "artifact": {
                "kind": "brief",
                "draft_brief": {
                    "project": {
                        "title": "Magic Prince",
                        "description": "2D platformer",
                        "art_direction": "painterly fantasy",
                        "dimension": "2d",
                        "genre": "2d_platformer",
                        "gameplay_loop": "Run jump slash through levels.",
                        "session_goal": "Demo move jump attack.",
                        "player_asset": "hero",
                        "controls": {"move_left": ["A"], "move_right": ["D"], "jump": ["Space"]},
                        "viewport": {"width": 1280, "height": 720},
                        "camera": {"mode": "follow_player"},
                    },
                    "assets": [
                        {
                            "id": "hero",
                            "name": "hero",
                            "type": "character",
                            "usage": "player_idle",
                            "usage_description": "Hero idle",
                            "description": "A prince",
                            "display_size": "128x128 px",
                            "generate_method": "image",
                        }
                    ],
                },
            },
            "ready_to_export": True,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(commit_payload, ensure_ascii=False),
        ) as mock_llm:
            result = run_turn(session, user_message="落实成 brief", config=config)
        self.assertTrue(mock_llm.called)
        system = mock_llm.call_args.kwargs.get("messages") or mock_llm.call_args[1].get("messages")
        if system is None:
            system = mock_llm.call_args[0][0] if mock_llm.call_args[0] else mock_llm.call_args.kwargs["messages"]
        # messages kw
        msgs = mock_llm.call_args.kwargs["messages"]
        self.assertIn("Commit Brief", msgs[0]["content"])
        self.assertTrue(result["ready_to_export"])
        self.assertIsNotNone(session.get("draft_brief"))
        self.assertEqual(session["mode"], "commit_brief")

    def test_intent_hint_triggers_followup_commit(self) -> None:
        session = new_session("c2")
        chat_payload = {
            "assistant_message": "好，我按 brief 落实。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "commit_brief",
            "artifact": None,
            "ready_to_export": False,
        }
        commit_payload = {
            "assistant_message": "草案好了。",
            "choices": ["导出"],
            "mode": "commit_brief",
            "intent_hint": "none",
            "artifact": {
                "kind": "brief",
                "draft_brief": {
                    "project": {
                        "title": "Demo",
                        "description": "Demo game",
                        "art_direction": "pixel",
                        "dimension": "2d",
                        "genre": "2d_platformer",
                        "gameplay_loop": "Jump around.",
                        "session_goal": "Move only.",
                        "player_asset": "hero",
                        "controls": {"move_left": ["A"], "move_right": ["D"]},
                        "viewport": {"width": 1280, "height": 720},
                        "camera": {"mode": "follow_player"},
                    },
                    "assets": [
                        {
                            "id": "hero",
                            "name": "hero",
                            "type": "character",
                            "usage": "player_idle",
                            "usage_description": "Hero",
                            "description": "Hero",
                            "display_size": "64x64 px",
                            "generate_method": "image",
                        }
                    ],
                },
            },
            "ready_to_export": True,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            side_effect=[
                json.dumps(chat_payload, ensure_ascii=False),
                json.dumps(commit_payload, ensure_ascii=False),
            ],
        ):
            result = run_turn(session, user_message="差不多了，帮我整理成可交付的需求吧", config=config)
        self.assertTrue(result["ready_to_export"])
        # chat ack + commit reply
        self.assertGreaterEqual(len(session["messages"]), 3)

    def test_compress_trims_old_messages(self) -> None:
        session = new_session("long")
        # Build oversized history (over _CHAR_BUDGET, more than _RECENT_KEEP)
        session["messages"] = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": ("x" * 1200)}
            for i in range(60)
        ]
        self.assertGreater(
            sum(len(m["content"]) for m in session["messages"]),
            _CHAR_BUDGET,
        )
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value="早期讨论了横版与跳跃手感。"):
            compressed = maybe_compress_session(session, config)
        self.assertTrue(compressed)
        self.assertTrue(session["summary"])
        self.assertLessEqual(len(session["messages"]), 40)
        self.assertGreater(session["compressed_count"], 0)

        payload = _build_user_payload(session, "chat")
        self.assertIn("conversation_summary", payload)

    def test_compress_prompt_excludes_ledger_decisions(self) -> None:
        from host_chat import _compress_prompt

        ledger = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "answer_text": "开局可进",
                "status": "verified",
            }
        ]
        prompt = _compress_prompt("已有摘要", [{"role": "user", "content": "hi"}], decision_ledger=ledger)
        self.assertIn("勿写入 conversation_summary", prompt)
        self.assertIn("system.aquarium.unlock_rule", prompt)
        self.assertIn("禁止", prompt)
        self.assertNotIn("保留已拍板设定", prompt)

    def test_compress_prompt_without_ledger_backward_compatible(self) -> None:
        from host_chat import _compress_prompt

        prompt = _compress_prompt("old", [{"role": "user", "content": "讨论横版"}])
        self.assertIn("待定", prompt)
        self.assertIn("较早对话", prompt)
        self.assertIn("（无 — 宿主未注入 decision_ledger）", prompt)

    def test_export_requires_draft(self) -> None:
        session = new_session("e1")
        with self.assertRaises(HostChatError):
            export_brief(session)

    def test_export_requires_contract_complete(self) -> None:
        session = new_session("e2")
        session["draft_brief"] = {
            "project": {"title": "T", "genre": "2d_platformer"},
            "assets": [{"id": "hero", "name": "hero", "type": "character"}],
        }
        session["ready_to_export"] = True
        with self.assertRaises(HostChatError) as ctx:
            export_brief(session)
        self.assertIn("校验未通过", str(ctx.exception))

    def test_status_chat_session(self) -> None:
        session = new_session("s1")
        session["messages"] = [{"role": "user", "content": "hi"}]
        st = session_status(session)
        self.assertTrue(st["exists"])
        self.assertEqual(st["message_count"], 1)
        self.assertFalse(st["ready_to_export"])
        self.assertIsNone(st.get("draft_brief"))

    def test_status_includes_draft_summary(self) -> None:
        session = new_session("s2")
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
            },
            "assets": [{"name": "hero", "type": "character", "usage": "player_idle"}],
        }
        st = session_status(session)
        self.assertEqual(st["title"], "Demo")
        self.assertEqual(st["genre"], "2d_platformer")
        self.assertEqual(st["asset_count"], 1)
        self.assertEqual(st["assets"][0]["name"], "hero")
        self.assertIsNotNone(st["draft_brief"])
        self.assertFalse(st["ready_to_export"])

    def test_system_prompt_injects_animation_graphs_skill(self) -> None:
        for mode in ("chat", "commit_brief"):
            prompt = _system_prompt(mode)
            self.assertIn("animation_graphs", prompt)
            self.assertIn("禁止", prompt)
            self.assertIn("states", prompt)
            self.assertIn("Godot clip", prompt)
        doc_prompt = _system_prompt("commit_doc")
        self.assertNotIn("禁止（常见幻觉）", doc_prompt)

    def test_autofix_message_includes_gaps_and_clip_hint(self) -> None:
        draft = {
            "project": {"title": "T"},
            "assets": [
                {
                    "name": "hero",
                    "type": "character",
                    "usage": "reference_still",
                    "usage_description": "ref",
                    "description": "h",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                },
                {
                    "name": "hero_walk",
                    "type": "character",
                    "usage": "player_locomotion",
                    "usage_description": "walk",
                    "description": "w",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                    "reference_asset": "hero",
                    "action": "walking",
                    "animation_method": "video",
                },
            ],
            "animation_graphs": [
                {
                    "character_asset": "hero",
                    "default_clip": "idle",
                    "transitions": [{"from": "idle", "to": "跑动"}],
                }
            ],
        }
        msg = build_autofix_user_message(["animation_graphs 'hero': unknown to clip '跑动'"], draft)
        self.assertIn("unknown to clip", msg)
        self.assertIn("states", msg)
        self.assertIn("brief_patches", msg)
        self.assertIn("hero:", msg)
        self.assertIn("idle", msg)
        self.assertIn("资产 → Godot clip", msg)
        type_msg = build_autofix_user_message(
            ["2 asset(s) have illegal type 'animation' (e.g. a1, a2)."],
            draft,
        )
        self.assertIn("brief_patches", type_msg)
        self.assertIn("character_pose", type_msg)
        self.assertNotIn("资产 → Godot clip", type_msg)

    def test_autofix_deterministic_clears_illegal_asset_types(self) -> None:
        """animation/item aliases are code-fixed; LLM must not be required for that."""
        session = new_session("af-types")
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "description": "A simple demo game.",
                "art_direction": "pixel",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
                "session_goal": "Move.",
                "player_asset": "hero",
                "controls": {"move_left": ["A"], "move_right": ["D"]},
                "viewport": {"width": 1280, "height": 720},
                "camera": {"mode": "follow_player"},
            },
            "assets": [
                {
                    "id": "hero",
                    "name": "hero",
                    "type": "character",
                    "usage": "reference_still",
                    "usage_description": "ref",
                    "description": "Hero",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                },
                {
                    "id": "hero_walk",
                    "name": "hero_walk",
                    "type": "animation",
                    "usage": "player_locomotion",
                    "usage_description": "walk",
                    "description": "Walk",
                    "display_size": "64x64 px",
                    "generate_method": "video",
                    "reference_asset": "hero",
                    "action": "walking",
                    "animation_method": "video",
                },
                {
                    "id": "coin_icon",
                    "name": "coin_icon",
                    "type": "item",
                    "usage": "ui_icon",
                    "usage_description": "coin",
                    "description": "Coin",
                    "display_size": "32x32 px",
                    "generate_method": "image",
                },
            ],
            "animation_graphs": [
                {
                    "character_asset": "hero",
                    "default_clip": "walk",
                    "transitions": [],
                }
            ],
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion") as mock_llm:
            result = run_autofix(session, config=config, max_rounds=3)
        mock_llm.assert_not_called()
        self.assertTrue(result["ok"], result)
        types = {a["name"]: a["type"] for a in session["draft_brief"]["assets"]}
        self.assertEqual(types["hero_walk"], "character_pose")
        self.assertEqual(types["coin_icon"], "texture")

    def test_autofix_deterministic_clears_clip_mismatch(self) -> None:
        """Clip name typos are code-fixed; LLM must not be required."""
        session = new_session("af0")
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "description": "A simple demo game.",
                "art_direction": "pixel",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
                "session_goal": "Move.",
                "player_asset": "hero",
                "controls": {"move_left": ["A"], "move_right": ["D"]},
                "viewport": {"width": 1280, "height": 720},
                "camera": {"mode": "follow_player"},
            },
            "assets": [
                {
                    "id": "hero",
                    "name": "hero",
                    "type": "character",
                    "usage": "reference_still",
                    "usage_description": "ref",
                    "description": "Hero",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                },
                {
                    "id": "hero_walk",
                    "name": "hero_walk",
                    "type": "character",
                    "usage": "player_locomotion",
                    "usage_description": "walk",
                    "description": "Walk",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                    "reference_asset": "hero",
                    "action": "walking",
                    "animation_method": "video",
                },
            ],
            "animation_graphs": [
                {
                    "character_asset": "hero",
                    "default_clip": "idle",
                    "states": [{"id": "跑动", "clip": "跑动"}],
                    "transitions": [
                        {"from": "idle", "to": "hero_walk", "bidirectional": True},
                    ],
                }
            ],
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion") as mock_llm:
            result = run_autofix(session, config=config, max_rounds=3)
        mock_llm.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertEqual(result["gaps"], [])
        graph = session["draft_brief"]["animation_graphs"][0]
        self.assertNotIn("states", graph)
        self.assertEqual(graph["transitions"][0]["to"], "walk")

    def test_autofix_loop_clears_gaps(self) -> None:
        """Non-mechanical gaps still go through LLM rounds."""
        session = new_session("af1")
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "description": "A simple demo game.",
                "art_direction": "",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
                "session_goal": "Move.",
                "player_asset": "hero",
                "controls": {"move_left": ["A"], "move_right": ["D"]},
                "viewport": {"width": 1280, "height": 720},
                "camera": {"mode": "follow_player"},
            },
            "assets": [
                {
                    "id": "hero",
                    "name": "hero",
                    "type": "character",
                    "usage": "player_idle",
                    "usage_description": "Hero",
                    "description": "Hero",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                },
            ],
        }
        fixed = copy.deepcopy(session["draft_brief"])
        fixed["project"]["art_direction"] = "pixel art"
        fix_payload = {
            "assistant_message": "已补 art_direction。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {"draft_brief": fixed},
            "ready_to_export": False,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(fix_payload, ensure_ascii=False),
        ):
            result = run_autofix(session, config=config, max_rounds=3)
        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "contract_complete")
        self.assertEqual(result["gaps"], [])
        self.assertGreaterEqual(result["rounds_run"], 1)

    def test_status_reaudits_and_clears_stale_gaps(self) -> None:
        """Stale session gaps must not stick after draft is already fixed."""
        session = new_session("s3")
        session["gaps"] = [
            "animation_graphs '球员_普通': unknown to clip '跑动'",
        ]
        # Minimal draft without multi-clip graph requirement — audit should not keep that gap
        session["draft_brief"] = {
            "project": {
                "title": "Demo",
                "description": "A simple demo game.",
                "art_direction": "pixel",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "Jump around.",
                "session_goal": "Move.",
                "player_asset": "hero",
                "controls": {"move_left": ["A"], "move_right": ["D"]},
                "viewport": {"width": 1280, "height": 720},
                "camera": {"mode": "follow_player"},
            },
            "assets": [
                {
                    "name": "hero",
                    "type": "character",
                    "usage": "player_idle",
                    "usage_description": "Hero",
                    "description": "Hero",
                    "display_size": "64x64 px",
                    "generate_method": "image",
                }
            ],
        }
        st = session_status(session)
        self.assertFalse(
            any("跑动" in g for g in st["gaps"]),
            f"stale gap leaked: {st['gaps']}",
        )

    def test_chat_turn_persists_draft_document(self) -> None:
        session = new_session("doc1")
        llm_payload = {
            "assistant_message": "我先把讨论写成草稿说明。",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "artifact": {
                "draft_document": {
                    "title": "攻击手感笔记",
                    "format": "markdown",
                    "body": "# 攻击手感\n\n- 轻攻击三段\n",
                }
            },
            "ready_to_export": False,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value=json.dumps(llm_payload)):
            result = run_turn(session, user_message="记一下攻击手感", config=config)
        self.assertFalse(result["ready_to_export"])
        self.assertEqual(session["draft_document"]["title"], "攻击手感笔记")
        self.assertIn("轻攻击", session["draft_document"]["body"])
        st = session_status(session)
        self.assertTrue(st["has_document"])
        self.assertEqual(st["document_title"], "攻击手感笔记")

    def test_commit_doc_keyword_stores_body(self) -> None:
        session = new_session("doc2")
        session["messages"] = [
            {"role": "user", "content": "横版跳跃，三段斩"},
            {"role": "assistant", "content": "好的。"},
        ]
        commit_payload = {
            "assistant_message": "设计说明已整理。",
            "choices": ["保存"],
            "mode": "commit_doc",
            "intent_hint": "none",
            "artifact": {
                "kind": "document",
                "title": "横版设计说明",
                "format": "markdown",
                "body": "# 横版设计说明\n\n三段斩。\n",
            },
            "ready_to_export": True,
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(commit_payload, ensure_ascii=False),
        ) as mock_llm:
            result = run_turn(session, user_message="整理成设计说明", config=config)
        msgs = mock_llm.call_args.kwargs["messages"]
        self.assertIn("Commit Doc", msgs[0]["content"])
        self.assertTrue(result["ready_to_export"])
        self.assertIn("三段斩", session["draft_document"]["body"])

    def test_attach_bound_replaces_foreign_draft_from_disk(self) -> None:
        from host_chat import attach_bound_project

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "fishing-2d"
            proj.mkdir(parents=True)
            disk_draft = {
                "project": {"title": "2D钓鱼模拟器", "genre": "simulation"},
                "assets": [{"name": "rod", "type": "prop", "usage": "player"}],
            }
            (proj / "brief.draft.json").write_text(
                json.dumps(disk_draft, ensure_ascii=False),
                encoding="utf-8",
            )
            session = new_session("bind-test")
            session["draft_brief"] = {
                "project": {"title": "Black Whistle"},
                "assets": [{"name": "ball", "type": "prop", "usage": "player"}],
            }
            session["bound_brief_rel"] = "projects/black-whistle/brief.json"
            attach_bound_project(session, "projects/fishing-2d/brief.json", repo_root=root)
            self.assertEqual(session["bound_brief_rel"], "projects/fishing-2d/brief.json")
            self.assertEqual(
                (session.get("draft_brief") or {}).get("project", {}).get("title"),
                "2D钓鱼模拟器",
            )
            self.assertEqual(len((session.get("draft_brief") or {}).get("assets") or []), 1)

    def test_attach_bound_always_copies_disk_draft(self) -> None:
        from host_chat import attach_bound_project

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "fishing-2d"
            proj.mkdir(parents=True)
            (proj / "brief.draft.json").write_text(
                json.dumps(
                    {
                        "project": {"title": "2D钓鱼模拟器"},
                        "assets": [{"name": "from_disk", "type": "prop", "usage": "x"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            session = new_session("bind-copy")
            session["bound_brief_rel"] = "projects/fishing-2d/brief.json"
            session["draft_brief"] = {
                "project": {"title": "2D钓鱼模拟器"},
                "assets": [
                    {"name": "old", "type": "prop", "usage": "x"},
                    {"name": "newer", "type": "prop", "usage": "y"},
                ],
            }
            attach_bound_project(session, "projects/fishing-2d/brief.json", repo_root=root)
            assets = (session.get("draft_brief") or {}).get("assets") or []
            # Flush writes 2 assets to disk, then hydrate reads them back
            self.assertEqual(len(assets), 2)
            self.assertEqual(assets[1]["name"], "newer")
            disk = json.loads((proj / "brief.draft.json").read_text(encoding="utf-8"))
            self.assertEqual(len(disk.get("assets") or []), 2)

    def test_attach_bound_does_not_clobber_richer_disk_after_pull(self) -> None:
        from host_chat import attach_bound_project, draft_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "fishing-2d"
            proj.mkdir(parents=True)
            thin = {
                "project": {"title": "2D钓鱼模拟器"},
                "assets": [{"name": "old", "type": "prop", "usage": "x"}],
            }
            rich = {
                "project": {
                    "title": "2D钓鱼模拟器",
                    "scenes": [{"id": "lake", "title": "湖面"}],
                    "systems": [{"id": "cast", "title": "抛竿"}],
                },
                "assets": [
                    {"name": "old", "type": "prop", "usage": "x"},
                    {"name": "rod", "type": "prop", "usage": "y"},
                    {"name": "carp", "type": "character", "usage": "z"},
                ],
            }
            (proj / "brief.draft.json").write_text(
                json.dumps(rich, ensure_ascii=False),
                encoding="utf-8",
            )
            session = new_session("bind-pull")
            session["bound_brief_rel"] = "projects/fishing-2d/brief.json"
            session["draft_brief"] = thin
            # Session still thinks disk is the thin draft it last wrote.
            session["draft_disk_fingerprint"] = draft_fingerprint(thin)
            attach_bound_project(session, "projects/fishing-2d/brief.json", repo_root=root)
            assets = (session.get("draft_brief") or {}).get("assets") or []
            self.assertEqual(len(assets), 3)
            disk = json.loads((proj / "brief.draft.json").read_text(encoding="utf-8"))
            self.assertEqual(len(disk.get("assets") or []), 3)
            self.assertEqual(len(disk["project"].get("scenes") or []), 1)

    def test_sync_session_draft_from_disk_reloads_after_external_edit(self) -> None:
        from host_chat import draft_fingerprint, persist_project_draft, sync_session_draft_from_disk

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "fishing-2d"
            proj.mkdir(parents=True)
            session = new_session("sync-pull")
            session["bound_brief_rel"] = "projects/fishing-2d/brief.json"
            session["draft_brief"] = {
                "project": {"title": "2D钓鱼模拟器"},
                "assets": [{"name": "old", "type": "prop", "usage": "x"}],
            }
            persist_project_draft(session, repo_root=root)
            thin_fp = session["draft_disk_fingerprint"]
            rich = {
                "project": {
                    "title": "2D钓鱼模拟器",
                    "scenes": [{"id": "lake", "title": "湖面"}],
                },
                "assets": [
                    {"name": "old", "type": "prop", "usage": "x"},
                    {"name": "rod", "type": "prop", "usage": "y"},
                ],
            }
            (proj / "brief.draft.json").write_text(
                json.dumps(rich, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertNotEqual(draft_fingerprint(rich), thin_fp)
            changed = sync_session_draft_from_disk(session, repo_root=root)
            self.assertTrue(changed)
            self.assertEqual(len((session.get("draft_brief") or {}).get("assets") or []), 2)
            self.assertEqual(
                (session.get("draft_brief") or {})
                .get("project", {})
                .get("scenes", [{}])[0]
                .get("id"),
                "lake",
            )
            # Second call with unchanged mtime should be a no-op.
            self.assertFalse(sync_session_draft_from_disk(session, repo_root=root))

    def test_sync_disk_only_change_pulls_from_disk(self) -> None:
        from host_chat import draft_fingerprint, persist_project_draft, sync_session_draft_from_disk

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            session = new_session("sync-disk-only")
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            persist_project_draft(session, repo_root=root)
            tracked = session["draft_disk_fingerprint"]
            disk_only = {"project": {"title": "Disk Edit"}, "assets": []}
            (proj / "brief.draft.json").write_text(
                json.dumps(disk_only, ensure_ascii=False),
                encoding="utf-8",
            )
            self.assertNotEqual(draft_fingerprint(disk_only), tracked)
            self.assertEqual(
                draft_fingerprint(session["draft_brief"]),
                tracked,
            )
            self.assertTrue(sync_session_draft_from_disk(session, repo_root=root))
            self.assertEqual(session["draft_brief"]["project"]["title"], "Disk Edit")

    def test_sync_session_only_change_keeps_session(self) -> None:
        from host_chat import persist_project_draft, sync_session_draft_from_disk

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            session = new_session("sync-session-only")
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            persist_project_draft(session, repo_root=root)
            session["draft_brief"] = {"project": {"title": "Session Edit"}, "assets": []}
            self.assertFalse(sync_session_draft_from_disk(session, repo_root=root))
            self.assertEqual(session["draft_brief"]["project"]["title"], "Session Edit")

    def test_sync_dual_edit_raises_without_overwrite(self) -> None:
        from host_chat import draft_fingerprint, persist_project_draft, sync_session_draft_from_disk

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            session = new_session("sync-dual")
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            persist_project_draft(session, repo_root=root)
            session["draft_brief"] = {"project": {"title": "Session Edit"}, "assets": []}
            session_fp = draft_fingerprint(session["draft_brief"])
            disk_other = {"project": {"title": "Disk Edit"}, "assets": []}
            (proj / "brief.draft.json").write_text(
                json.dumps(disk_other, ensure_ascii=False),
                encoding="utf-8",
            )
            disk_fp = draft_fingerprint(disk_other)
            tracked = session["draft_disk_fingerprint"]
            self.assertNotEqual(session_fp, tracked)
            self.assertNotEqual(disk_fp, tracked)
            self.assertNotEqual(session_fp, disk_fp)
            with self.assertRaises(HostChatError):
                sync_session_draft_from_disk(session, repo_root=root)
            self.assertEqual(session["draft_brief"]["project"]["title"], "Session Edit")

    def test_sync_force_overwrites_after_dual_edit(self) -> None:
        from host_chat import draft_fingerprint, persist_project_draft, sync_session_draft_from_disk

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            session = new_session("sync-force")
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            persist_project_draft(session, repo_root=root)
            session["draft_brief"] = {"project": {"title": "Session Edit"}, "assets": []}
            disk_other = {"project": {"title": "Disk Edit"}, "assets": []}
            (proj / "brief.draft.json").write_text(
                json.dumps(disk_other, ensure_ascii=False),
                encoding="utf-8",
            )
            self.assertTrue(
                sync_session_draft_from_disk(session, repo_root=root, force=True)
            )
            self.assertEqual(session["draft_brief"]["project"]["title"], "Disk Edit")
            self.assertEqual(
                session["draft_disk_fingerprint"],
                draft_fingerprint(session["draft_brief"]),
            )

    def test_save_session_persists_bound_draft(self) -> None:
        from host_chat import persist_project_draft, save_session

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "fishing-2d"
            proj.mkdir(parents=True)
            session = new_session("persist-draft")
            session["bound_brief_rel"] = "projects/fishing-2d/brief.json"
            session["draft_brief"] = {
                "project": {"title": "同步测试"},
                "assets": [{"id": "a", "name": "a", "type": "prop", "usage": "x"}],
            }
            sess_path = Path(tmp) / "sess.json"
            # save_session uses _repo_root by default — call persist with explicit root
            out = persist_project_draft(session, repo_root=root)
            self.assertIsNotNone(out)
            assert out is not None
            disk = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(disk["project"]["title"], "同步测试")
            self.assertEqual(len(disk["assets"]), 1)
            zh = proj / "brief.zh.md"
            self.assertTrue(zh.is_file(), "persist should refresh brief.zh.md skeleton")
            self.assertIn("同步测试", zh.read_text(encoding="utf-8"))


class ExternalBoundProjectTests(unittest.TestCase):
    def test_attach_bound_external_without_brief(self) -> None:
        from external_projects import add_external_project
        from host_chat import attach_bound_project

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "fishing-ext"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")
            entry = add_external_project(workspace, ext_root)
            key = f"external:{entry['id']}/brief.json"

            session = new_session("ext-bind")
            attach_bound_project(session, key, repo_root=workspace)
            self.assertEqual(session["bound_brief_rel"], key)
            self.assertEqual(session["project_slug"], "fishing-ext")
            self.assertIsNone(session.get("draft_brief"))

    def test_attach_bound_external_hydrates_from_disk(self) -> None:
        from external_projects import add_external_project
        from host_chat import attach_bound_project

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "my-game"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")
            disk_draft = {
                "project": {"title": "外置钓鱼", "genre": "simulation"},
                "assets": [{"name": "rod", "type": "prop", "usage": "player"}],
            }
            (ext_root / "brief.draft.json").write_text(
                json.dumps(disk_draft, ensure_ascii=False),
                encoding="utf-8",
            )
            entry = add_external_project(workspace, ext_root)
            key = f"external:{entry['id']}/brief.json"

            session = new_session("ext-hydrate")
            attach_bound_project(session, key, repo_root=workspace)
            self.assertEqual(
                (session.get("draft_brief") or {}).get("project", {}).get("title"),
                "外置钓鱼",
            )

    def test_resolve_bound_brief_output_path_external(self) -> None:
        from external_projects import add_external_project
        from host_chat import attach_bound_project, resolve_bound_brief_output_path

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "export-target"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")
            entry = add_external_project(workspace, ext_root)
            key = f"external:{entry['id']}/brief.json"

            session = new_session("ext-resolve")
            attach_bound_project(session, key, repo_root=workspace, hydrate_draft=False)
            out = resolve_bound_brief_output_path(session, repo_root=workspace)
            self.assertEqual(out, (ext_root / "brief.json").resolve())

    def test_export_external_bound_sidecar_at_root(self) -> None:
        import copy

        from external_projects import add_external_project
        from host_chat import (
            attach_bound_project,
            draft_fingerprint,
            export_brief,
            makeability_sidecar_path,
            resolve_bound_brief_output_path,
            write_makeability_sidecar,
        )
        from test_fixtures import SMOKE_BRIEF
        from test_makeability_gate import _detail_only_review

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "sidecar-game"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")
            entry = add_external_project(workspace, ext_root)
            key = f"external:{entry['id']}/brief.json"

            session = new_session("ext-export")
            draft = copy.deepcopy(SMOKE_BRIEF)
            session["draft_brief"] = draft
            session["ready_to_export"] = True
            session["makeability_review"] = _detail_only_review(draft)
            attach_bound_project(session, key, repo_root=workspace, hydrate_draft=False)

            brief = export_brief(session)
            output = resolve_bound_brief_output_path(session, repo_root=workspace)
            assert output is not None
            output.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            sidecar_path = makeability_sidecar_path(key, repo_root=workspace)
            write_makeability_sidecar(sidecar_path, session["makeability_review"])

            self.assertTrue(output.is_file())
            self.assertEqual(output.parent, ext_root.resolve())
            self.assertTrue(sidecar_path.is_file())
            self.assertEqual(sidecar_path, (ext_root / "makeability.json").resolve())
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(sidecar.get("draft_fingerprint"), draft_fingerprint(draft))


from pi_runtime import resolve_brief_executor


class BriefExecutorRoutingTest(unittest.TestCase):
    def test_env_forces_host(self) -> None:
        with patch.dict(os.environ, {"GAMEFACTORY_BRIEF_EXECUTOR": "host"}):
            self.assertEqual(resolve_brief_executor({"agents": {"brief": {"executor": "pi"}}}), "host")

    def test_env_pi_falls_back_when_not_ready(self) -> None:
        with (
            patch.dict(os.environ, {"GAMEFACTORY_BRIEF_EXECUTOR": "pi"}),
            patch("pi_runtime.pi_status", return_value={"ready": False}),
        ):
            self.assertEqual(resolve_brief_executor({}), "host")

    def test_config_pi_falls_back_when_not_ready(self) -> None:
        with patch.dict(os.environ, {"GAMEFACTORY_BRIEF_EXECUTOR": ""}, clear=False):
            os.environ.pop("GAMEFACTORY_BRIEF_EXECUTOR", None)
            with patch("pi_runtime.pi_status", return_value={"ready": False}):
                self.assertEqual(
                    resolve_brief_executor({"agents": {"brief": {"executor": "pi"}}}),
                    "host",
                )

    def test_call_llm_uses_pi_when_forced(self) -> None:
        session = new_session("pi-route")
        payload = {
            "assistant_message": "来自 Pi",
            "choices": ["A"],
            "mode": "chat",
            "intent_hint": "none",
            "ready_to_export": False,
        }
        config = {
            "agents": {"brief": {"executor": "pi"}},
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"},
        }
        with (
            patch.dict(os.environ, {"GAMEFACTORY_BRIEF_EXECUTOR": "pi"}),
            patch("pi_runtime.pi_status", return_value={"ready": True}),
            patch(
                "pi_runtime.run_pi_brief_turn_with_tools",
                return_value=json.dumps(payload),
            ) as mock_pi,
            patch("host_chat.chat_text_completion") as mock_host,
        ):
            result = run_turn(session, user_message="你好", config=config)
        mock_pi.assert_called_once()
        mock_host.assert_not_called()
        self.assertEqual(result["assistant_message"], "来自 Pi")
        self.assertEqual(session.get("_brief_llm_backend"), "pi")

    def test_pi_failure_falls_back_to_host_once(self) -> None:
        from pi_runtime import PiRuntimeError

        session = new_session("pi-fail")
        host_payload = {
            "assistant_message": "来自 Host",
            "choices": [],
            "mode": "chat",
            "intent_hint": "none",
            "ready_to_export": False,
        }
        config = {
            "agents": {"brief": {"executor": "pi"}},
            "host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"},
        }
        with (
            patch.dict(os.environ, {"GAMEFACTORY_BRIEF_EXECUTOR": "pi"}),
            patch("pi_runtime.pi_status", return_value={"ready": True}),
            patch(
                "pi_runtime.run_pi_brief_turn_with_tools",
                side_effect=PiRuntimeError("boom"),
            ) as mock_pi,
            patch(
                "host_chat.chat_text_completion",
                return_value=json.dumps(host_payload),
            ) as mock_host,
        ):
            result = run_turn(session, user_message="你好", config=config)
        mock_pi.assert_called_once()
        mock_host.assert_called_once()
        self.assertEqual(result["assistant_message"], "来自 Host")
        self.assertEqual(session.get("_brief_llm_backend"), "host")
        self.assertIn("boom", session.get("_brief_llm_pi_error") or "")


class PersistCasAndExportSyncTests(unittest.TestCase):
    def test_persist_refuses_overwrite_when_disk_changed_during_llm(self) -> None:
        from host_chat import draft_fingerprint, persist_project_draft

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            session = new_session("cas-persist")
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            persist_project_draft(session, repo_root=root)
            tracked = session["draft_disk_fingerprint"]
            # External edit while "LLM" runs; session still at tracked content.
            (proj / "brief.draft.json").write_text(
                json.dumps({"project": {"title": "Disk"}, "assets": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            self.assertEqual(draft_fingerprint(session["draft_brief"]), tracked)
            with self.assertRaises(HostChatError) as ctx:
                persist_project_draft(session, repo_root=root)
            self.assertIn("外部修改", str(ctx.exception))
            disk = json.loads((proj / "brief.draft.json").read_text(encoding="utf-8"))
            self.assertEqual(disk["project"]["title"], "Disk")

    def test_export_syncs_disk_ahead_of_session(self) -> None:
        from host_chat import (
            draft_fingerprint,
            export_brief,
            persist_project_draft,
        )
        from test_fixtures import SMOKE_BRIEF
        from test_makeability_gate import _detail_only_review, _ready_session

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            draft = copy.deepcopy(SMOKE_BRIEF)
            session = _ready_session(review=_detail_only_review(draft))
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = draft
            persist_project_draft(session, repo_root=root)
            disk_newer = copy.deepcopy(draft)
            if isinstance(disk_newer.get("project"), dict):
                disk_newer["project"] = dict(disk_newer["project"])
                disk_newer["project"]["title"] = "Disk Ahead Title"
            (proj / "brief.draft.json").write_text(
                json.dumps(disk_newer, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            # Session still holds old draft; review matches disk so export can pass after sync.
            session["draft_brief"] = copy.deepcopy(draft)
            session["makeability_review"] = _detail_only_review(disk_newer)
            session["decision_ledger"] = []
            brief = export_brief(session, repo_root=root)
            self.assertEqual(brief["project"]["title"], "Disk Ahead Title")
            self.assertEqual(
                draft_fingerprint(session["draft_brief"]),
                draft_fingerprint(disk_newer),
            )

    def test_export_dual_edit_conflict_refuses(self) -> None:
        from host_chat import export_brief, persist_project_draft
        from test_fixtures import SMOKE_BRIEF
        from test_makeability_gate import _detail_only_review, _ready_session

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            draft = copy.deepcopy(SMOKE_BRIEF)
            session = _ready_session(review=_detail_only_review(draft))
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = draft
            persist_project_draft(session, repo_root=root)
            session["draft_brief"] = copy.deepcopy(draft)
            if isinstance(session["draft_brief"].get("project"), dict):
                session["draft_brief"]["project"] = dict(session["draft_brief"]["project"])
                session["draft_brief"]["project"]["title"] = "Session Edit"
            disk_edit = copy.deepcopy(draft)
            if isinstance(disk_edit.get("project"), dict):
                disk_edit["project"] = dict(disk_edit["project"])
                disk_edit["project"]["title"] = "Disk Edit"
            (proj / "brief.draft.json").write_text(
                json.dumps(disk_edit, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaises(HostChatError) as ctx:
                export_brief(session, repo_root=root)
            self.assertIn("不一致", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
