"""Tests for playtest plan generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from playtest_plan import build_playtest_from_brief, load_playtest_plan, save_playtest_plan

_REPO = Path(__file__).resolve().parent.parent
_EXAMPLE = _REPO / "resources" / "asset-brief.example.json"


class PlaytestPlanTests(unittest.TestCase):
    def test_build_from_brief_has_steps(self) -> None:
        plan = build_playtest_from_brief(_EXAMPLE)
        self.assertEqual(plan["schema_version"], 1)
        ops = [s["op"] for s in plan["steps"]]
        self.assertIn("screenshot", ops)
        self.assertIn("press", ops)
        self.assertIn("move_right", plan["input_actions"])
        self.assertTrue(plan["visual_checks"])

    def test_roundtrip_save_load(self) -> None:
        plan = build_playtest_from_brief(_EXAMPLE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "playtest.json"
            save_playtest_plan(plan, path)
            loaded = load_playtest_plan(path)
            self.assertEqual(loaded["playtest_id"], plan["playtest_id"])
            self.assertEqual(len(loaded["steps"]), len(plan["steps"]))


if __name__ == "__main__":
    unittest.main()
