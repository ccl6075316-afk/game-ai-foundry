"""Tests for deterministic pipeline runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline_manifest import (
    TASK_DONE,
    TASK_FAILED,
    TASK_PENDING,
    build_manifest,
    load_manifest,
    record_task,
    save_manifest,
)
from pipeline_runner import (
    extract_json_from_stdout,
    is_retryable_network_failure,
    outcome_from_process,
    reset_task_cascade,
    run_pipeline,
    run_task_subprocess,
)
from test_fixtures import EXAMPLE_BRIEF, MINIMAL_VIDEO_BRIEF, write_brief


class PipelineRunnerTest(unittest.TestCase):
    def test_extract_json_multiline(self) -> None:
        stdout = '{\n  "ok": false,\n  "next_action": "prompt_crafter_regenerate"\n}\n'
        parsed = extract_json_from_stdout(stdout)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["next_action"], "prompt_crafter_regenerate")

    def test_outcome_exit_2(self) -> None:
        stdout = json.dumps({"ok": False, "next_action": "prompt_crafter_regenerate"})
        outcome = outcome_from_process("a.image.generate", exit_code=2, stdout=stdout, stderr="")
        self.assertEqual(outcome.status, TASK_FAILED)
        self.assertTrue(outcome.should_pause)

    def test_network_failure_is_retryable(self) -> None:
        self.assertTrue(
            is_retryable_network_failure(
                1, "", "requests.exceptions.ConnectionError: Failed to establish"
            )
        )
        self.assertTrue(is_retryable_network_failure(124, "", "timeout"))
        self.assertTrue(is_retryable_network_failure(1, "", "HTTP 503 Service Unavailable"))
        self.assertFalse(
            is_retryable_network_failure(
                2, json.dumps({"next_action": "prompt_crafter_regenerate"}), ""
            )
        )
        self.assertFalse(is_retryable_network_failure(1, "", "Asset 'x' not found in brief"))

    def test_run_task_retries_network_then_succeeds(self) -> None:
        task = {"id": "x.image.generate", "command": "echo ok"}
        fail = outcome_from_process(
            "x.image.generate",
            exit_code=1,
            stdout="",
            stderr="ProxyError: Cannot connect to proxy",
        )
        ok = outcome_from_process("x.image.generate", exit_code=0, stdout="/tmp/a.png", stderr="")
        with mock.patch("pipeline_runner._run_task_once", side_effect=[fail, ok]) as once:
            with mock.patch("pipeline_runner.time.sleep") as sleep:
                outcome = run_task_subprocess(task, retries=3, retry_backoff=0.1)
        self.assertEqual(outcome.status, TASK_DONE)
        self.assertEqual(once.call_count, 2)
        sleep.assert_called_once()
        self.assertEqual(len(outcome.result.get("network_retries") or []), 1)

    def test_run_task_does_not_retry_validation(self) -> None:
        task = {"id": "x.image.generate", "command": "echo fail"}
        fail = outcome_from_process(
            "x.image.generate",
            exit_code=2,
            stdout=json.dumps({"ok": False, "next_action": "prompt_crafter_regenerate"}),
            stderr="",
        )
        with mock.patch("pipeline_runner._run_task_once", return_value=fail) as once:
            with mock.patch("pipeline_runner.time.sleep") as sleep:
                outcome = run_task_subprocess(task, retries=3, retry_backoff=0.1)
        self.assertEqual(outcome.status, TASK_FAILED)
        self.assertEqual(once.call_count, 1)
        sleep.assert_not_called()

    def test_reset_cascade(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        record_task(manifest, "knight.prompt.craft", status=TASK_DONE)
        reset_ids = reset_task_cascade(manifest, "knight.prompt.craft")
        self.assertIn("knight.image.generate", reset_ids)
        task = next(t for t in manifest["tasks"] if t["id"] == "knight.image.generate")
        self.assertEqual(task["status"], TASK_PENDING)

    def test_run_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "m.json"
            plans = Path(tmp) / "plans"
            plans.mkdir()
            out = Path(tmp) / "out"
            out.mkdir()
            manifest = build_manifest(
                EXAMPLE_BRIEF,
                plans_dir=plans,
                output_dir=out,
            )
            from pipeline_manifest import _CLI_DIR

            for task in manifest["tasks"]:
                if task["step"] == "prompt.craft":
                    plan_rel = (task.get("artifacts") or {}).get("plan")
                    if plan_rel:
                        plan_path = (_CLI_DIR / plan_rel).resolve()
                        plan_path.parent.mkdir(parents=True, exist_ok=True)
                        plan_path.write_text("{}", encoding="utf-8")
                        self.addCleanup(lambda p=plan_path: p.unlink(missing_ok=True))
                    task["status"] = TASK_DONE
            save_manifest(manifest_path, manifest)

            result = run_pipeline(manifest_path, dry_run=True, jobs=2)
            self.assertIn("would execute", result.message)

    def test_run_blocked_without_plans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "m.json"
            manifest = build_manifest(EXAMPLE_BRIEF)
            save_manifest(manifest_path, manifest)
            result = run_pipeline(manifest_path, dry_run=False, jobs=1)
            self.assertTrue(result.blocked)
            self.assertIn("Missing plan", result.message)

    def test_auto_skip_prompt_when_plan_exists(self) -> None:
        brief_path = write_brief(MINIMAL_VIDEO_BRIEF, prefix="runner-brief-")
        self.addCleanup(lambda: brief_path.unlink(missing_ok=True))
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "m.json"
            plans = Path(tmp) / "plans"
            plans.mkdir()
            (plans / "knight.json").write_text("{}", encoding="utf-8")
            (plans / "knight_walk.json").write_text("{}", encoding="utf-8")

            manifest = build_manifest(brief_path, plans_dir=plans, output_dir=Path(tmp) / "out")
            save_manifest(manifest_path, manifest)

            with mock.patch("pipeline_runner.run_task_subprocess") as run_mock:
                run_mock.return_value = outcome_from_process(
                    "knight.image.generate",
                    exit_code=0,
                    stdout="/tmp/x.png",
                    stderr="",
                )
                run_pipeline(manifest_path, jobs=1)
                called_ids = [call.args[0]["id"] for call in run_mock.call_args_list]
                self.assertNotIn("knight.prompt.craft", called_ids)

            loaded = load_manifest(manifest_path)
            prompt = next(t for t in loaded["tasks"] if t["id"] == "knight.prompt.craft")
            self.assertEqual(prompt["status"], TASK_DONE)


if __name__ == "__main__":
    unittest.main()
