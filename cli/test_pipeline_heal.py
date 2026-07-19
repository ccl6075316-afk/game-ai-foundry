"""Tests for pipeline failure diagnose / heal."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline_heal import classify_failed_task, diagnose_manifest, heal_manifest
from pipeline_manifest import build_manifest, record_task, tasks_list
from test_fixtures import EXAMPLE_BRIEF


class PipelineHealTests(unittest.TestCase):
    def test_classify_api_size(self) -> None:
        task = {
            "id": "pitch.image.generate",
            "step": "image.generate",
            "result": {
                "exit_code": 1,
                "stderr": "Images API error (HTTP 400): Invalid size '1920x1080'. "
                "Width and height must both be divisible by 16.",
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["owner"], "hermes")
        self.assertEqual(d["kind"], "config_size")
        self.assertEqual(d["pm_fit"], "yes")
        self.assertEqual(d["size_multiple"], 16)
        self.assertTrue(
            any("size_multiple" in h for h in d["cli_hints"]),
        )

    def test_classify_validation_needs_hermes(self) -> None:
        task = {
            "id": "hero.image.generate",
            "step": "image.generate",
            "result": {
                "exit_code": 2,
                "stdout_tail": '{"ok": false, "next_action": "prompt_crafter_regenerate"}',
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["owner"], "hermes")
        self.assertEqual(d["kind"], "validation")
        self.assertEqual(d["pm_fit"], "yes")

    def test_pm_advice_for_validation(self) -> None:
        from pipeline_heal import _aggregate_pm_advice

        advice = _aggregate_pm_advice(
            [
                {
                    "task_id": "a",
                    "kind": "validation",
                    "pm_fit": "yes",
                    "pm_tip": "x",
                }
            ]
        )
        self.assertTrue(advice["pm_suitable"])
        self.assertEqual(advice["pm_fit"], "yes")
        self.assertIn("适合", advice["pm_advice_short"])

    def test_heal_resets_code_owned(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        record_task(
            manifest,
            "knight.image.generate",
            status="failed",
            result={
                "exit_code": 1,
                "stderr": "ConnectionError: Failed to establish a new connection",
            },
        )
        report = heal_manifest(manifest, only_code=True)
        self.assertIn("knight.image.generate", report["healed"])
        task = next(t for t in tasks_list(manifest) if t["id"] == "knight.image.generate")
        self.assertEqual(task["status"], "pending")


if __name__ == "__main__":
    unittest.main()
