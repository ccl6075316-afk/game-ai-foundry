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


_REPO = Path(__file__).resolve().parent.parent
_BRIEF = _REPO / "resources" / "test-brief-dino-idle.json"


class PipelineManifestTest(unittest.TestCase):
    def test_dino_idle_dag(self) -> None:
        manifest = build_manifest(_BRIEF)
        ids = {t["id"] for t in tasks_list(manifest)}

        self.assertIn("raptor_scavenger.prompt.craft", ids)
        self.assertIn("raptor_scavenger.image.generate", ids)
        self.assertIn("raptor_scavenger_idle.prompt.craft", ids)
        self.assertIn("raptor_scavenger_idle.video.generate", ids)
        self.assertIn("raptor_scavenger_idle.video.split-frames", ids)
        self.assertIn("raptor_scavenger_idle.video.matte-frames", ids)

        video = next(t for t in tasks_list(manifest) if t["id"] == "raptor_scavenger_idle.video.generate")
        self.assertIn("raptor_scavenger.image.generate", video["depends_on"])
        self.assertIn("raptor_scavenger_idle.prompt.craft", video["depends_on"])

        ready = ready_tasks(manifest)
        ready_ids = {t["id"] for t in ready}
        self.assertIn("raptor_scavenger.prompt.craft", ready_ids)
        self.assertIn("raptor_scavenger_idle.prompt.craft", ready_ids)
        self.assertNotIn("raptor_scavenger_idle.video.generate", ready_ids)

    def test_record_and_ready_progression(self) -> None:
        manifest = build_manifest(_BRIEF)
        for task_id in ("raptor_scavenger.prompt.craft", "raptor_scavenger_idle.prompt.craft"):
            record_task(manifest, task_id, status="done", result={"exit_code": 0})

        ready_ids = {t["id"] for t in ready_tasks(manifest)}
        self.assertIn("raptor_scavenger.image.generate", ready_ids)
        self.assertNotIn("raptor_scavenger_idle.video.generate", ready_ids)

    def test_reconcile_plan_file(self) -> None:
        manifest = build_manifest(_BRIEF)
        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "cli"
            cli_dir.mkdir()
            plan_rel = "../plans/raptor.json"
            plan_path = (cli_dir / plan_rel).resolve()
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text("{}", encoding="utf-8")

            task = next(t for t in tasks_list(manifest) if t["id"] == "raptor_scavenger.prompt.craft")
            task["artifacts"]["plan"] = plan_rel

            import pipeline_manifest as pm

            old_cli = pm._CLI_DIR
            pm._CLI_DIR = cli_dir
            try:
                updated = reconcile_manifest(manifest)
            finally:
                pm._CLI_DIR = old_cli

            self.assertGreaterEqual(updated, 1)
            task = next(t for t in tasks_list(manifest) if t["id"] == "raptor_scavenger.prompt.craft")
            self.assertEqual(task["status"], "done")

    def test_prison_walk_manifest_includes_godot_task(self) -> None:
        brief = _REPO / "resources" / "test-brief-prison-walk.json"
        manifest = build_manifest(
            brief,
            output_dir=_REPO / "output" / "prison-test",
            godot_project=_REPO / "games" / "prison-demo",
        )
        ids = {t["id"] for t in tasks_list(manifest)}
        self.assertIn("prison_inmate_walk.video.matte-frames", ids)
        self.assertIn("test-brief-prison-walk.godot.assemble", ids)
        self.assertIn("test-brief-prison-walk.godot.dev-context", ids)

        matte = next(t for t in tasks_list(manifest) if t["id"] == "prison_inmate_walk.video.matte-frames")
        self.assertEqual(matte["status"], "pending")

        assemble = next(t for t in tasks_list(manifest) if t["id"] == "test-brief-prison-walk.godot.assemble")
        self.assertIn("prison_inmate_walk.video.matte-frames", assemble["depends_on"])
        self.assertEqual(assemble["layer"], matte["layer"] + 1)

        dev = next(t for t in tasks_list(manifest) if t["id"] == "test-brief-prison-walk.godot.dev-context")
        self.assertEqual(dev["role"], "godot-developer")
        self.assertIn("test-brief-prison-walk.godot.assemble", dev["depends_on"])
        self.assertEqual(dev["layer"], assemble["layer"] + 1)

    def test_asset_brief_example_layers(self) -> None:
        brief = _REPO / "resources" / "asset-brief.example.json"
        manifest = build_manifest(brief)
        summary = status_summary(manifest)
        self.assertGreater(summary["total"], 5)
        ready = ready_tasks(manifest)
        roles = {t["role"] for t in ready}
        self.assertIn("prompt-crafter", roles)


if __name__ == "__main__":
    unittest.main()
