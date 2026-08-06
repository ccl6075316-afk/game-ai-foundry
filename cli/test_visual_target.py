"""Tests for visual target candidate generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from visual_target import (
    _safe_scene_dir,
    apply_visual_target_pick,
    assign_visual_reference_to_scenes,
    brief_has_any_visual_reference,
    build_candidate_prompts,
    build_visual_target_plan,
    clear_visual_target_run_artifacts,
    default_output_dir,
    find_manifest_for_brief,
    generate_visual_targets,
    load_visual_target_manifest,
    match_scenes_for_north_star,
    resolve_visual_reference_for_asset,
    resolve_visual_reference_path,
    visual_target_brief_status,
)


def _write_example_brief(dir_path: Path, *, with_scenes: bool = False) -> Path:
    brief = {
        "project": {
            "title": "Dino Scavenger",
            "description": "Side-scrolling scavenger with raptor companion.",
            "art_direction": "Pixel art, warm desert palette.",
            "genre": "side_scroller",
            "gameplay_loop": "Collect scraps while avoiding hazards.",
            "session_goal": "Fill the scrap meter before sunset.",
            "viewport": {"width": 1280, "height": 720},
        },
        "assets": [
            {
                "id": "player",
                "type": "character",
                "usage": "player_idle",
                "generate_method": "image",
            }
        ],
    }
    if with_scenes:
        brief["project"]["scenes"] = [
            {
                "id": "dock",
                "title": "钓场",
                "summary": "Calm pier casting.",
                "notes": "wide horizon",
            },
            {
                "id": "combat",
                "title": "搏鱼",
                "summary": "Tense fight UI.",
            },
        ]
        brief["assets"][0]["scene_ids"] = ["combat", "dock"]
    path = dir_path / "dino-brief.json"
    path.write_text(json.dumps(brief), encoding="utf-8")
    return path


class TestVisualTarget(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.example_brief = _write_example_brief(self.tmp_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_build_candidate_prompts_count(self) -> None:
        prompts = build_candidate_prompts(self.example_brief, count=3)
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0]["id"], "a")
        text = prompts[0]["prompt"].lower()
        self.assertTrue("screenshot" in text or "framebuffer" in text)
        self.assertIn("use case:", text)
        self.assertTrue(
            "art direction" in text or "style lock" in text or "pixel" in text
        )

    def test_default_output_dir(self) -> None:
        out = default_output_dir(self.example_brief)
        self.assertIn("dino-scavenger", str(out))
        self.assertEqual(out.name, "visual-target")

    def test_build_visual_target_plan_scaffold(self) -> None:
        plan = build_visual_target_plan(
            self.example_brief,
            {"id": "a", "label": "opening_moment", "focus": "Opening scene."},
            craft=False,
            config={},
        )
        self.assertEqual(plan["kind"], "visual_target")
        self.assertEqual(plan["prompt_source"], "scaffold")
        self.assertTrue(plan["validation"]["skip_validate"] is True)
        self.assertIn("screenshot", plan["prompt"].lower())
        self.assertIn("Use case:", plan["prompt"])

    def test_generate_dry_run_writes_handoffs(self) -> None:
        out = self.tmp_path / "visual-target"
        plans = self.tmp_path / "plans"
        manifest = generate_visual_targets(
            self.example_brief,
            out,
            count=2,
            config={},
            dry_run=True,
            craft=False,
            plans_dir=plans,
        )
        self.assertEqual(len(manifest["candidates"]), 2)
        self.assertFalse(manifest["craft"])
        for c in manifest["candidates"]:
            self.assertTrue(Path(c["handoff_path"]).is_file())
            handoff = json.loads(Path(c["handoff_path"]).read_text(encoding="utf-8"))
            self.assertEqual(handoff["consumer_role"], "image-generator")
            self.assertEqual(handoff["plan"]["kind"], "visual_target")

    def test_image_size_from_handoff(self) -> None:
        from plan_io import image_size_from_handoff

        handoff = {"plan": {"image_size": "1280x720", "asset_type": "visual_target"}}
        self.assertEqual(image_size_from_handoff(handoff), "1280x720")
        self.assertIsNone(image_size_from_handoff({"plan": {}}))

    def test_apply_pick_updates_brief(self) -> None:
        out_dir = self.tmp_path / "visual-target"
        out_dir.mkdir()
        fake_png = out_dir / "candidate_b.png"
        fake_png.write_bytes(b"\x89PNG\r\n")

        manifest = {
            "viewport_size": "1280x720",
            "candidates": [
                {"id": "a", "label": "opening", "path": str(out_dir / "candidate_a.png")},
                {"id": "b", "label": "action", "path": str(fake_png), "prompt_summary": "action"},
            ],
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = apply_visual_target_pick(self.example_brief, "b", manifest_path)
        self.assertEqual(result["selected_id"], "b")

        data = json.loads(self.example_brief.read_text(encoding="utf-8"))
        self.assertTrue(data["project"]["visual_reference"])
        self.assertEqual(data["project"]["visual_target"]["selected_id"], "b")
        self.assertEqual(data["project"]["visual_target"]["image_size"], "1280x720")

        self.assertEqual(len(data["project"]["visual_target"]["candidates"]), 2)

        updated = load_visual_target_manifest(manifest_path)
        self.assertEqual(updated["selected_id"], "b")
        self.assertTrue((out_dir / "selected.png").is_file())

    def test_default_output_dir_with_scene(self) -> None:
        out = default_output_dir(self.example_brief, scene_id="combat")
        self.assertEqual(out.name, "combat")
        self.assertEqual(out.parent.name, "visual-target")

    def test_safe_scene_dir_cjk_unique(self) -> None:
        self.assertEqual(_safe_scene_dir("combat"), "combat")
        a = _safe_scene_dir("钓场")
        b = _safe_scene_dir("搏鱼")
        self.assertTrue(a.startswith("scene_"))
        self.assertTrue(b.startswith("scene_"))
        self.assertNotEqual(a, b)
        self.assertEqual(_safe_scene_dir("钓场"), a)
        # Punctuation / separators must not collide with clean ASCII ids
        self.assertNotEqual(_safe_scene_dir("combat!"), "combat")
        self.assertNotEqual(_safe_scene_dir("foo/bar"), _safe_scene_dir("foo_bar"))
        self.assertEqual(_safe_scene_dir("foo_bar"), "foo_bar")

    def test_find_manifest_without_scene_prefers_global(self) -> None:
        """No --scene → global manifest even if a newer scene manifest exists."""
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        base = self.tmp_path / "vt"
        global_dir = base
        scene_dir = base / "combat"
        global_dir.mkdir(parents=True)
        scene_dir.mkdir(parents=True)
        global_m = global_dir / "manifest.json"
        scene_m = scene_dir / "manifest.json"
        global_m.write_text(
            json.dumps(
                {
                    "brief_path": str(brief),
                    "candidates": [{"id": "a", "path": "old.png"}],
                }
            ),
            encoding="utf-8",
        )
        import time

        time.sleep(0.02)
        scene_m.write_text(
            json.dumps(
                {
                    "brief_path": str(brief),
                    "scene_id": "combat",
                    "candidates": [{"id": "b", "path": "new.png"}],
                }
            ),
            encoding="utf-8",
        )
        with patch(
            "visual_target.default_output_dir",
            side_effect=lambda bp, scene_id=None: (
                scene_dir if scene_id else global_dir
            ),
        ):
            listed = find_manifest_for_brief(brief, None)
            picked = find_manifest_for_brief(brief, None)
            scene_found = find_manifest_for_brief(brief, None, scene_id="combat")
        self.assertEqual(listed.resolve(), global_m.resolve())
        self.assertEqual(picked.resolve(), global_m.resolve())
        self.assertEqual(scene_found.resolve(), scene_m.resolve())

    def test_find_manifest_without_global_requires_scene(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        base = self.tmp_path / "vt-only-scene"
        scene_dir = base / "combat"
        scene_dir.mkdir(parents=True)
        (scene_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "brief_path": str(brief),
                    "scene_id": "combat",
                    "candidates": [{"id": "a", "path": "x.png"}],
                }
            ),
            encoding="utf-8",
        )
        with patch(
            "visual_target.default_output_dir",
            side_effect=lambda bp, scene_id=None: (
                scene_dir if scene_id else base
            ),
        ):
            with self.assertRaises(Exception) as ctx:
                find_manifest_for_brief(brief, None)
        self.assertIn("--scene", str(ctx.exception))

    def test_find_manifest_tries_multiple_scene_ids(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        dock_dir = self.tmp_path / "visual-target" / "dock"
        dock_dir.mkdir(parents=True)
        man = dock_dir / "manifest.json"
        man.write_text(
            json.dumps(
                {
                    "brief_path": str(brief),
                    "scene_id": "dock",
                    "candidates": [{"id": "a", "path": "x.png"}],
                }
            ),
            encoding="utf-8",
        )
        with patch(
            "visual_target.default_output_dir",
            side_effect=lambda bp, scene_id=None: (
                self.tmp_path / "visual-target" / str(scene_id)
                if scene_id
                else self.tmp_path / "visual-target"
            ),
        ):
            # combat missing, dock present — second id wins
            found = find_manifest_for_brief(
                brief, None, scene_ids=["combat", "dock"]
            )
        self.assertEqual(found.resolve(), man.resolve())

    def test_generate_dry_run_scene_subdir_and_manifest(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out = self.tmp_path / "visual-target" / "combat"
        plans = self.tmp_path / "plans"
        manifest = generate_visual_targets(
            brief,
            out,
            count=2,
            config={},
            dry_run=True,
            craft=False,
            plans_dir=plans,
            scene_id="combat",
        )
        self.assertEqual(manifest["scene_id"], "combat")
        self.assertTrue((out / "manifest.json").is_file())
        prompt = manifest["candidates"][0]["prompt"].lower()
        self.assertTrue(
            "搏鱼" in prompt or "tense fight" in prompt or "combat" in prompt,
            msg=prompt[:400],
        )

    def test_generate_clears_stale_partial_before_retry(self) -> None:
        """Failed prior run left hollow scene dir + half plan; retry must start clean."""
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out = self.tmp_path / "visual-target" / "combat"
        plans = self.tmp_path / "plans" / "combat"
        out.mkdir(parents=True)
        plans.mkdir(parents=True)
        stale_png = out / "candidate_a.png"
        stale_png.write_bytes(b"\x89PNG-stale")
        (plans / "candidate_a.json").write_text('{"stale": true}', encoding="utf-8")
        # No manifest — mirrors mid-run image API failure.

        manifest = generate_visual_targets(
            brief,
            out,
            count=2,
            config={},
            dry_run=True,
            craft=False,
            plans_dir=plans,
            scene_id="combat",
        )
        self.assertTrue((out / "manifest.json").is_file())
        self.assertEqual(len(manifest["candidates"]), 2)
        self.assertFalse(stale_png.is_file())
        handoff = json.loads(
            Path(manifest["candidates"][0]["handoff_path"]).read_text(encoding="utf-8")
        )
        self.assertNotIn("stale", handoff)

    def test_generate_image_failure_rolls_back_scene_artifacts(self) -> None:
        """Image API errors must not leave empty scene dirs or partial candidates."""
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out = self.tmp_path / "visual-target" / "combat"
        plans = self.tmp_path / "plans" / "combat"
        sibling = self.tmp_path / "visual-target" / "dock"
        sibling.mkdir(parents=True)
        (sibling / "keep.txt").write_text("keep", encoding="utf-8")

        def fake_generate_image(**kwargs: object) -> None:
            out_path = Path(str(kwargs["output"]))
            # Fail a specific variant so parallel runs stay deterministic.
            if out_path.name == "candidate_a.png":
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"\x89PNG-ok")
                return
            raise RuntimeError("503 no available channel")

        with patch("gamefactory.generate_image", side_effect=fake_generate_image), patch(
            "gamefactory.resolve_image_proxy", return_value=None
        ), patch(
            "image_model_route.resolve_image_credentials",
            return_value=type(
                "C",
                (),
                {
                    "model": "gpt-image-2",
                    "api_key": "test-key",
                    "api_base": "https://api.example.com/v1",
                },
            )(),
        ):
            with self.assertRaises(RuntimeError):
                generate_visual_targets(
                    brief,
                    out,
                    count=2,
                    config={"image": {"api_key": "x", "model": "gpt-image-2"}},
                    dry_run=False,
                    craft=False,
                    plans_dir=plans,
                    scene_id="combat",
                )

        self.assertFalse(out.exists())
        self.assertFalse(plans.exists())
        self.assertFalse((out / "manifest.json").exists())
        self.assertTrue((sibling / "keep.txt").is_file())

    def test_generate_runs_candidates_in_parallel(self) -> None:
        """Three candidates should overlap in flight (not purely sequential)."""
        import threading
        import time

        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out = self.tmp_path / "visual-target" / "combat"
        plans = self.tmp_path / "plans" / "combat"
        lock = threading.Lock()
        active = 0
        max_active = 0

        def fake_generate_image(**kwargs: object) -> None:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.08)
            out_path = Path(str(kwargs["output"]))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"\x89PNG")
            with lock:
                active -= 1

        with patch("gamefactory.generate_image", side_effect=fake_generate_image), patch(
            "gamefactory.resolve_image_proxy", return_value=None
        ), patch(
            "image_model_route.resolve_image_credentials",
            return_value=type(
                "C",
                (),
                {
                    "model": "gpt-image-2",
                    "api_key": "test-key",
                    "api_base": "https://api.example.com/v1",
                },
            )(),
        ):
            manifest = generate_visual_targets(
                brief,
                out,
                count=3,
                config={"image": {"api_key": "x", "model": "gpt-image-2"}},
                dry_run=False,
                craft=False,
                plans_dir=plans,
                scene_id="combat",
            )

        self.assertEqual(len(manifest["candidates"]), 3)
        self.assertEqual([c["id"] for c in manifest["candidates"]], ["a", "b", "c"])
        self.assertEqual(manifest.get("parallel"), 3)
        self.assertGreaterEqual(max_active, 2)

    def test_clear_artifacts_preserves_sibling_scene_dirs(self) -> None:
        base = self.tmp_path / "visual-target"
        scene = base / "main_hub"
        plans = self.tmp_path / "plans"
        base.mkdir()
        scene.mkdir()
        (base / "candidate_a.png").write_bytes(b"png")
        (base / "manifest.json").write_text("{}", encoding="utf-8")
        (base / "selected.png").write_bytes(b"picked")
        (scene / "keep.png").write_bytes(b"keep")
        plans.mkdir()
        (plans / "candidate_a.json").write_text("{}", encoding="utf-8")

        clear_visual_target_run_artifacts(base, plans)

        self.assertFalse((base / "candidate_a.png").exists())
        self.assertFalse((base / "manifest.json").exists())
        self.assertFalse((plans / "candidate_a.json").exists())
        self.assertTrue((base / "selected.png").is_file())
        self.assertTrue((scene / "keep.png").is_file())

    def test_failed_regenerate_keeps_previous_selected_png(self) -> None:
        """Regenerate that dies mid-image must not break an already-picked north star."""
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out = self.tmp_path / "visual-target" / "combat"
        plans = self.tmp_path / "plans" / "combat"
        out.mkdir(parents=True)
        plans.mkdir(parents=True)
        selected = out / "selected.png"
        selected.write_bytes(b"\x89PNG-picked")
        (out / "candidate_a.png").write_bytes(b"\x89PNG-old")
        (out / "manifest.json").write_text(
            json.dumps({"candidates": [{"id": "a"}]}), encoding="utf-8"
        )

        with patch("gamefactory.generate_image", side_effect=RuntimeError("503")), patch(
            "gamefactory.resolve_image_proxy", return_value=None
        ), patch(
            "image_model_route.resolve_image_credentials",
            return_value=type(
                "C",
                (),
                {
                    "model": "gpt-image-2",
                    "api_key": "test-key",
                    "api_base": "https://api.example.com/v1",
                },
            )(),
        ):
            with self.assertRaises(RuntimeError):
                generate_visual_targets(
                    brief,
                    out,
                    count=1,
                    config={"image": {"api_key": "x", "model": "gpt-image-2"}},
                    dry_run=False,
                    craft=False,
                    plans_dir=plans,
                    scene_id="combat",
                )

        # Scene dir may remain solely for selected.png (pick artifact).
        self.assertTrue(selected.is_file())
        self.assertEqual(selected.read_bytes(), b"\x89PNG-picked")
        self.assertFalse((out / "candidate_a.png").exists())
        self.assertFalse((out / "manifest.json").exists())

    def test_pick_scene_writes_scene_ref_without_seeding_global(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out_dir = self.tmp_path / "visual-target" / "combat"
        out_dir.mkdir(parents=True)
        fake_png = out_dir / "candidate_a.png"
        fake_png.write_bytes(b"\x89PNG\r\n")
        manifest = {
            "viewport_size": "1280x720",
            "scene_id": "combat",
            "candidates": [
                {"id": "a", "label": "opening", "path": str(fake_png)},
            ],
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with patch("project_paths.repo_root", return_value=self.tmp_path):
            result = apply_visual_target_pick(
                brief, "a", manifest_path, scene_id="combat"
            )

        self.assertEqual(result["scene_id"], "combat")
        data = json.loads(brief.read_text(encoding="utf-8"))
        scenes = {s["id"]: s for s in data["project"]["scenes"]}
        self.assertTrue(scenes["combat"]["visual_reference"])
        # Scene pick must not seed global (avoids wrong style-img2img fallback).
        self.assertFalse(str(data["project"].get("visual_reference") or "").strip())
        self.assertTrue(brief_has_any_visual_reference(brief))
        self.assertTrue((out_dir / "selected.png").is_file())
        self.assertNotIn("visual_reference", scenes["dock"])

    def test_pick_scene_does_not_overwrite_existing_global(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        data = json.loads(brief.read_text(encoding="utf-8"))
        data["project"]["visual_reference"] = "output/keep/global.png"
        brief.write_text(json.dumps(data), encoding="utf-8")

        out_dir = self.tmp_path / "visual-target" / "dock"
        out_dir.mkdir(parents=True)
        fake_png = out_dir / "candidate_b.png"
        fake_png.write_bytes(b"\x89PNG\r\n")
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "viewport_size": "1280x720",
                    "scene_id": "dock",
                    "candidates": [
                        {"id": "b", "label": "calm", "path": str(fake_png)},
                    ],
                }
            ),
            encoding="utf-8",
        )
        with patch("project_paths.repo_root", return_value=self.tmp_path):
            apply_visual_target_pick(brief, "b", manifest_path, scene_id="dock")

        updated = json.loads(brief.read_text(encoding="utf-8"))
        self.assertEqual(updated["project"]["visual_reference"], "output/keep/global.png")
        dock = next(s for s in updated["project"]["scenes"] if s["id"] == "dock")
        self.assertTrue(dock["visual_reference"])
        self.assertNotEqual(dock["visual_reference"], "output/keep/global.png")

    def test_resolve_falls_back_to_global(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        global_png = self.tmp_path / "global.png"
        global_png.write_bytes(b"\x89PNG\r\n")
        data = json.loads(brief.read_text(encoding="utf-8"))
        data["project"]["visual_reference"] = str(global_png)
        brief.write_text(json.dumps(data), encoding="utf-8")

        self.assertEqual(resolve_visual_reference_path(brief), global_png.resolve())
        self.assertIsNone(resolve_visual_reference_path(brief, scene_id="combat"))
        self.assertEqual(
            resolve_visual_reference_for_asset(brief, scene_ids=["combat", "dock"]),
            global_png.resolve(),
        )
        self.assertTrue(brief_has_any_visual_reference(brief))

    def test_resolve_prefers_matching_scene(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        global_png = self.tmp_path / "global.png"
        scene_png = self.tmp_path / "combat.png"
        global_png.write_bytes(b"\x89PNG\r\n")
        scene_png.write_bytes(b"\x89PNG\r\n")
        data = json.loads(brief.read_text(encoding="utf-8"))
        data["project"]["visual_reference"] = str(global_png)
        for scene in data["project"]["scenes"]:
            if scene["id"] == "combat":
                scene["visual_reference"] = str(scene_png)
        brief.write_text(json.dumps(data), encoding="utf-8")

        self.assertEqual(
            resolve_visual_reference_path(brief, scene_id="combat"),
            scene_png.resolve(),
        )
        self.assertEqual(
            resolve_visual_reference_for_asset(brief, scene_ids=["combat", "dock"]),
            scene_png.resolve(),
        )
        # Unknown scene id → fall through to global
        self.assertEqual(
            resolve_visual_reference_for_asset(brief, scene_ids=["missing"]),
            global_png.resolve(),
        )
        st = visual_target_brief_status(brief)
        self.assertTrue(st["ready"])
        self.assertTrue(st["global_ready"])
        combat = next(s for s in st["scenes"] if s["id"] == "combat")
        self.assertTrue(combat["ready"])
        dock = next(s for s in st["scenes"] if s["id"] == "dock")
        self.assertFalse(dock["ready"])

    def test_match_scenes_prompt_vs_description(self) -> None:
        scenes = [
            {
                "id": "dock",
                "title": "钓场",
                "summary": "Calm pier casting on the harbor.",
                "notes": "wide horizon pier",
            },
            {
                "id": "combat",
                "title": "搏鱼",
                "summary": "Tense fight UI and struggle bar.",
            },
            {
                "id": "aquarium",
                "title": "水族馆",
                "summary": "Indoor fish tank collection display.",
                "visual_reference": "output/already.png",
            },
        ]
        pier_prompt = (
            "Full viewport gameplay mock of calm pier casting harbor dock, "
            "wide horizon, fishing rod, peaceful water."
        )
        ranked = match_scenes_for_north_star(scenes, prompt=pier_prompt)
        ids = [r["id"] for r in ranked]
        self.assertIn("dock", ids)
        self.assertNotIn("combat", ids)
        # already has visual_reference → skipped
        self.assertNotIn("aquarium", ids)

        fight_prompt = "tense fight struggle combat UI reel battle bar"
        fight_ids = [r["id"] for r in match_scenes_for_north_star(scenes, prompt=fight_prompt)]
        self.assertIn("combat", fight_ids)
        self.assertNotIn("dock", fight_ids)

    def test_pick_auto_matches_similar_empty_scenes(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        data = json.loads(brief.read_text(encoding="utf-8"))
        # Add a second calm scene that should share dock's north star
        data["project"]["scenes"].append(
            {
                "id": "harbor_shop",
                "title": "码头商店",
                "summary": "Calm pier shop near the harbor casting area.",
                "notes": "same dock mood, wide horizon",
            }
        )
        brief.write_text(json.dumps(data), encoding="utf-8")

        out_dir = self.tmp_path / "visual-target" / "dock"
        out_dir.mkdir(parents=True)
        fake_png = out_dir / "candidate_a.png"
        fake_png.write_bytes(b"\x89PNG\r\n")
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "viewport_size": "1280x720",
                    "scene_id": "dock",
                    "candidates": [
                        {
                            "id": "a",
                            "label": "opening",
                            "prompt_summary": "Calm pier casting harbor",
                            "prompt": (
                                "Calm pier casting on the harbor dock, "
                                "wide horizon, peaceful fishing water."
                            ),
                            "path": str(fake_png),
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        with patch("project_paths.repo_root", return_value=self.tmp_path):
            result = apply_visual_target_pick(
                brief,
                "a",
                manifest_path,
                scene_id="dock",
                auto_match_scenes=True,
                config={},  # force heuristic (no LLM key)
            )
        self.assertEqual(result.get("scene_ids"), ["dock"])
        self.assertIn("harbor_shop", result.get("auto_matched_scene_ids") or [])
        updated = json.loads(brief.read_text(encoding="utf-8"))
        scenes = {s["id"]: s for s in updated["project"]["scenes"]}
        self.assertEqual(
            scenes["dock"]["visual_reference"],
            scenes["harbor_shop"]["visual_reference"],
        )
        # Contrasting combat must stay empty
        self.assertNotIn("visual_reference", scenes["combat"])
        # Scene generate scope stays dock (auto_match must not rewrite scene_id).
        remanifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(remanifest.get("scene_id"), "dock")
        self.assertEqual(remanifest.get("scene_ids"), ["dock"])
        self.assertIn("harbor_shop", remanifest.get("auto_matched_scene_ids") or [])

    def test_global_pick_auto_match_keeps_manifest_global(self) -> None:
        """Global generate/pick must not become scene-scoped via auto_match."""
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        data = json.loads(brief.read_text(encoding="utf-8"))
        data["project"]["scenes"].append(
            {
                "id": "harbor_shop",
                "title": "码头商店",
                "summary": "Calm pier shop near the harbor casting area.",
                "notes": "same dock mood, wide horizon",
            }
        )
        brief.write_text(json.dumps(data), encoding="utf-8")
        out_dir = self.tmp_path / "visual-target"
        out_dir.mkdir(parents=True)
        fake_png = out_dir / "candidate_a.png"
        fake_png.write_bytes(b"\x89PNG\r\n")
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "viewport_size": "1280x720",
                    "candidates": [
                        {
                            "id": "a",
                            "label": "opening",
                            "prompt": (
                                "Calm pier casting on the harbor dock, "
                                "wide horizon, peaceful fishing water."
                            ),
                            "path": str(fake_png),
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        with patch("project_paths.repo_root", return_value=self.tmp_path):
            result = apply_visual_target_pick(
                brief,
                "a",
                manifest_path,
                auto_match_scenes=True,
                config={},
            )
        self.assertTrue(result.get("auto_matched_scene_ids"))
        # Return scope stays global — auto_match must not fill scene_ids.
        self.assertEqual(result.get("scene_ids") or [], [])
        self.assertIsNone(result.get("scene_id"))
        remanifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIsNone(remanifest.get("scene_id"))
        self.assertEqual(remanifest.get("scene_ids") or [], [])
        # Re-pick without --scene must still update global, not scene-only.
        with patch("project_paths.repo_root", return_value=self.tmp_path):
            apply_visual_target_pick(
                brief,
                "a",
                manifest_path,
                auto_match_scenes=False,
                config={},
            )
        updated = json.loads(brief.read_text(encoding="utf-8"))
        self.assertTrue(str(updated["project"].get("visual_reference") or "").strip())
        remanifest2 = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertNotIn("auto_matched_scene_ids", remanifest2)
        self.assertNotIn("auto_match_method", remanifest2)

    def test_pick_infers_manifest_scene_ids_list(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out_dir = self.tmp_path / "visual-target" / "combat"
        out_dir.mkdir(parents=True)
        fake_png = out_dir / "candidate_a.png"
        fake_png.write_bytes(b"\x89PNG\r\n")
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "viewport_size": "1280x720",
                    "scene_id": "combat",
                    "scene_ids": ["combat", "dock"],
                    "candidates": [
                        {"id": "a", "label": "opening", "path": str(fake_png)},
                    ],
                }
            ),
            encoding="utf-8",
        )
        with patch("project_paths.repo_root", return_value=self.tmp_path):
            result = apply_visual_target_pick(
                brief, "a", manifest_path, auto_match_scenes=False
            )
        self.assertEqual(result["scene_ids"], ["combat", "dock"])
        data = json.loads(brief.read_text(encoding="utf-8"))
        scenes = {s["id"]: s for s in data["project"]["scenes"]}
        self.assertEqual(
            scenes["combat"]["visual_reference"],
            scenes["dock"]["visual_reference"],
        )

    def test_pick_auto_match_does_not_overwrite(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        data = json.loads(brief.read_text(encoding="utf-8"))
        data["project"]["scenes"].append(
            {
                "id": "harbor_shop",
                "title": "码头商店",
                "summary": "Calm pier shop near the harbor.",
                "visual_reference": "output/keep-me.png",
            }
        )
        brief.write_text(json.dumps(data), encoding="utf-8")
        out_dir = self.tmp_path / "visual-target" / "dock"
        out_dir.mkdir(parents=True)
        fake_png = out_dir / "candidate_a.png"
        fake_png.write_bytes(b"\x89PNG\r\n")
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "viewport_size": "1280x720",
                    "scene_id": "dock",
                    "candidates": [
                        {
                            "id": "a",
                            "label": "opening",
                            "prompt": "Calm pier casting harbor dock wide horizon",
                            "path": str(fake_png),
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        with patch("project_paths.repo_root", return_value=self.tmp_path):
            apply_visual_target_pick(
                brief,
                "a",
                manifest_path,
                scene_id="dock",
                auto_match_scenes=True,
                config={},
            )
        updated = json.loads(brief.read_text(encoding="utf-8"))
        shop = next(s for s in updated["project"]["scenes"] if s["id"] == "harbor_shop")
        self.assertEqual(shop["visual_reference"], "output/keep-me.png")

    def test_pick_multiple_scenes_share_same_path(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        out_dir = self.tmp_path / "visual-target" / "combat"
        out_dir.mkdir(parents=True)
        fake_png = out_dir / "candidate_a.png"
        fake_png.write_bytes(b"\x89PNG\r\n")
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "viewport_size": "1280x720",
                    "scene_id": "combat",
                    "candidates": [
                        {"id": "a", "label": "opening", "path": str(fake_png)},
                    ],
                }
            ),
            encoding="utf-8",
        )
        with patch("project_paths.repo_root", return_value=self.tmp_path):
            result = apply_visual_target_pick(
                brief,
                "a",
                manifest_path,
                scene_ids=["combat", "dock"],
            )
        self.assertEqual(result["scene_ids"], ["combat", "dock"])
        data = json.loads(brief.read_text(encoding="utf-8"))
        scenes = {s["id"]: s for s in data["project"]["scenes"]}
        self.assertEqual(
            scenes["combat"]["visual_reference"],
            scenes["dock"]["visual_reference"],
        )
        self.assertEqual(scenes["combat"]["visual_reference"], result["visual_reference"])

    def test_assign_skips_existing_unless_overwrite(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        combat_png = self.tmp_path / "combat.png"
        dock_png = self.tmp_path / "dock.png"
        combat_png.write_bytes(b"\x89PNG\r\n")
        dock_png.write_bytes(b"\x89PNG\r\n")
        data = json.loads(brief.read_text(encoding="utf-8"))
        for scene in data["project"]["scenes"]:
            if scene["id"] == "combat":
                scene["visual_reference"] = str(combat_png)
            if scene["id"] == "dock":
                scene["visual_reference"] = str(dock_png)
        brief.write_text(json.dumps(data), encoding="utf-8")

        with patch("project_paths.repo_root", return_value=self.tmp_path):
            result = assign_visual_reference_to_scenes(
                brief, scene_ids=["dock"], from_scene="combat"
            )
        self.assertEqual(result["scene_ids"], [])
        self.assertEqual(result["skipped_scene_ids"], ["dock"])
        updated = json.loads(brief.read_text(encoding="utf-8"))
        dock = next(s for s in updated["project"]["scenes"] if s["id"] == "dock")
        self.assertEqual(dock["visual_reference"], str(dock_png))

        with patch("project_paths.repo_root", return_value=self.tmp_path):
            forced = assign_visual_reference_to_scenes(
                brief, scene_ids=["dock"], from_scene="combat", overwrite=True
            )
        self.assertEqual(forced["scene_ids"], ["dock"])
        updated = json.loads(brief.read_text(encoding="utf-8"))
        dock = next(s for s in updated["project"]["scenes"] if s["id"] == "dock")
        self.assertEqual(dock["visual_reference"], str(combat_png))

    def test_suggest_falls_back_when_llm_returns_empty(self) -> None:
        from visual_target import suggest_auto_match_scene_ids

        project = {
            "scenes": [
                {
                    "id": "dock",
                    "title": "钓场",
                    "summary": "Calm pier casting harbor",
                },
                {
                    "id": "combat",
                    "title": "搏鱼",
                    "summary": "Tense fight UI",
                },
            ]
        }
        with patch(
            "visual_target.match_scenes_for_north_star_llm",
            return_value=[],
        ):
            ids, method = suggest_auto_match_scene_ids(
                project,
                prompt="Calm pier casting harbor dock wide horizon",
                primary_scene_id=None,
                use_llm=True,
                config={"prompt": {"api_key": "x"}},
            )
        self.assertEqual(method, "heuristic")
        self.assertIn("dock", ids)
        self.assertNotIn("combat", ids)

    def test_assign_shares_path_without_copy(self) -> None:
        brief = _write_example_brief(self.tmp_path, with_scenes=True)
        shared = self.tmp_path / "shared.png"
        shared.write_bytes(b"\x89PNG\r\n")
        data = json.loads(brief.read_text(encoding="utf-8"))
        for scene in data["project"]["scenes"]:
            if scene["id"] == "combat":
                scene["visual_reference"] = str(shared)
        brief.write_text(json.dumps(data), encoding="utf-8")

        with patch("project_paths.repo_root", return_value=self.tmp_path):
            result = assign_visual_reference_to_scenes(
                brief,
                scene_ids=["dock"],
                from_scene="combat",
            )
        self.assertEqual(result["scene_ids"], ["dock"])
        updated = json.loads(brief.read_text(encoding="utf-8"))
        scenes = {s["id"]: s for s in updated["project"]["scenes"]}
        self.assertEqual(
            scenes["dock"]["visual_reference"],
            scenes["combat"]["visual_reference"],
        )
        # Same path string → asset resolve for dock uses combat's image
        self.assertEqual(
            resolve_visual_reference_for_asset(brief, scene_ids=["dock"]),
            shared.resolve(),
        )

    def test_legacy_global_only_unchanged(self) -> None:
        """Old briefs with only project.visual_reference keep prior behavior."""
        global_png = self.tmp_path / "selected.png"
        global_png.write_bytes(b"\x89PNG\r\n")
        data = json.loads(self.example_brief.read_text(encoding="utf-8"))
        data["project"]["visual_reference"] = str(global_png)
        self.example_brief.write_text(json.dumps(data), encoding="utf-8")

        self.assertEqual(
            resolve_visual_reference_path(self.example_brief),
            global_png.resolve(),
        )
        self.assertEqual(
            resolve_visual_reference_for_asset(
                self.example_brief, scene_ids=["anything"]
            ),
            global_png.resolve(),
        )
        st = visual_target_brief_status(self.example_brief)
        self.assertTrue(st["ready"])
        self.assertEqual(st["scenes"], [])


if __name__ == "__main__":
    unittest.main()
