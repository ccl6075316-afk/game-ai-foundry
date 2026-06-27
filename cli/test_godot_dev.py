"""Tests for godot-developer handoff builder."""

from __future__ import annotations

import unittest
from pathlib import Path

from godot_dev import build_godot_dev_plan
from plan_io import build_godot_dev_handoff

_REPO = Path(__file__).resolve().parent.parent
_BRIEF = _REPO / "resources" / "test-brief-dino-idle.json"
_PROJECT = _REPO / "games" / "dino-test"


class GodotDevHandoffTest(unittest.TestCase):
    def test_build_dev_plan(self) -> None:
        plan = build_godot_dev_plan(
            _BRIEF,
            project_path=_PROJECT,
            assemble_handoff_path=None,
        )
        self.assertIn("games", plan["project_path"])
        self.assertEqual(plan["language"], "csharp")
        self.assertTrue(plan["implementation_goals"])
        self.assertEqual(plan["product"]["title"], "Wasteland Survivors")

    def test_dev_handoff_consumer_role(self) -> None:
        plan = {"project_path": "games/demo", "implementation_goals": []}
        handoff = build_godot_dev_handoff(plan)
        self.assertEqual(handoff["consumer_role"], "godot-developer")
        self.assertEqual(handoff["producer_role"], "orchestrator")


if __name__ == "__main__":
    unittest.main()
