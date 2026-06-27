"""E2E smoke tests — plan + dry-run (no API); optional live run via env."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from pipeline_manifest import build_manifest, tasks_list
from pipeline_runner import run_pipeline
from test_fixtures import SMOKE_BRIEF, write_brief

_REPO = Path(__file__).resolve().parent.parent
_SMOKE_BRIEF_PATH = _REPO / "tests" / "fixtures" / "briefs" / "e2e-smoke-brief.json"


class E2eSmokeTests(unittest.TestCase):
    def test_smoke_brief_builds_minimal_dag(self) -> None:
        brief_path = write_brief(SMOKE_BRIEF, prefix="smoke-brief-")
        self.addCleanup(lambda: brief_path.unlink(missing_ok=True))
        manifest = build_manifest(
            brief_path,
            output_dir=Path(tempfile.gettempdir()) / "gf-e2e-smoke-out",
            godot_project=Path(tempfile.gettempdir()) / "gf-e2e-smoke-game",
            include_game_dev=False,
        )
        ids = {t["id"] for t in tasks_list(manifest)}
        self.assertIn("slime_hero.prompt.craft", ids)
        self.assertIn("slime_hero.image.generate", ids)
        self.assertIn("slime_hero.image.remove-bg", ids)
        self.assertTrue(any(t.endswith(".godot.assemble") for t in ids))
        self.assertEqual(len(ids), 5)

    def test_fixture_brief_builds_godot_task(self) -> None:
        if not _SMOKE_BRIEF_PATH.is_file():
            self.skipTest("local e2e-smoke-brief.json not present")
        manifest = build_manifest(
            _SMOKE_BRIEF_PATH,
            output_dir=_REPO / "output" / "e2e-smoke",
            godot_project=_REPO / "games" / "e2e-smoke",
            include_game_dev=False,
        )
        ids = {t["id"] for t in tasks_list(manifest)}
        self.assertIn("e2e-smoke-brief.godot.assemble", ids)
        self.assertTrue(manifest.get("godot_project"))

    def test_dry_run_single_wave(self) -> None:
        brief_path = write_brief(SMOKE_BRIEF, prefix="smoke-brief-")
        self.addCleanup(lambda: brief_path.unlink(missing_ok=True))
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "e2e-smoke.json"
            manifest = build_manifest(
                brief_path,
                output_dir=Path(tmp) / "output",
                godot_project=Path(tmp) / "game",
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
    def test_live_smoke_run_with_godot(self) -> None:
        if not _SMOKE_BRIEF_PATH.is_file():
            self.skipTest("local e2e-smoke-brief.json not present")
        manifest_path = _REPO / "pipeline" / "e2e-smoke-godot.json"
        manifest = build_manifest(
            _SMOKE_BRIEF_PATH,
            output_dir=_REPO / "output" / "e2e-smoke-godot",
            godot_project=_REPO / "games" / "e2e-smoke-godot",
            include_game_dev=False,
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        result = run_pipeline(manifest_path, jobs=2, run_prompts=True)
        self.assertTrue(result.complete, result.message)
        self.assertTrue((_REPO / "games" / "e2e-smoke-godot" / "project.godot").is_file())


if __name__ == "__main__":
    unittest.main()
