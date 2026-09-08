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

    def test_classify_matte_missing_frames_as_missing_file(self) -> None:
        task = {
            "id": "pose_x.video.matte-frames",
            "step": "video.matte-frames",
            "asset_id": "pose_x",
            "result": {
                "exit_code": 1,
                "stderr": (
                    "Error: Batch matting had failures:\n"
                    "frame_0005.png: Cannot read ../projects/x/output/pose_x_frames/frame_0005.png\n"
                ),
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "missing_file")
        self.assertEqual(d["pm_fit"], "no")
        # Matte missing frames → resplit only; do not purge plan via craft reset.
        self.assertEqual(d["reset_task_id"], "pose_x.video.split-frames")
        self.assertTrue(any("pose_x.video.split-frames" in h for h in d["cli_hints"]))
        self.assertFalse(any("--run-prompts" in h for h in d["cli_hints"]))

    def test_classify_click_missing_input_dir_as_missing_file(self) -> None:
        task = {
            "id": "pose_x.video.matte-frames",
            "step": "video.matte-frames",
            "asset_id": "pose_x",
            "result": {
                "exit_code": 2,
                "stderr": (
                    "Error: Invalid value for '--input-dir': "
                    "Directory '../projects/x/output/pose_x_frames' does not exist."
                ),
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "missing_file")
        self.assertEqual(d["pm_fit"], "no")
        self.assertEqual(d["reset_task_id"], "pose_x.video.split-frames")

    def test_classify_split_missing_mp4_resets_generate(self) -> None:
        task = {
            "id": "pose_x.video.split-frames",
            "step": "video.split-frames",
            "asset_id": "pose_x",
            "result": {
                "exit_code": 1,
                "stderr": "Error: Input video ../output/pose_x.mp4 not found",
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "missing_file")
        self.assertEqual(d["reset_task_id"], "pose_x.video.generate")
        self.assertFalse(any("--run-prompts" in h for h in d["cli_hints"]))

    def test_classify_generate_missing_plan_resets_craft(self) -> None:
        task = {
            "id": "pose_x.video.generate",
            "step": "video.generate",
            "asset_id": "pose_x",
            "result": {
                "exit_code": 1,
                "stderr": "Error: Plan file ../plans/pose_x.json not found",
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "missing_file")
        self.assertEqual(d["reset_task_id"], "pose_x.prompt.craft")

    def test_classify_assemble_missing_handoff_regenerates(self) -> None:
        task = {
            "id": "brief.godot.assemble",
            "step": "godot.assemble",
            "result": {
                "exit_code": 2,
                "stderr": (
                    "Error: Invalid value for '--assemble-file': "
                    "Path '../projects/x/plans/godot_brief.json' does not exist."
                ),
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "missing_file")
        self.assertEqual(d["remediation"], "regenerate_assemble_handoff")
        self.assertEqual(d["reset_task_id"], "brief.godot.assemble")
        self.assertEqual(d["pm_fit"], "no")

    def test_classify_godot_assemble_exit2_not_validation(self) -> None:
        task = {
            "id": "brief.godot.assemble",
            "step": "godot.assemble",
            "result": {
                "exit_code": 2,
                "stderr": "Error: Godot assemble failed: missing sprites",
            },
        }
        d = classify_failed_task(task)
        self.assertNotEqual(d["kind"], "validation")

    def test_classify_stale_plan_role_mismatch(self) -> None:
        task = {
            "id": "pose_x.video.generate",
            "step": "video.generate",
            "asset_id": "pose_x",
            "depends_on": ["pose_x.prompt.craft", "char.image.generate"],
            "result": {
                "exit_code": 1,
                "stderr": "Error: Plan file ../plans/pose_x.json is not for video-generator",
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "stale_plan")
        self.assertEqual(d["pm_fit"], "yes")
        self.assertEqual(d["remediation"], "reset_and_recraft_prompt")
        self.assertTrue(any("pose_x.prompt.craft" in h for h in d["cli_hints"]))
        self.assertTrue(any("--run-prompts" in h for h in d["cli_hints"]))

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

    def test_classify_network_http_522_download(self) -> None:
        task = {
            "id": "bg_11c7f01383.image.generate",
            "step": "image.generate",
            "result": {
                "exit_code": 1,
                "stderr": (
                    "Error: Failed to download image from "
                    "https://files.anyroutes.cn/au9mebn5cq2o0hn/output/20260826/"
                    "144277/cf1bc15a-8257-4c3d-a45f-f3bf98ceb86a/"
                    "02fe5f4a-3865-4010-9153-54e6e8935eee.png: HTTP 522"
                ),
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "network")
        self.assertEqual(d["pm_fit"], "no")
        self.assertIn("522", d["summary"])

    def test_classify_prompt_llm_response_ended_prematurely_as_network(self) -> None:
        task = {
            "id": "pose_x.prompt.craft",
            "step": "prompt.craft",
            "result": {
                "exit_code": 1,
                "stderr": "Error: Prompt LLM request failed: Response ended prematurely",
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "network")
        self.assertEqual(d["pm_fit"], "no")
        self.assertEqual(d["owner"], "code")

    def test_classify_billing_insufficient_credits(self) -> None:
        task = {
            "id": "fish.image.generate",
            "step": "image.generate",
            "result": {
                "exit_code": 1,
                "stderr": (
                    "Error: Images API error (HTTP 402): Insufficient credits. "
                    "Add more using https://openrouter.ai/settings/credits"
                ),
            },
        }
        d = classify_failed_task(task)
        self.assertEqual(d["kind"], "billing")
        self.assertEqual(d["pm_fit"], "no")
        self.assertEqual(d["owner"], "user")
        self.assertIn("402", d["summary"])

    def test_pm_advice_all_billing(self) -> None:
        from pipeline_heal import _aggregate_pm_advice

        advice = _aggregate_pm_advice(
            [
                {"task_id": "a", "kind": "billing", "pm_fit": "no"},
                {"task_id": "b", "kind": "billing", "pm_fit": "no"},
            ]
        )
        self.assertFalse(advice["pm_suitable"])
        self.assertIn("余额", advice["pm_advice_short"])

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

    def test_diagnose_and_heal_persists_failure_log_before_reset(self) -> None:
        """Heal clears failed→pending; failure-log.jsonl must keep the reason."""
        import json

        from pipeline_heal import diagnose_and_heal_file, failure_log_path
        from pipeline_manifest import MANIFEST_VERSION, TASK_PENDING, load_manifest, save_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            save_manifest(
                manifest_path,
                {
                    "manifest_version": MANIFEST_VERSION,
                    "tasks": [
                        {
                            "id": "bg_x.image.generate",
                            "step": "image.generate",
                            "status": "failed",
                            "result": {
                                "exit_code": 1,
                                "stderr": "ConnectionError: Failed to establish a new connection",
                            },
                        }
                    ],
                },
            )
            report = diagnose_and_heal_file(manifest_path, apply=True)
            self.assertTrue(report.get("applied"))
            self.assertIn("bg_x.image.generate", report.get("healed") or [])
            after = load_manifest(manifest_path)
            self.assertEqual(after["tasks"][0]["status"], TASK_PENDING)
            log_path = failure_log_path(manifest_path)
            self.assertTrue(log_path.is_file(), f"missing {log_path}")
            rows = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertGreaterEqual(len(rows), 1)
            last = rows[-1]
            self.assertEqual(last.get("event"), "pre_heal")
            items = last.get("items") or []
            self.assertEqual(items[0].get("task_id"), "bg_x.image.generate")
            self.assertEqual(items[0].get("kind"), "network")
            blob = str(items[0].get("summary") or "") + str(items[0].get("stderr") or "")
            self.assertIn("ConnectionError", blob)
            self.assertEqual(report.get("failure_log"), str(log_path))


if __name__ == "__main__":
    unittest.main()
