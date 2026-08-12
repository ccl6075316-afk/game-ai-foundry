"""Tests for brief catalog shards — IO, resolve, migrate, intro budgets."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from brief_shards import (
    DESCRIPTION_MAX_CHARS,
    GAMEPLAY_LOOP_MAX_CHARS,
    apply_description_write_guard,
    audit_catalog_refs,
    audit_intro_budgets,
    brief_uses_catalog,
    build_focus_context,
    canonicalize_structure_to_shards,
    hydrate_brief_for_review,
    is_catalog_ref,
    is_legacy_asset_entry,
    is_legacy_scene_entry,
    is_legacy_system_entry,
    load_json_shard,
    load_shard,
    migrate_brief_to_shards,
    related_shards,
    resolve_asset_specs,
    resolve_shard_path,
    save_json_shard,
    search_shards,
    upsert_shard_body,
)


class TestBriefShardsIo(unittest.TestCase):
    def test_catalog_scene_ref(self) -> None:
        ref = {"id": "hub", "title": "Hub", "path": "scenes/hub.json"}
        self.assertTrue(is_catalog_ref(ref, kind="scene"))
        self.assertFalse(is_legacy_scene_entry(ref))

    def test_catalog_asset_ref_name_or_id(self) -> None:
        ref = {"id": "fish_01", "name": "fish_01", "path": "assets/fish_01.spec.json"}
        self.assertTrue(is_catalog_ref(ref, kind="asset"))
        ref2 = {"id": "fish_02", "path": "assets/fish_02.spec.json"}
        self.assertTrue(is_catalog_ref(ref2, kind="asset"))

    def test_legacy_scene_has_body_without_usable_path(self) -> None:
        legacy = {"id": "dock", "title": "Dock", "summary": "Fishing pier."}
        self.assertTrue(is_legacy_scene_entry(legacy))
        self.assertFalse(is_catalog_ref(legacy, kind="scene"))

    def test_legacy_system(self) -> None:
        legacy = {"id": "eco", "title": "Eco", "notes": "rules"}
        self.assertTrue(is_legacy_system_entry(legacy))

    def test_legacy_asset(self) -> None:
        legacy = {"id": "a", "name": "a", "type": "texture", "usage": "prop"}
        self.assertTrue(is_legacy_asset_entry(legacy))

    def test_resolve_shard_path_rejects_escape(self) -> None:
        root = Path("/tmp/proj")
        with self.assertRaises(ValueError):
            resolve_shard_path(root, "../etc/passwd")

    def test_shard_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "scenes" / "x.json"
            data = {"id": "x", "title": "X", "summary": "hi"}
            save_json_shard(path, data)
            loaded = load_json_shard(path)
            self.assertEqual(loaded, data)
            text = path.read_text(encoding="utf-8")
            self.assertIn("\n", text)


class TestResolveAndAudit(unittest.TestCase):
    def test_resolve_asset_specs_from_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = root / "assets" / "eel.spec.json"
            spec_path.parent.mkdir(parents=True)
            save_json_shard(
                spec_path,
                {
                    "id": "eel",
                    "name": "eel",
                    "type": "character",
                    "usage": "player_idle",
                    "display_size": {"width": 64, "height": 64},
                    "usage_description": "hero",
                },
            )
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {"title": "T", "description": "d", "art_direction": "a", "dimension": "2d"},
                        "assets": [
                            {"id": "eel", "name": "eel", "path": "assets/eel.spec.json"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            specs = resolve_asset_specs(brief_path)
            self.assertEqual(len(specs), 1)
            self.assertEqual(specs[0]["type"], "character")
            self.assertEqual(specs[0]["id"], "eel")

    def test_audit_missing_shard_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = {
                "project": {"title": "T"},
                "scenes": [{"id": "s1", "title": "S", "path": "scenes/s1.json"}],
            }
            errs = audit_catalog_refs(brief, root)
            self.assertTrue(any("missing" in e.lower() or "not found" in e.lower() for e in errs))

    def test_audit_id_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "systems" / "eco.json"
            shard.parent.mkdir(parents=True)
            save_json_shard(shard, {"id": "other", "title": "Eco"})
            brief = {
                "project": {"title": "T"},
                "systems": [{"id": "eco", "title": "Eco", "path": "systems/eco.json"}],
            }
            errs = audit_catalog_refs(brief, root)
            self.assertTrue(any("mismatch" in e.lower() or "id" in e.lower() for e in errs))


class TestMigrate(unittest.TestCase):
    def test_migrate_thick_brief_to_shards(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "Game",
                            "description": "Short.",
                            "art_direction": "pixel",
                            "dimension": "2d",
                            "scenes": [],
                            "systems": [],
                        },
                        "assets": [
                            {
                                "id": "bg",
                                "name": "bg",
                                "type": "background",
                                "usage": "world_background",
                                "usage_description": "sky",
                                "display_size": {"width": 320, "height": 180},
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            # scenes/systems live under project in some briefs — migrate reads top-level too
            data = json.loads(brief_path.read_text(encoding="utf-8"))
            data["scenes"] = [{"id": "main", "title": "Main", "summary": "hub screen"}]
            data["systems"] = [{"id": "time", "title": "Time", "notes": "decay"}]
            brief_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            report = migrate_brief_to_shards(brief_path, backup=True)
            self.assertTrue(report.get("ok"))
            backup = root / "brief.pre-shard.json"
            self.assertTrue(backup.is_file())
            out = json.loads(brief_path.read_text(encoding="utf-8"))
            self.assertEqual(
                out["scenes"],
                [{"id": "main", "title": "Main", "path": "scenes/main.json"}],
            )
            self.assertTrue((root / "scenes" / "main.json").is_file())
            self.assertTrue((root / "assets" / "bg.spec.json").is_file())
            asset_ref = out["assets"][0]
            self.assertIn("path", asset_ref)
            self.assertNotIn("type", asset_ref)


class RelatedShardsTests(unittest.TestCase):
    def _write_catalog_fixtures(self, root: Path) -> dict:
        """Minimal catalog: main_hub scene, combat system, hero asset, ab system."""
        save_json_shard(
            root / "scenes" / "main_hub.json",
            {"id": "main_hub", "title": "Main Hub", "summary": "Hub screen."},
        )
        save_json_shard(
            root / "systems" / "combat.json",
            {"id": "combat", "title": "Combat", "notes": "Combat rules."},
        )
        save_json_shard(
            root / "systems" / "ab.json",
            {"id": "ab", "title": "Short Id System", "notes": "Tiny id."},
        )
        save_json_shard(
            root / "assets" / "hero.spec.json",
            {
                "id": "hero",
                "name": "Hero",
                "type": "character",
                "scene_ids": ["main_hub"],
            },
        )
        save_json_shard(
            root / "scenes" / "arena.json",
            {
                "id": "arena",
                "title": "Arena",
                "notes": "Uses combat system for rounds.",
            },
        )
        return {
            "project": {"title": "T"},
            "scenes": [
                {"id": "main_hub", "title": "Main Hub", "path": "scenes/main_hub.json"},
                {"id": "arena", "title": "Arena", "path": "scenes/arena.json"},
            ],
            "systems": [
                {"id": "combat", "title": "Combat", "path": "systems/combat.json"},
                {"id": "ab", "title": "Short Id System", "path": "systems/ab.json"},
            ],
            "assets": [
                {"id": "hero", "name": "Hero", "path": "assets/hero.spec.json"},
            ],
        }

    def test_asset_declared_scene_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = self._write_catalog_fixtures(root)
            related = related_shards(root, brief, "asset", "hero")
            scene_hits = [r for r in related if r["kind"] == "scene" and r["id"] == "main_hub"]
            self.assertEqual(len(scene_hits), 1)
            self.assertIn("declared", scene_hits[0]["via"])
            self.assertEqual(scene_hits[0]["title"], "Main Hub")

    def test_scene_mention_system_id_word_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = self._write_catalog_fixtures(root)
            related = related_shards(root, brief, "scene", "arena")
            combat_hits = [r for r in related if r["kind"] == "system" and r["id"] == "combat"]
            self.assertEqual(len(combat_hits), 1)
            self.assertIn("mention", combat_hits[0]["via"])
            self.assertNotIn("declared", combat_hits[0]["via"])

    def test_self_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = self._write_catalog_fixtures(root)
            related = related_shards(root, brief, "scene", "arena")
            self.assertFalse(any(r["id"] == "arena" for r in related))

    def test_mention_disappears_when_notes_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = self._write_catalog_fixtures(root)
            before = related_shards(root, brief, "scene", "arena")
            self.assertTrue(any(r["id"] == "combat" for r in before))
            save_json_shard(
                root / "scenes" / "arena.json",
                {"id": "arena", "title": "Arena", "notes": "No system references."},
            )
            after = related_shards(root, brief, "scene", "arena")
            self.assertFalse(any(r["id"] == "combat" for r in after))

    def test_short_id_no_mention(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = self._write_catalog_fixtures(root)
            save_json_shard(
                root / "scenes" / "arena.json",
                {
                    "id": "arena",
                    "title": "Arena",
                    "notes": "Mentions ab twice: ab and ab.",
                },
            )
            related = related_shards(root, brief, "scene", "arena")
            self.assertFalse(any(r["id"] == "ab" for r in related))

    def test_noncombat_does_not_mention_combat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = self._write_catalog_fixtures(root)
            save_json_shard(
                root / "scenes" / "arena.json",
                {
                    "id": "arena",
                    "title": "Arena",
                    "notes": "noncombat exploration mode.",
                },
            )
            related = related_shards(root, brief, "scene", "arena")
            self.assertFalse(any(r["id"] == "combat" for r in related))

    def test_missing_focus_id_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = self._write_catalog_fixtures(root)
            self.assertEqual(related_shards(root, brief, "scene", "missing"), [])


class TestSearchAndLoad(unittest.TestCase):
    def test_search_hits_shard_body(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard = root / "scenes" / "main_hub.json"
            shard.parent.mkdir(parents=True)
            save_json_shard(
                shard,
                {"id": "main_hub", "title": "Harbor Hub", "summary": "Busy harbor docks."},
            )
            brief = {
                "project": {"title": "T"},
                "scenes": [
                    {"id": "main_hub", "title": "Harbor Hub", "path": "scenes/main_hub.json"},
                ],
            }
            hits = search_shards(root, brief, "harbor")
            self.assertTrue(hits)
            self.assertEqual(hits[0]["kind"], "scene")
            self.assertEqual(hits[0]["id"], "main_hub")

    def test_load_shard_catalog_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = "systems/eco.json"
            save_json_shard(
                root / rel,
                {"id": "eco", "title": "Eco", "notes": "rules"},
            )
            brief = {
                "systems": [{"id": "eco", "title": "Eco", "path": rel}],
            }
            body = load_shard(root, "system", "eco", brief)
            self.assertEqual(body["notes"], "rules")
            with self.assertRaises(ValueError):
                load_shard(root, "system", "missing", brief)

    def test_load_brief_resolves_catalog_asset_type(self) -> None:
        from brief import load_brief

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = root / "assets" / "rod.spec.json"
            spec_path.parent.mkdir(parents=True)
            save_json_shard(
                spec_path,
                {
                    "id": "rod",
                    "name": "rod",
                    "type": "texture",
                    "usage": "world_background",
                    "display_size": {"width": 32, "height": 32},
                    "usage_description": "fishing rod",
                },
            )
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "T",
                            "description": "d",
                            "art_direction": "a",
                            "dimension": "2d",
                        },
                        "assets": [{"id": "rod", "name": "rod", "path": "assets/rod.spec.json"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            _project, assets = load_brief(brief_path)
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets[0].type.value, "texture")

    def test_description_write_guard(self) -> None:
        old = {"project": {"description": "short"}}
        new = {"project": {"description": "x" * (DESCRIPTION_MAX_CHARS + 50)}}
        out = apply_description_write_guard(old, new)
        self.assertEqual(out["project"]["description"], "short")


class TestIntroBudgets(unittest.TestCase):
    def test_over_budget_warnings(self) -> None:
        brief = {
            "project": {
                "description": "x" * (DESCRIPTION_MAX_CHARS + 1),
                "gameplay_loop": "y" * (GAMEPLAY_LOOP_MAX_CHARS + 1),
            }
        }
        warnings = audit_intro_budgets(brief)
        self.assertTrue(any("description" in w.lower() and "budget" in w.lower() for w in warnings))
        self.assertTrue(any("gameplay_loop" in w.lower() and "budget" in w.lower() for w in warnings))


class TestFocusContextTruncate(unittest.TestCase):
    def test_build_focus_context_truncates_long_intro(self) -> None:
        draft = {
            "project": {
                "title": "T",
                "description": "d" * (DESCRIPTION_MAX_CHARS + 100),
                "gameplay_loop": "g" * (GAMEPLAY_LOOP_MAX_CHARS + 50),
            },
            "assets": [],
        }
        ctx = build_focus_context(draft, {"kind": "project"})
        proj = ctx["project"]
        self.assertLessEqual(len(proj["description"]), DESCRIPTION_MAX_CHARS + 1)
        self.assertTrue(proj.get("description_truncated"))
        self.assertLessEqual(len(proj["gameplay_loop"]), GAMEPLAY_LOOP_MAX_CHARS + 1)
        self.assertTrue(proj.get("gameplay_loop_truncated"))

    def test_build_focus_context_sets_focus_error_when_shard_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {"id": "missing", "title": "Missing", "path": "scenes/missing.json"},
                    ],
                },
                "assets": [],
            }
            ctx = build_focus_context(
                draft,
                {"kind": "scene", "id": "missing"},
                project_root=root,
            )
            self.assertEqual(ctx.get("focus"), {"kind": "scene", "id": "missing"})
            self.assertNotIn("focus_shard", ctx)
            err = str(ctx.get("focus_error") or "")
            self.assertTrue(err, "expected focus_error when shard cannot load")


class TestFocusContextRelatedShards(unittest.TestCase):
    def _write_catalog_fixtures(self, root: Path) -> dict:
        (root / "scenes").mkdir(parents=True, exist_ok=True)
        (root / "systems").mkdir(parents=True, exist_ok=True)
        (root / "assets").mkdir(parents=True, exist_ok=True)
        save_json_shard(
            root / "scenes" / "main_hub.json",
            {"id": "main_hub", "title": "Main Hub", "summary": "Hub screen."},
        )
        save_json_shard(
            root / "systems" / "combat.json",
            {"id": "combat", "title": "Combat", "notes": "Combat rules."},
        )
        save_json_shard(
            root / "assets" / "hero.spec.json",
            {
                "id": "hero",
                "name": "Hero",
                "type": "character",
                "scene_ids": ["main_hub"],
            },
        )
        save_json_shard(
            root / "scenes" / "arena.json",
            {
                "id": "arena",
                "title": "Arena",
                "notes": "Uses combat system for rounds.",
            },
        )
        return {
            "project": {"title": "T"},
            "scenes": [
                {"id": "main_hub", "title": "Main Hub", "path": "scenes/main_hub.json"},
                {"id": "arena", "title": "Arena", "path": "scenes/arena.json"},
            ],
            "systems": [
                {"id": "combat", "title": "Combat", "path": "systems/combat.json"},
            ],
            "assets": [
                {"id": "hero", "name": "Hero", "path": "assets/hero.spec.json"},
            ],
        }

    def test_scene_focus_includes_related_shards_without_notes_dump(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            draft = self._write_catalog_fixtures(root)
            ctx = build_focus_context(
                draft,
                {"kind": "scene", "id": "arena"},
                project_root=root,
            )
            related = ctx.get("related_shards")
            self.assertIsInstance(related, list)
            combat_hits = [r for r in related if r.get("kind") == "system" and r.get("id") == "combat"]
            self.assertEqual(len(combat_hits), 1)
            for item in related:
                self.assertNotIn("notes", item)
            self.assertNotIn("combat", ctx)
            systems_thin = ctx.get("systems") or []
            for row in systems_thin:
                self.assertNotIn("notes", row)

    def test_project_focus_omits_related_shards(self) -> None:
        draft = {"project": {"title": "T"}, "assets": []}
        ctx = build_focus_context(draft, {"kind": "project"}, project_root=Path("."))
        self.assertNotIn("related_shards", ctx)
        self.assertNotIn("related_error", ctx)

    def test_no_project_root_omits_related_shards(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            draft = self._write_catalog_fixtures(root)
            ctx = build_focus_context(
                draft,
                {"kind": "scene", "id": "arena"},
                project_root=None,
            )
            self.assertNotIn("related_shards", ctx)
            self.assertNotIn("related_error", ctx)

    def test_missing_shard_keeps_focus_error_with_related_handling(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            draft = {
                "project": {
                    "title": "T",
                    "scenes": [
                        {"id": "missing", "title": "Missing", "path": "scenes/missing.json"},
                    ],
                },
                "assets": [],
            }
            ctx = build_focus_context(
                draft,
                {"kind": "scene", "id": "missing"},
                project_root=root,
            )
            self.assertTrue(ctx.get("focus_error"))
            self.assertNotIn("focus_shard", ctx)
            if "related_shards" in ctx:
                self.assertIsInstance(ctx["related_shards"], list)
            else:
                self.assertTrue(ctx.get("related_error"))


class TestUpsertShardBody(unittest.TestCase):
    def test_upsert_shard_body_updates_file_and_returns_thin_ref(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hub = root / "scenes" / "hub.json"
            hub.parent.mkdir(parents=True)
            save_json_shard(
                hub,
                {"id": "hub", "title": "Hub", "summary": "a"},
            )
            brief = {
                "project": {
                    "scenes": [
                        {"id": "hub", "title": "Hub", "path": "scenes/hub.json"},
                    ],
                },
            }
            ref = upsert_shard_body(root, brief, "scene", "hub", {"notes": "new note"})
            self.assertIsNotNone(ref)
            assert ref is not None
            self.assertEqual(ref, {"id": "hub", "title": "Hub", "path": "scenes/hub.json"})
            body = load_json_shard(root / "scenes" / "hub.json")
            self.assertEqual(body["notes"], "new note")
            self.assertNotIn("notes", ref)

    def test_brief_uses_catalog(self) -> None:
        self.assertFalse(brief_uses_catalog({"project": {"scenes": [{"id": "x", "title": "X"}]}}))
        self.assertTrue(
            brief_uses_catalog(
                {
                    "project": {
                        "scenes": [
                            {"id": "x", "title": "X", "path": "scenes/x.json"},
                        ],
                    },
                }
            )
        )


class TestNormalizeCatalogPath(unittest.TestCase):
    def test_normalize_scenes_preserves_catalog_path(self) -> None:
        from brief import normalize_scenes

        raw = [
            {
                "id": "hub",
                "title": "Hub",
                "path": "scenes/hub.json",
                "summary": "should drop",
            }
        ]
        out = normalize_scenes(raw)
        self.assertEqual(out, [{"id": "hub", "title": "Hub", "path": "scenes/hub.json"}])


class TestHydrateBriefForReview(unittest.TestCase):
    def test_hydrate_loads_catalog_scene_and_system_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scenes").mkdir()
            (root / "systems").mkdir()
            save_json_shard(
                root / "scenes" / "hall.json",
                {"id": "hall", "title": "Hall", "notes": "UNLOCK_FROM_START"},
            )
            save_json_shard(
                root / "systems" / "economy.json",
                {"id": "economy", "title": "Economy", "notes": "TICKET_BASELINE"},
            )
            draft = {
                "project": {
                    "title": "Demo",
                    "description": "short",
                    "scenes": [
                        {"id": "hall", "title": "Hall", "path": "scenes/hall.json"},
                    ],
                    "systems": [
                        {
                            "id": "economy",
                            "title": "Economy",
                            "path": "systems/economy.json",
                        },
                    ],
                },
                "assets": [
                    {"id": "rod", "name": "rod", "path": "assets/rod.spec.json"},
                ],
            }
            (root / "assets").mkdir()
            save_json_shard(
                root / "assets" / "rod.spec.json",
                {"id": "rod", "name": "rod", "type": "texture"},
            )
            payload = hydrate_brief_for_review(draft, root)
            scenes = payload["draft_brief"]["project"]["scenes"]
            systems = payload["draft_brief"]["project"]["systems"]
            self.assertEqual(scenes[0]["notes"], "UNLOCK_FROM_START")
            self.assertEqual(systems[0]["notes"], "TICKET_BASELINE")
            self.assertEqual(payload["scene_shards"]["hall"]["notes"], "UNLOCK_FROM_START")
            self.assertEqual(payload["system_shards"]["economy"]["notes"], "TICKET_BASELINE")
            self.assertEqual(payload["assets_index"][0]["type"], "texture")
            self.assertEqual(payload["hydrate_errors"], [])

    def test_hydrate_legacy_inline_passthrough(self) -> None:
        draft = {
            "project": {
                "scenes": [
                    {"id": "dock", "title": "Dock", "notes": "INLINE_NOTE"},
                ],
                "systems": [],
            },
            "assets": [],
        }
        payload = hydrate_brief_for_review(draft, None)
        self.assertEqual(payload["draft_brief"]["project"]["scenes"][0]["notes"], "INLINE_NOTE")
        self.assertEqual(payload["scene_shards"]["dock"]["notes"], "INLINE_NOTE")

    def test_load_brief_full_hydrates_catalog_scene_summary(self) -> None:
        from brief import load_brief_full

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scenes").mkdir()
            (root / "assets").mkdir()
            save_json_shard(
                root / "scenes" / "pier.json",
                {
                    "id": "pier",
                    "title": "Pier",
                    "summary": "SUMMARY_FROM_SHARD",
                    "visual_reference": "output/vt/selected.png",
                },
            )
            save_json_shard(
                root / "assets" / "rod.spec.json",
                {
                    "id": "rod",
                    "name": "rod",
                    "type": "texture",
                    "usage": "prop",
                    "display_size": {"width": 32, "height": 32},
                },
            )
            brief_path = root / "brief.json"
            brief_path.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "Demo",
                            "description": "d",
                            "genre": "sim",
                            "gameplay_loop": "loop",
                            "session_goal": "goal",
                            "scenes": [
                                {
                                    "id": "pier",
                                    "title": "Pier",
                                    "path": "scenes/pier.json",
                                }
                            ],
                        },
                        "assets": [
                            {
                                "id": "rod",
                                "name": "rod",
                                "path": "assets/rod.spec.json",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            project, assets, _graphs = load_brief_full(brief_path)
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets[0].type.value if hasattr(assets[0].type, "value") else str(assets[0].type), "texture")
            self.assertEqual(project.scenes[0].get("summary"), "SUMMARY_FROM_SHARD")
            self.assertEqual(
                project.scenes[0].get("visual_reference"),
                "output/vt/selected.png",
            )

    def test_canonicalize_structure_to_shards_writes_scene_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = {
                "project": {
                    "title": "Demo",
                    "scenes": [
                        {
                            "id": "dock",
                            "title": "Dock",
                            "summary": "Pier",
                            "notes": "SHARD_NOTE",
                        }
                    ],
                },
                "assets": [],
            }
            out = canonicalize_structure_to_shards(candidate, root)
            scene = out["project"]["scenes"][0]
            self.assertTrue(is_catalog_ref(scene, kind="scene"))
            shard = load_json_shard(root / "scenes" / "dock.json")
            self.assertEqual(shard["notes"], "SHARD_NOTE")


if __name__ == "__main__":
    unittest.main()
