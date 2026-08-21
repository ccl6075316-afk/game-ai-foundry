"""Tests for pipeline failure diagnose / heal."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline_heal import classify_failed_task, diagnose_manifest, heal_manifest
from pipeline_manifest import build_manifest, record_task, tasks_list
from prompt_craft import _CJK_BRIEF_BLOCK_MSG
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

    def test_classify_cjk_prompt_craft_as_validation(self) -> None:
        task = {
            "id": "hero.prompt.craft",
            "step": "prompt.craft",
            "result": {
                "exit_code": 1,
                "stderr": _CJK_BRIEF_BLOCK_MSG,
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "validation")
        self.assertEqual(d["remediation"], "reset_and_recraft_prompt")
        self.assertEqual(d["owner"], "hermes")
        self.assertEqual(d["pm_fit"], "yes")
        self.assertTrue(any("--run-prompts" in h for h in d["cli_hints"]))

    def test_classify_typeerror_surfaces_exception_line(self) -> None:
        task = {
            "id": "kit.prompt.craft",
            "step": "prompt.craft",
            "result": {
                "exit_code": 1,
                "stderr": (
                    "\x1b[31mTraceback\x1b[0m (most recent call last):\n"
                    "  File click/core.py, line 1, in invoke\n"
                    "TypeError: PromptPlan.__init__() got an unexpected "
                    "keyword argument 'expand_items'\n"
                ),
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "unknown")
        self.assertIn("expand_items", d["summary"])
        self.assertIn("TypeError", d["summary"])

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

    def test_build_fix_command_chain_validation(self) -> None:
        from pipeline_heal import build_fix_command_chain

        diagnosis = {
            "needs_hermes": [
                {
                    "task_id": "hero.image.generate",
                    "kind": "validation",
                    "cli_hints": [
                        "pipeline reset --task-id hero.image.generate --cascade",
                        "pipeline run --run-prompts --jobs 4",
                    ],
                },
                {
                    "task_id": "icon.image.generate",
                    "kind": "validation",
                    "cli_hints": [
                        "pipeline reset --task-id icon.image.generate --cascade",
                    ],
                },
            ],
        }
        cmds = build_fix_command_chain("../pipeline/test.json", diagnosis)
        self.assertEqual(len(cmds), 3)
        self.assertTrue(all("--manifest ../pipeline/test.json" in c for c in cmds if "pipeline" in c))
        self.assertEqual(sum(1 for c in cmds if c.startswith("pipeline run")), 1)
        self.assertIn("--run-prompts", cmds[-1])

    def test_auto_fix_without_agent(self) -> None:
        from pipeline_heal import can_auto_fix_without_agent

        yes = {
            "manifest_cli_rel": "../pipeline/x.json",
            "needs_hermes": [{"kind": "validation", "cli_hints": ["pipeline reset --task-id a --cascade"]}],
        }
        self.assertTrue(can_auto_fix_without_agent(yes))
        no = {
            "manifest_cli_rel": "../pipeline/x.json",
            "needs_hermes": [{"kind": "unknown", "cli_hints": ["pipeline reset --task-id a --cascade"]}],
        }
        self.assertFalse(can_auto_fix_without_agent(no))

    def test_build_fix_command_chain_mixed_validation_config_size(self) -> None:
        from pipeline_heal import build_fix_command_chain

        diagnosis = {
            "needs_hermes": [
                {
                    "kind": "validation",
                    "cli_hints": ["pipeline reset --task-id hero.image.generate --cascade"],
                },
                {
                    "kind": "config_size",
                    "cli_hints": [
                        "config set --key image.constraints.size_multiple --value 16",
                        "pipeline reset --task-id pitch.image.generate --cascade",
                        "pipeline run --jobs 4",
                    ],
                },
            ],
        }
        cmds = build_fix_command_chain("../pipeline/test.json", diagnosis)
        run_cmds = [c for c in cmds if c.startswith("pipeline run")]
        self.assertEqual(len(run_cmds), 1)
        self.assertIn("--run-prompts", run_cmds[0])
        self.assertIn("--manifest ../pipeline/test.json", run_cmds[0])


if __name__ == "__main__":
    unittest.main()
