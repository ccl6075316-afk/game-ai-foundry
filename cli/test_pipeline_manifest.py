"""Tests for pipeline manifest DAG builder."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brief import AssetSpec, AssetType, ProjectContext, load_brief
from generation_fingerprint import (
    build_generation_input,
    embed_generation_fingerprint,
    is_handoff_generation_stale,
)
from plan_io import build_handoff
from pipeline_manifest import (
    build_manifest,
    ready_tasks,
    reconcile_manifest,
    record_task,
    status_summary,
    tasks_list,
    _collect_task_artifact_rels,
)
from test_fixtures import EXAMPLE_BRIEF


class PipelineManifestTest(unittest.TestCase):
    def test_example_brief_video_walk_dag(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        ids = {t["id"] for t in tasks_list(manifest)}

        self.assertIn("knight.prompt.craft", ids)
        self.assertIn("knight.image.generate", ids)
        self.assertIn("knight_walk.prompt.craft", ids)
        self.assertIn("knight_walk.video.generate", ids)
        self.assertIn("knight_walk.video.split-frames", ids)
        self.assertIn("knight_walk.video.matte-frames", ids)

        video = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.video.generate")
        self.assertIn("knight.image.generate", video["depends_on"])
        self.assertIn("knight_walk.prompt.craft", video["depends_on"])

        ready = ready_tasks(manifest)
        ready_ids = {t["id"] for t in ready}
        self.assertIn("knight.prompt.craft", ready_ids)
        self.assertIn("knight_walk.prompt.craft", ready_ids)
        self.assertNotIn("knight_walk.video.generate", ready_ids)

    def test_record_and_ready_progression(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        for task_id in ("knight.prompt.craft", "knight_walk.prompt.craft"):
            record_task(manifest, task_id, status="done", result={"exit_code": 0})

        ready_ids = {t["id"] for t in ready_tasks(manifest)}
        self.assertIn("knight.image.generate", ready_ids)
        self.assertNotIn("knight_walk.video.generate", ready_ids)

    def test_reconcile_plan_file(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "cli"
            cli_dir.mkdir()
            plan_rel = "../plans/knight.json"
            plan_path = (cli_dir / plan_rel).resolve()
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(
                json.dumps(
                    {
                        "handoff_version": 1,
                        "consumer_role": "image-generator",
                        "plan": {"prompt": "knight"},
                    }
                ),
                encoding="utf-8",
            )

            task = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            task["artifacts"]["plan"] = plan_rel

            import pipeline_manifest as pm

            old_cli = pm._CLI_DIR
            pm._CLI_DIR = cli_dir
            try:
                updated = reconcile_manifest(manifest)
            finally:
                pm._CLI_DIR = old_cli

            self.assertGreaterEqual(updated["promoted"], 1)
            self.assertGreaterEqual(updated["total"], 1)
            task = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            self.assertEqual(task["status"], "done")

    def test_reconcile_rejects_image_plan_for_animation_craft(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "cli"
            cli_dir.mkdir()
            plan_rel = "../plans/knight_walk.json"
            plan_path = (cli_dir / plan_rel).resolve()
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(
                json.dumps(
                    {
                        "handoff_version": 1,
                        "consumer_role": "image-generator",
                        "plan": {"prompt": "walk"},
                    }
                ),
                encoding="utf-8",
            )

            task = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.prompt.craft")
            task["artifacts"]["plan"] = plan_rel
            task["status"] = "pending"

            import pipeline_manifest as pm

            old_cli = pm._CLI_DIR
            pm._CLI_DIR = cli_dir
            try:
                updated = reconcile_manifest(manifest)
            finally:
                pm._CLI_DIR = old_cli

            task = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.prompt.craft")
            self.assertEqual(task["status"], "pending")
            self.assertEqual(updated["promoted"], 0)

    def test_reconcile_rejects_incomplete_split_frames_dir(self) -> None:
        """Partial/corrupt frame dirs must not be promoted to done."""
        from test_fixtures import MINIMAL_VIDEO_BRIEF, write_brief

        brief_path = write_brief(MINIMAL_VIDEO_BRIEF, prefix="split-recon-")
        self.addCleanup(lambda: brief_path.unlink(missing_ok=True))
        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "cli"
            cli_dir.mkdir()
            frames_rel = "../output/knight_walk_frames"
            frames_dir = (cli_dir / frames_rel).resolve()
            frames_dir.mkdir(parents=True)
            (frames_dir / "frame_0001.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
            (frames_dir / "frame_0002.png").write_bytes(b"truncated")

            manifest = build_manifest(brief_path)
            craft = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.prompt.craft")
            craft["status"] = "done"
            gen = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.video.generate")
            gen["status"] = "done"
            split = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.video.split-frames")
            split["status"] = "pending"
            split["artifacts"]["output_dir"] = frames_rel
            split["command"] = (
                "python gamefactory.py video split-frames "
                "--input x.mp4 --output-dir y --frames 8"
            )

            import pipeline_manifest as pm

            old_cli = pm._CLI_DIR
            pm._CLI_DIR = cli_dir
            try:
                updated = reconcile_manifest(manifest)
            finally:
                pm._CLI_DIR = old_cli

            split = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.video.split-frames")
            self.assertEqual(split["status"], "pending")
            self.assertEqual(updated["promoted"], 0)

    def test_invalidate_mismatched_craft_plans_resets_done(self) -> None:
        from pipeline_manifest import invalidate_mismatched_craft_plans, record_task

        manifest = build_manifest(EXAMPLE_BRIEF)
        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "cli"
            cli_dir.mkdir()
            plan_rel = "../plans/knight_walk.json"
            plan_path = (cli_dir / plan_rel).resolve()
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(
                json.dumps(
                    {
                        "handoff_version": 1,
                        "consumer_role": "image-generator",
                        "plan": {"prompt": "walk"},
                    }
                ),
                encoding="utf-8",
            )

            craft = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.prompt.craft")
            craft["artifacts"]["plan"] = plan_rel
            record_task(manifest, "knight_walk.prompt.craft", status="done", result={"exit_code": 0})
            record_task(manifest, "knight_walk.video.generate", status="failed", result={"exit_code": 1})

            import pipeline_manifest as pm

            old_cli = pm._CLI_DIR
            pm._CLI_DIR = cli_dir
            try:
                reset_ids = invalidate_mismatched_craft_plans(manifest)
            finally:
                pm._CLI_DIR = old_cli

            self.assertIn("knight_walk.prompt.craft", reset_ids)
            self.assertIn("knight_walk.video.generate", reset_ids)
            craft = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.prompt.craft")
            self.assertEqual(craft["status"], "pending")

    def test_invalidate_missing_output_resets_done_and_cascade(self) -> None:
        """Deleted unsatisfactory assets should re-queue done tasks on reconcile."""
        from pipeline_manifest import invalidate_missing_artifacts

        manifest = build_manifest(EXAMPLE_BRIEF)
        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "cli"
            cli_dir.mkdir()
            plan_rel = "../plans/knight.json"
            plan_path = (cli_dir / plan_rel).resolve()
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text("{}", encoding="utf-8")
            out_rel = "../output/knight_raw.png"
            out_path = (cli_dir / out_rel).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"png")

            prompt = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            prompt["artifacts"]["plan"] = plan_rel
            gen = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.generate")
            gen["artifacts"]["output"] = out_rel
            gen["artifacts"]["plan"] = plan_rel
            record_task(manifest, "knight.prompt.craft", status="done", result={"exit_code": 0})
            record_task(manifest, "knight.image.generate", status="done", result={"exit_code": 0})
            # Mark a downstream task done too — cascade should clear it.
            trim = next(
                (t for t in tasks_list(manifest) if t["id"] == "knight.image.trim"),
                None,
            )
            if trim is not None:
                record_task(manifest, "knight.image.trim", status="done", result={"exit_code": 0})

            out_path.unlink()

            import pipeline_manifest as pm

            old_cli = pm._CLI_DIR
            pm._CLI_DIR = cli_dir
            try:
                reset_ids = invalidate_missing_artifacts(manifest)
            finally:
                pm._CLI_DIR = old_cli

            self.assertIn("knight.image.generate", reset_ids)
            gen = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.generate")
            self.assertEqual(gen["status"], "pending")
            if trim is not None:
                trim = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.trim")
                self.assertEqual(trim["status"], "pending")
            # Prompt plan still on disk — stay done.
            prompt = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            self.assertEqual(prompt["status"], "done")

    def test_reconcile_does_not_promote_generate_on_plan_alone(self) -> None:
        """Plan on disk must not mark image.generate done when the PNG is missing."""
        manifest = build_manifest(EXAMPLE_BRIEF)
        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "cli"
            cli_dir.mkdir()
            plan_rel = "../plans/knight.json"
            plan_path = (cli_dir / plan_rel).resolve()
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(
                json.dumps(
                    {
                        "handoff_version": 1,
                        "consumer_role": "image-generator",
                        "plan": {"prompt": "knight"},
                    }
                ),
                encoding="utf-8",
            )
            out_rel = "../output/knight_raw.png"

            prompt = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            prompt["artifacts"]["plan"] = plan_rel
            gen = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.generate")
            gen["artifacts"]["plan"] = plan_rel
            gen["artifacts"]["output"] = out_rel

            import pipeline_manifest as pm

            old_cli = pm._CLI_DIR
            pm._CLI_DIR = cli_dir
            try:
                synced = reconcile_manifest(manifest)
            finally:
                pm._CLI_DIR = old_cli

            self.assertGreaterEqual(synced["promoted"], 1)
            prompt = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            self.assertEqual(prompt["status"], "done")
            gen = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.generate")
            self.assertEqual(gen["status"], "pending")

    def test_example_brief_manifest_includes_godot_task(self) -> None:
        manifest = build_manifest(
            EXAMPLE_BRIEF,
            output_dir=Path(tempfile.gettempdir()) / "gf-test-out",
            godot_project=Path(tempfile.gettempdir()) / "gf-test-game",
        )
        ids = {t["id"] for t in tasks_list(manifest)}
        self.assertIn("knight_walk.video.matte-frames", ids)
        self.assertIn("asset-brief.example.godot.assemble", ids)
        self.assertIn("asset-brief.example.godot.dev-context", ids)

        matte = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.video.matte-frames")
        self.assertEqual(matte["status"], "pending")

        assemble = next(t for t in tasks_list(manifest) if t["id"] == "asset-brief.example.godot.assemble")
        self.assertIn("knight_walk.video.matte-frames", assemble["depends_on"])
        by_id = {t["id"]: t for t in tasks_list(manifest)}
        max_dep_layer = max(by_id[d]["layer"] for d in assemble["depends_on"])
        self.assertEqual(assemble["layer"], max_dep_layer + 1)

        dev = next(t for t in tasks_list(manifest) if t["id"] == "asset-brief.example.godot.dev-context")
        self.assertEqual(dev["role"], "godot-developer")
        self.assertIn("asset-brief.example.godot.assemble", dev["depends_on"])
        self.assertEqual(dev["layer"], assemble["layer"] + 1)

    def test_reconcile_resets_stale_done_tasks(self) -> None:
        """Brief/spec change vs saved plan should invalidate done generate chain."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            cli_dir = repo / "cli"
            cli_dir.mkdir(parents=True)
            brief_rel = "resources/stale-test-brief.json"
            brief_path = repo / brief_rel
            brief_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(EXAMPLE_BRIEF, brief_path)

            out_dir = repo / "projects" / "stale-test" / "output"
            plans_dir = repo / "projects" / "stale-test" / "plans"
            manifest = build_manifest(
                brief_path,
                output_dir=out_dir,
                plans_dir=plans_dir,
            )

            plan_rel = "../projects/stale-test/plans/knight.json"
            plan_path = (cli_dir / plan_rel).resolve()
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            out_rel = "../projects/stale-test/output/knight_raw.png"
            out_path = (cli_dir / out_rel).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"png")

            project, assets = load_brief(brief_path)
            spec = next(a for a in assets if a.name == "knight")
            old_plan = embed_generation_fingerprint(
                {
                    "prompt": "old crafted prompt",
                    "asset_name": spec.name,
                    "asset_type": spec.type.value,
                    "image_size": "1024x1024",
                },
                spec=spec,
                project=project,
            )
            handoff = build_handoff(
                old_plan,
                context={
                    "asset": {
                        "id": spec.id,
                        "name": spec.name,
                        "type": spec.type.value,
                        "description": spec.description,
                    }
                },
            )
            plan_path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")

            prompt = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            prompt["artifacts"]["plan"] = plan_rel
            gen = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.generate")
            gen["artifacts"]["plan"] = plan_rel
            gen["artifacts"]["output"] = out_rel
            record_task(manifest, "knight.prompt.craft", status="done", result={"exit_code": 0})
            record_task(manifest, "knight.image.generate", status="done", result={"exit_code": 0})

            data = json.loads(brief_path.read_text(encoding="utf-8"))
            for asset in data.get("assets", []):
                if asset.get("name") == "knight":
                    asset["description"] = str(asset.get("description", "")) + " — sizing v2 refresh"
            brief_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            project2, assets2 = load_brief(brief_path)
            spec2 = next(a for a in assets2 if a.name == "knight")
            current = build_generation_input(spec2, project2)
            self.assertTrue(is_handoff_generation_stale(handoff, current))

            import pipeline_manifest as pm

            old_repo = pm._REPO_ROOT
            old_cli = pm._CLI_DIR
            pm._REPO_ROOT = repo
            pm._CLI_DIR = cli_dir
            try:
                synced = reconcile_manifest(manifest)
            finally:
                pm._REPO_ROOT = old_repo
                pm._CLI_DIR = old_cli

            self.assertGreaterEqual(synced.get("stale_invalidated", 0), 1)
            prompt = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            gen = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.generate")
            self.assertEqual(prompt["status"], "pending")
            self.assertEqual(gen["status"], "pending")
            self.assertFalse(out_path.is_file())
            self.assertFalse(plan_path.is_file())
            self.assertGreaterEqual(synced.get("stale_purged", 0), 1)

    def test_shard_notes_do_not_force_stale(self) -> None:
        """Spec shard notes are not part of generation fingerprint."""
        project = ProjectContext(title="t")
        spec = AssetSpec(
            name="bg",
            type=AssetType.BACKGROUND,
            id="bg_test",
            description="same description",
            aspect_ratio="16:9",
        )
        plan = embed_generation_fingerprint(
            {"prompt": "p", "asset_name": "bg", "asset_type": "background"},
            spec=spec,
            project=project,
        )
        handoff = build_handoff(
            plan,
            context={"asset": {"id": "bg_test", "description": "same description"}},
        )
        shard = {
            "id": "bg_test",
            "name": "bg",
            "type": "background",
            "description": "same description",
            "notes": "long shard-only notes that should not affect staleness",
        }
        current = build_generation_input(spec, project, raw_shard=shard)
        self.assertFalse(is_handoff_generation_stale(handoff, current))

    def test_collect_artifact_rels_skips_cross_asset_reference(self) -> None:
        task = {
            "step": "video.generate",
            "artifacts": {
                "plan": "../plans/walk.json",
                "reference_image": "../output/knight_raw.png",
                "output": "../output/walk.mp4",
                "kit_style_reference": "../output/anchor_raw.png",
            },
        }
        rels = _collect_task_artifact_rels(task)
        # plan is owned by prompt.craft — generate must not purge it.
        self.assertNotIn("../plans/walk.json", rels)
        self.assertIn("../output/walk.mp4", rels)
        self.assertNotIn("../output/knight_raw.png", rels)
        self.assertNotIn("../output/anchor_raw.png", rels)

    def test_collect_artifact_rels_craft_purges_plan(self) -> None:
        task = {
            "step": "prompt.craft",
            "artifacts": {"plan": "../plans/walk.json"},
        }
        self.assertEqual(
            _collect_task_artifact_rels(task),
            ["../plans/walk.json"],
        )

    def test_collect_artifact_rels_matte_skips_input_dir(self) -> None:
        task = {
            "step": "video.matte-frames",
            "artifacts": {
                "input_dir": "../output/walk_frames",
                "output_dir": "../output/walk_nobg",
            },
        }
        rels = _collect_task_artifact_rels(task)
        self.assertNotIn("../output/walk_frames", rels)
        self.assertIn("../output/walk_nobg", rels)

    def test_max_wave_filters_generation_dag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = json.loads(Path(EXAMPLE_BRIEF).read_text(encoding="utf-8"))
            deferred_names = {"mossy_rock"}
            for asset in brief.get("assets") or []:
                asset["production_wave"] = 2 if asset.get("name") in deferred_names else 1
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            out_dir = root / "output"
            plans_dir = root / "plans"
            full = build_manifest(
                brief_path,
                output_dir=out_dir,
                plans_dir=plans_dir,
                include_godot=False,
                include_game_dev=False,
            )
            wave1 = build_manifest(
                brief_path,
                output_dir=out_dir,
                plans_dir=plans_dir,
                include_godot=False,
                include_game_dev=False,
                max_wave=1,
            )
            full_names = {t["asset"] for t in tasks_list(full)}
            wave_names = {t["asset"] for t in tasks_list(wave1)}
            self.assertIn("mossy_rock", full_names)
            self.assertNotIn("mossy_rock", wave_names)
            self.assertLess(len(tasks_list(wave1)), len(tasks_list(full)))
            self.assertEqual(wave1.get("meta", {}).get("production_max_wave"), 1)

    def test_placeholder_assets_do_not_enter_generation_dag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = json.loads(Path(EXAMPLE_BRIEF).read_text(encoding="utf-8"))
            for asset in brief.get("assets") or []:
                if asset.get("name") == "mossy_rock":
                    asset["availability"] = "placeholder"
                    asset["placeholder_reason"] = "later"
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            manifest = build_manifest(
                brief_path,
                output_dir=root / "output",
                plans_dir=root / "plans",
                include_godot=False,
                include_game_dev=False,
            )
            asset_names = {t["asset"] for t in tasks_list(manifest)}
            self.assertNotIn("mossy_rock", asset_names)

    def test_placeholder_reference_asset_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = json.loads(Path(EXAMPLE_BRIEF).read_text(encoding="utf-8"))
            for asset in brief.get("assets") or []:
                if asset.get("name") == "knight":
                    asset["availability"] = "placeholder"
                    asset["placeholder_reason"] = "later"
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "placeholder|占位|reference_asset"):
                build_manifest(
                    brief_path,
                    output_dir=root / "output",
                    plans_dir=root / "plans",
                    include_godot=False,
                    include_game_dev=False,
                )

    def test_asset_brief_example_layers(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        summary = status_summary(manifest)
        self.assertGreater(summary["total"], 5)
        ready = ready_tasks(manifest)
        roles = {t["role"] for t in ready}
        self.assertIn("prompt-crafter", roles)


if __name__ == "__main__":
    unittest.main()
