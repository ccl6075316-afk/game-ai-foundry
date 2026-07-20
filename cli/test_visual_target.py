"""Tests for visual target candidate generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from visual_target import (
    apply_visual_target_pick,
    build_candidate_prompts,
    build_visual_target_plan,
    default_output_dir,
    generate_visual_targets,
    load_visual_target_manifest,
)


def _write_example_brief(dir_path: Path) -> Path:
    brief = {
        "project": {
            "title": "Dino Scavenger",
            "description": "Side-scrolling scavenger with raptor companion.",
            "art_direction": "Pixel art, warm desert palette.",
            "genre": "side_scroller",
            "gameplay_loop": "Collect scraps while avoiding hazards.",
            "session_goal": "Fill the scrap meter before sunset.",
            "viewport": {"width": 1280, "height": 720},
        },
        "assets": [
            {
                "id": "player",
                "type": "character",
                "usage": "player_idle",
                "generate_method": "image",
            }
        ],
    }
    path = dir_path / "dino-brief.json"
    path.write_text(json.dumps(brief), encoding="utf-8")
    return path


class TestVisualTarget(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.example_brief = _write_example_brief(self.tmp_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_build_candidate_prompts_count(self) -> None:
        prompts = build_candidate_prompts(self.example_brief, count=3)
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0]["id"], "a")
        text = prompts[0]["prompt"].lower()
        self.assertTrue("screenshot" in text or "framebuffer" in text)
        self.assertIn("use case:", text)
        self.assertTrue(
            "art direction" in text or "style lock" in text or "pixel" in text
        )

    def test_default_output_dir(self) -> None:
        out = default_output_dir(self.example_brief)
        self.assertIn("dino-scavenger", str(out))
        self.assertEqual(out.name, "visual-target")

    def test_build_visual_target_plan_scaffold(self) -> None:
        plan = build_visual_target_plan(
            self.example_brief,
            {"id": "a", "label": "opening_moment", "focus": "Opening scene."},
            craft=False,
            config={},
        )
        self.assertEqual(plan["kind"], "visual_target")
        self.assertEqual(plan["prompt_source"], "scaffold")
        self.assertTrue(plan["validation"]["skip_validate"] is True)
        self.assertIn("screenshot", plan["prompt"].lower())
        self.assertIn("Use case:", plan["prompt"])

    def test_generate_dry_run_writes_handoffs(self) -> None:
        out = self.tmp_path / "visual-target"
        plans = self.tmp_path / "plans"
        manifest = generate_visual_targets(
            self.example_brief,
            out,
            count=2,
            config={},
            dry_run=True,
            craft=False,
            plans_dir=plans,
        )
        self.assertEqual(len(manifest["candidates"]), 2)
        self.assertFalse(manifest["craft"])
        for c in manifest["candidates"]:
            self.assertTrue(Path(c["handoff_path"]).is_file())
            handoff = json.loads(Path(c["handoff_path"]).read_text(encoding="utf-8"))
            self.assertEqual(handoff["consumer_role"], "image-generator")
            self.assertEqual(handoff["plan"]["kind"], "visual_target")

    def test_image_size_from_handoff(self) -> None:
        from plan_io import image_size_from_handoff

        handoff = {"plan": {"image_size": "1280x720", "asset_type": "visual_target"}}
        self.assertEqual(image_size_from_handoff(handoff), "1280x720")
        self.assertIsNone(image_size_from_handoff({"plan": {}}))

    def test_apply_pick_updates_brief(self) -> None:
        out_dir = self.tmp_path / "visual-target"
        out_dir.mkdir()
        fake_png = out_dir / "candidate_b.png"
        fake_png.write_bytes(b"\x89PNG\r\n")

        manifest = {
            "viewport_size": "1280x720",
            "candidates": [
                {"id": "a", "label": "opening", "path": str(out_dir / "candidate_a.png")},
                {"id": "b", "label": "action", "path": str(fake_png), "prompt_summary": "action"},
            ],
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = apply_visual_target_pick(self.example_brief, "b", manifest_path)
        self.assertEqual(result["selected_id"], "b")

        data = json.loads(self.example_brief.read_text(encoding="utf-8"))
        self.assertTrue(data["project"]["visual_reference"])
        self.assertEqual(data["project"]["visual_target"]["selected_id"], "b")
        self.assertEqual(data["project"]["visual_target"]["image_size"], "1280x720")

        self.assertEqual(len(data["project"]["visual_target"]["candidates"]), 2)

        updated = load_visual_target_manifest(manifest_path)
        self.assertEqual(updated["selected_id"], "b")
        self.assertTrue((out_dir / "selected.png").is_file())


if __name__ == "__main__":
    unittest.main()
