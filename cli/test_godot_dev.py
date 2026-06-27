"""Tests for godot-developer handoff builder."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from assets_manifest import build_assets_manifest, save_assets_manifest
from godot_dev import BRIEF_CONTRACT_RULES, build_godot_dev_plan
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
        self.assertIn("authoritative_sources", plan)
        self.assertIn("animation_graphs", plan)
        self.assertEqual(len(plan["animation_graphs"]), 1)
        self.assertIn("runtime_bindings", plan)
        self.assertEqual(plan["contract_rules"], BRIEF_CONTRACT_RULES)

    def test_dev_handoff_consumer_role(self) -> None:
        plan = {"project_path": "games/demo", "implementation_goals": []}
        handoff = build_godot_dev_handoff(plan)
        self.assertEqual(handoff["consumer_role"], "godot-developer")
        self.assertEqual(handoff["producer_role"], "orchestrator")

    def test_runtime_bindings_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "output" / "asset-brief.example"
            out.mkdir(parents=True)
            manifest = build_assets_manifest(EXAMPLE_BRIEF, output_dir=out)
            manifest["assets"]["knight"]["runtime"] = {
                "sprite_frames": "assets/sprites/knight/knight.tres",
            }
            manifest_path = out / "assets-manifest.json"
            save_assets_manifest(manifest_path, manifest)

            repo = Path(__file__).resolve().parent.parent
            brief_in_repo = repo / "resources" / "asset-brief.example.json"
            plan = build_godot_dev_plan(
                brief_in_repo,
                project_path=Path(tmp) / "games" / "demo",
                assets_manifest_path=manifest_path,
            )
            knight = next(b for b in plan["runtime_bindings"] if b["asset"] == "knight")
            self.assertEqual(
                knight["runtime"]["sprite_frames"],
                "assets/sprites/knight/knight.tres",
            )
            self.assertIsNotNone(plan["authoritative_sources"]["assets_manifest"])


if __name__ == "__main__":
    unittest.main()
