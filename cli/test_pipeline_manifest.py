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

            self.assertGreaterEqual(updated, 1)
            task = next(t for t in tasks_list(manifest) if t["id"] == "knight.prompt.craft")
            self.assertEqual(task["status"], "done")

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
        self.assertEqual(assemble["layer"], matte["layer"] + 1)

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
