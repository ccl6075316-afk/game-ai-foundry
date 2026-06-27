"""Tests for godot-developer handoff builder."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from godot_dev import build_godot_dev_plan
from plan_io import build_godot_dev_handoff
from test_fixtures import EXAMPLE_BRIEF


class GodotDevHandoffTest(unittest.TestCase):
    def test_build_dev_plan(self) -> None:
        plan = build_godot_dev_plan(
            EXAMPLE_BRIEF,
            project_path=Path(tempfile.gettempdir()) / "gf-test-game",
            assemble_handoff_path=None,
        )
        self.assertIn("gf-test-game", plan["project_path"].replace("\\", "/"))
        self.assertEqual(plan["language"], "csharp")
        self.assertTrue(plan["implementation_goals"])
        self.assertEqual(plan["product"]["title"], "Forest Platformer")

    def test_dev_handoff_consumer_role(self) -> None:
        plan = {"project_path": "games/demo", "implementation_goals": []}
        handoff = build_godot_dev_handoff(plan)
        self.assertEqual(handoff["consumer_role"], "godot-developer")
        self.assertEqual(handoff["producer_role"], "orchestrator")


if __name__ == "__main__":
    unittest.main()
