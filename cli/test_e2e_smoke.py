"""E2E smoke tests — plan + dry-run (no API); optional live run via env."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from pipeline_manifest import build_manifest, tasks_list
from pipeline_runner import run_pipeline

_REPO = Path(__file__).resolve().parent.parent
_SMOKE_BRIEF = _REPO / "tests" / "fixtures" / "briefs" / "e2e-smoke-brief.json"
_PLANNED_MANIFEST = _REPO / "tests" / "fixtures" / "manifests" / "e2e-smoke-planned.json"


class E2eSmokeTests(unittest.TestCase):
    def test_smoke_brief_builds_minimal_dag(self) -> None:
        manifest = build_manifest(
            _SMOKE_BRIEF,
            output_dir=_REPO / "output" / "e2e-smoke",
            godot_project=_REPO / "games" / "e2e-smoke",
            include_game_dev=False,
        )
        ids = {t["id"] for t in tasks_list(manifest)}
        self.assertIn("slime_hero.prompt.craft", ids)
        self.assertIn("slime_hero.image.generate", ids)
        self.assertIn("slime_hero.image.remove-bg", ids)
        self.assertEqual(len(ids), 4)

    def test_planned_manifest_fixture_matches_shape(self) -> None:
        self.assertTrue(_PLANNED_MANIFEST.is_file())
        data = json.loads(_PLANNED_MANIFEST.read_text(encoding="utf-8"))
        ids = {t["id"] for t in data.get("tasks", [])}
        self.assertIn("slime_hero.prompt.craft", ids)

    def test_dry_run_single_wave(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "e2e-smoke.json"
            manifest = build_manifest(
                _SMOKE_BRIEF,
                output_dir=Path(tmp) / "output",
                include_godot=False,
                include_game_dev=False,
            )
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            result = run_pipeline(
                manifest_path,
                jobs=2,
                run_prompts=True,
                dry_run=True,
            )
        self.assertFalse(result.complete)
        self.assertIn("Dry run", result.message)


@unittest.skipUnless(os.environ.get("GAMEFACTORY_E2E_LIVE") == "1", "Set GAMEFACTORY_E2E_LIVE=1 for API run")
class E2eLiveTests(unittest.TestCase):
    def test_live_smoke_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "output"
            manifest_path = Path(tmp) / "manifest.json"
            manifest = build_manifest(
                _SMOKE_BRIEF,
                output_dir=out,
                include_godot=False,
                include_game_dev=False,
            )
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            result = run_pipeline(manifest_path, jobs=2, run_prompts=True)
            self.assertTrue(result.complete or result.paused, result.message)


if __name__ == "__main__":
    unittest.main()
