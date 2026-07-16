"""Tests for regression snapshot harness."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from progress import init_progress, save_progress
from production import derive_production, save_production
from regression import list_regression_plans, snapshot_passing_plan
from test_fixtures import EXAMPLE_BRIEF


class RegressionTest(unittest.TestCase):
    def test_snapshot_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prod_path = tmp_path / "production.json"
            save_production(derive_production(EXAMPLE_BRIEF), prod_path)
            progress = init_progress(brief_path=EXAMPLE_BRIEF, production_path=prod_path)
            progress_path = tmp_path / "progress.json"
            save_progress(progress, progress_path)

            plan_path = tmp_path / "playtest_smoke.json"
            plan_path.write_text(
                json.dumps({"schema_version": 1, "steps": [{"op": "wait_frames", "frames": 1}]}),
                encoding="utf-8",
            )
            entry = snapshot_passing_plan(progress_path, plan_path, label="smoke")
            self.assertTrue(Path(entry["plan_path"]).is_file())

            plans = list_regression_plans(progress_path=progress_path)
            self.assertEqual(len(plans), 1)
            self.assertEqual(plans[0].name, "smoke.json")

            reloaded = json.loads(progress_path.read_text(encoding="utf-8"))
            self.assertEqual(reloaded["phases"]["validation"]["regression"], "pass")
            self.assertEqual(len(reloaded["phases"]["validation"]["regression_snapshots"]), 1)


if __name__ == "__main__":
    unittest.main()
