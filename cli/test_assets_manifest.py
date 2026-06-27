"""Unit tests for assets manifest — brief contract + pipeline stage ledger."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from assets_manifest import (
    apply_task_to_assets_manifest,
    build_assets_manifest,
    load_assets_manifest,
    refresh_assets_manifest_from_pipeline,
    save_assets_manifest,
)
from brief import load_brief, resolve_generate_method, validate_brief_for_export
from pipeline_manifest import TASK_DONE, build_manifest, tasks_list
from test_fixtures import EXAMPLE_BRIEF, write_brief


class AssetsManifestTests(unittest.TestCase):
    def test_build_from_brief(self) -> None:
        manifest = build_assets_manifest(EXAMPLE_BRIEF)
        self.assertIn("knight", manifest["assets"])
        brief = manifest["assets"]["knight"]["brief"]
        self.assertEqual(brief["usage"], "reference_still")
        self.assertEqual(brief["generate_method"], "image")
        self.assertEqual(manifest["assets"]["knight_walk"]["brief"]["generate_method"], "video")

    def test_resolve_generate_method(self) -> None:
        _, assets = load_brief(EXAMPLE_BRIEF)
        by_name = {a.name: a for a in assets}
        self.assertEqual(resolve_generate_method(by_name["knight"]), "image")
        self.assertEqual(resolve_generate_method(by_name["knight_walk"]), "video")

    def test_validate_brief_requires_usage(self) -> None:
        bad = write_brief(
            {
                "project": {"title": "X"},
                "assets": [{"name": "a", "type": "character", "display_size": "64x64"}],
            }
        )
        try:
            project, assets = load_brief(bad)
            with self.assertRaises(ValueError):
                validate_brief_for_export(project, assets)
        finally:
            bad.unlink(missing_ok=True)

    def test_apply_task_stage(self) -> None:
        manifest = build_assets_manifest(EXAMPLE_BRIEF)
        task = {
            "id": "knight.image.generate",
            "asset": "knight",
            "step": "image.generate",
            "status": "done",
            "artifacts": {"output": "../output/asset-brief.example/knight_raw.png"},
        }
        self.assertTrue(apply_task_to_assets_manifest(manifest, task))
        stages = manifest["assets"]["knight"]["stages"]
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0]["stage"], "image.raw")
        self.assertEqual(stages[0]["next_consumer"], "orchestrator")

    def test_refresh_from_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            plans = Path(tmp) / "plans"
            pipeline = build_manifest(EXAMPLE_BRIEF, output_dir=out, plans_dir=plans, include_godot=False)
            for task in tasks_list(pipeline):
                if task["asset"] == "knight" and task["step"] == "image.generate":
                    task["status"] = TASK_DONE
                    break

            path = refresh_assets_manifest_from_pipeline(pipeline)
            self.assertIsNotNone(path)
            assert path is not None
            loaded = load_assets_manifest(path)
            knight_stages = loaded["assets"]["knight"]["stages"]
            self.assertTrue(any(s["stage"] == "image.raw" for s in knight_stages))

    def test_save_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assets-manifest.json"
            data = build_assets_manifest(EXAMPLE_BRIEF)
            save_assets_manifest(path, data)
            loaded = load_assets_manifest(path)
            self.assertEqual(loaded["assets"]["forest_bg"]["brief"]["usage"], "world_background")


if __name__ == "__main__":
    unittest.main()
