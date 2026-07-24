"""Tests for pipeline manifest DAG builder."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline_manifest import (
    build_manifest,
    ready_tasks,
    reconcile_manifest,
    record_task,
    status_summary,
    tasks_list,
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
            plan_path.write_text("{}", encoding="utf-8")

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
            plan_path.write_text("{}", encoding="utf-8")
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

    def test_asset_brief_example_layers(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        summary = status_summary(manifest)
        self.assertGreater(summary["total"], 5)
        ready = ready_tasks(manifest)
        roles = {t["role"] for t in ready}
        self.assertIn("prompt-crafter", roles)


if __name__ == "__main__":
    unittest.main()
