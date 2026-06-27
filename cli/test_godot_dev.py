"""Tests for godot-developer handoff builder."""

from __future__ import annotations

import unittest
from pathlib import Path

from godot_dev import build_godot_dev_plan
from plan_io import build_godot_dev_handoff

_REPO = Path(__file__).resolve().parent.parent
_BRIEF = _REPO / "resources" / "test-brief-prison-walk.json"
_PROJECT = _REPO / "games" / "prison-demo"
_ASSEMBLE = _REPO / "plans" / "godot_test-brief-prison-walk.json"


class GodotDevHandoffTest(unittest.TestCase):
    def test_build_dev_plan(self) -> None:
        if not _PROJECT.is_dir():
            self.skipTest("games/prison-demo not present locally")
        plan = build_godot_dev_plan(
            _BRIEF,
            project_path=_PROJECT,
            assemble_handoff_path=_ASSEMBLE if _ASSEMBLE.is_file() else None,
        )
        self.assertIn("games", plan["project_path"])
        self.assertEqual(plan["language"], "csharp")
        self.assertTrue(plan["implementation_goals"])
        self.assertEqual(plan["product"]["title"], "Prison Break Arena")

    def test_dev_handoff_consumer_role(self) -> None:
        plan = {"project_path": "games/demo", "implementation_goals": []}
        handoff = build_godot_dev_handoff(plan)
        self.assertEqual(handoff["consumer_role"], "godot-developer")
        self.assertEqual(handoff["producer_role"], "orchestrator")


if __name__ == "__main__":
    unittest.main()
