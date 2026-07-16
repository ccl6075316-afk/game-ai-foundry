"""Tests for per-task playtest harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from production import derive_production, save_production
from task_playtest import build_playtest_for_task
from test_fixtures import EXAMPLE_BRIEF


class TaskPlaytestTest(unittest.TestCase):
    def test_build_task_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prod_path = Path(tmp) / "production.json"
            save_production(derive_production(EXAMPLE_BRIEF), prod_path)
            plan = build_playtest_for_task(EXAMPLE_BRIEF, prod_path, "player_controller")
            self.assertEqual(plan["task_id"], "player_controller")
            self.assertTrue(plan["steps"])
            self.assertTrue(plan["acceptance_criteria"])
            ops = {s.get("op") for s in plan["steps"] if isinstance(s, dict)}
            self.assertIn("assert_node", ops)
            self.assertIn("assert_action", ops)
            self.assertIn("assert_property", ops)


if __name__ == "__main__":
    unittest.main()
