"""Tests for host run-assets batch pipeline repair with auto-fix loop."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from host.run_assets import run_assets
from pipeline_manifest import MANIFEST_VERSION, save_manifest
from pipeline_runner import PipelineRunResult
from safe_cli import normalize_action


def _sample_manifest() -> dict:
    return {
        "manifest_version": MANIFEST_VERSION,
        "brief": "test-brief.json",
        "tasks": [
            {
                "id": "foo.prompt.craft",
                "asset": "foo",
                "step": "prompt.craft",
                "status": "failed",
                "depends_on": [],
            },
        ],
    }


def _validation_diagnosis(*, task_id: str = "foo.prompt.craft") -> dict:
    manifest_cli_rel = "../pipeline/test.json"
    diagnosis = {
        "failed_count": 1,
        "items": [
            {
                "task_id": task_id,
                "kind": "validation",
                "owner": "hermes",
                "pm_fit": "yes",
            }
        ],
        "needs_hermes": [
            {
                "task_id": task_id,
                "kind": "validation",
                "owner": "hermes",
                "cli_hints": [
                    f"pipeline reset --manifest {manifest_cli_rel} --task-id {task_id} --cascade",
                ],
            }
        ],
        "manifest_cli_rel": manifest_cli_rel,
        "fix_commands": [
            f"pipeline reset --manifest {manifest_cli_rel} --task-id {task_id} --cascade",
            f"pipeline run --manifest {manifest_cli_rel} --jobs 4 --run-prompts",
        ],
        "auto_fix_without_agent": True,
    }
    return diagnosis


def _heal_report(diagnosis: dict) -> dict:
    return {
        "applied": True,
        "healed": [],
        "diagnose": diagnosis,
        "fix_commands": diagnosis["fix_commands"],
        "auto_fix_without_agent": True,
        "manifest_cli_rel": diagnosis["manifest_cli_rel"],
    }


class HostRunAssetsTests(unittest.TestCase):
    def test_auto_fix_validation_then_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            incomplete = PipelineRunResult(
                paused=True,
                message="Pipeline has failed tasks: foo.prompt.craft",
                summary={"done": False, "failed_ids": ["foo.prompt.craft"]},
            )
            complete = PipelineRunResult(
                complete=True,
                message="All tasks done.",
                summary={"done": True},
            )
            diagnosis = _validation_diagnosis()
            heal_report = _heal_report(diagnosis)

            with mock.patch("host.run_assets.run_pipeline", side_effect=[incomplete, complete]) as run_mock:
                with mock.patch(
                    "host.run_assets.diagnose_and_heal_file",
                    return_value=heal_report,
                ) as diagnose_mock:
                    with mock.patch(
                        "host.run_assets._execute_fix_commands",
                        return_value={"executed": [{"action": "reset"}], "run_result": None},
                    ) as fix_mock:
                        result = run_assets(
                            manifest_path,
                            jobs=2,
                            run_prompts=False,
                            auto_fix=True,
                            max_repair_rounds=2,
                        )

            self.assertTrue(result["ok"])
            self.assertEqual(result["stopped_reason"], "complete")
            self.assertGreaterEqual(len(result["rounds"]), 2)
            diagnose_mock.assert_called_once()
            fix_mock.assert_called_once()
            self.assertEqual(run_mock.call_count, 2)
            _, second_kwargs = run_mock.call_args_list[1]
            self.assertTrue(second_kwargs.get("run_prompts"))

    def test_same_failure_stops_at_max_rounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            incomplete = PipelineRunResult(
                paused=True,
                message="Pipeline has failed tasks: foo.prompt.craft",
                summary={"done": False, "failed_ids": ["foo.prompt.craft"]},
            )
            diagnosis = _validation_diagnosis()
            heal_report = _heal_report(diagnosis)

            with mock.patch(
                "host.run_assets.run_pipeline",
                return_value=incomplete,
            ) as run_mock:
                with mock.patch(
                    "host.run_assets.diagnose_and_heal_file",
                    return_value=heal_report,
                ) as diagnose_mock:
                    with mock.patch(
                        "host.run_assets._execute_fix_commands",
                        return_value={"executed": [{"action": "reset"}], "run_result": None},
                    ) as fix_mock:
                        result = run_assets(
                            manifest_path,
                            auto_fix=True,
                            max_repair_rounds=2,
                        )

            self.assertFalse(result["ok"])
            self.assertEqual(result["stopped_reason"], "max_rounds")
            self.assertEqual(diagnose_mock.call_count, 2)
            self.assertEqual(fix_mock.call_count, 2)
            self.assertEqual(run_mock.call_count, 3)
            self.assertIsNotNone(result.get("diagnosis"))
            self.assertEqual(
                (result.get("diagnosis") or {}).get("failed_count"),
                1,
            )

    def test_code_heal_cleared_failures_then_rerun(self) -> None:
        """Network/code heal resets tasks; must run_pipeline again, not needs_agent."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            incomplete = PipelineRunResult(
                paused=True,
                message="Pipeline has failed tasks: foo.image.generate",
                summary={"done": False, "failed_ids": ["foo.image.generate"]},
            )
            complete = PipelineRunResult(
                complete=True,
                message="All tasks done.",
                summary={"done": True},
            )
            post_clean = {
                "failed_count": 0,
                "items": [],
                "needs_hermes": [],
                "manifest_cli_rel": "../pipeline/test.json",
                "fix_commands": [],
                "auto_fix_without_agent": False,
                "summary": {"done": False, "pending": 1},
            }
            heal_report = {
                "applied": True,
                "healed": ["foo.image.generate"],
                "diagnose": post_clean,
                "fix_commands": [],
                "auto_fix_without_agent": False,
                "manifest_cli_rel": "../pipeline/test.json",
            }

            with mock.patch(
                "host.run_assets.run_pipeline",
                side_effect=[incomplete, complete],
            ) as run_mock:
                with mock.patch(
                    "host.run_assets.diagnose_and_heal_file",
                    return_value=heal_report,
                ) as diagnose_mock:
                    with mock.patch("host.run_assets._execute_fix_commands") as fix_mock:
                        result = run_assets(
                            manifest_path,
                            jobs=2,
                            run_prompts=False,
                            auto_fix=True,
                            max_repair_rounds=2,
                        )

            self.assertTrue(result["ok"])
            self.assertEqual(result["stopped_reason"], "complete")
            self.assertEqual(result["repair_rounds"], 1)
            diagnose_mock.assert_called_once()
            fix_mock.assert_not_called()
            self.assertEqual(run_mock.call_count, 2)

    def test_unknown_diagnosis_needs_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            incomplete = PipelineRunResult(
                blocked=True,
                message="Unknown failure",
                summary={"done": False},
            )
            diagnosis = {
                "failed_count": 1,
                "items": [{"task_id": "foo.prompt.craft", "kind": "unknown", "owner": "hermes"}],
                "needs_hermes": [{"task_id": "foo.prompt.craft", "kind": "unknown", "owner": "hermes"}],
                "manifest_cli_rel": "../pipeline/test.json",
                "fix_commands": [],
                "auto_fix_without_agent": False,
            }
            heal_report = {
                "applied": True,
                "diagnose": diagnosis,
                "fix_commands": [],
                "auto_fix_without_agent": False,
            }

            with mock.patch("host.run_assets.run_pipeline", return_value=incomplete) as run_mock:
                with mock.patch(
                    "host.run_assets.diagnose_and_heal_file",
                    return_value=heal_report,
                ) as diagnose_mock:
                    with mock.patch("host.run_assets._execute_fix_commands") as fix_mock:
                        result = run_assets(manifest_path, auto_fix=True)

            self.assertFalse(result["ok"])
            self.assertEqual(result["stopped_reason"], "needs_agent")
            diagnose_mock.assert_called_once()
            fix_mock.assert_not_called()
            self.assertEqual(run_mock.call_count, 1)

    def test_safe_cli_allows_host_run_assets(self) -> None:
        info = normalize_action(
            "python gamefactory.py host run-assets "
            "--manifest ../pipeline/x.json --auto-fix --run-prompts --json"
        )
        self.assertTrue(info["ok"])
        self.assertEqual(info["argv"][:2], ["host", "run-assets"])


if __name__ == "__main__":
    unittest.main()
