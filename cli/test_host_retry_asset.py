"""Tests for host retry-asset single-asset pipeline repair."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from host.retry_asset import retry_asset
from pipeline_manifest import MANIFEST_VERSION, TASK_FAILED, TASK_PENDING, load_manifest, save_manifest
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
                "status": TASK_FAILED,
                "depends_on": [],
            },
            {
                "id": "foo.image.generate",
                "asset": "foo",
                "step": "image.generate",
                "status": "done",
                "depends_on": ["foo.prompt.craft"],
            },
        ],
    }


class HostRetryAssetTests(unittest.TestCase):
    def test_recraft_prompt_runs_cascade_and_pipeline_with_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            run_result = PipelineRunResult(
                complete=True,
                message="All tasks done.",
                summary={"done": True, "counts": {}},
            )

            with mock.patch("host.retry_asset.run_pipeline", return_value=run_result) as run_mock:
                result = retry_asset(
                    manifest_path,
                    asset="foo",
                    recraft_prompt=True,
                    jobs=2,
                )

            loaded = load_manifest(manifest_path)
            prompt = next(t for t in loaded["tasks"] if t["id"] == "foo.prompt.craft")
            image = next(t for t in loaded["tasks"] if t["id"] == "foo.image.generate")
            self.assertEqual(prompt["status"], TASK_PENDING)
            self.assertEqual(image["status"], TASK_PENDING)

            run_mock.assert_called_once()
            _, kwargs = run_mock.call_args
            self.assertTrue(kwargs.get("run_prompts"))
            self.assertEqual(kwargs.get("jobs"), 2)

            self.assertTrue(result["ok"])
            self.assertEqual(result["asset"], "foo")
            self.assertEqual(result["reset_task_id"], "foo.prompt.craft")
            self.assertTrue(result["recraft_prompt"])
            self.assertTrue(result["run_prompts"])
            self.assertEqual(result["run_exit_code"], 0)
            self.assertIn("foo.prompt.craft", result["reset_ids"])
            self.assertIn("foo.image.generate", result["reset_ids"])

    def test_auto_run_prompts_when_reset_is_prompt_craft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            run_result = PipelineRunResult(
                paused=True,
                message="Pipeline has failed tasks: foo.prompt.craft",
                summary={"done": False, "failed_ids": ["foo.prompt.craft"]},
            )

            with mock.patch("host.retry_asset.run_pipeline", return_value=run_result) as run_mock:
                result = retry_asset(manifest_path, asset="foo", recraft_prompt=False, jobs=4)

            self.assertTrue(run_mock.call_args.kwargs.get("run_prompts"))
            self.assertFalse(result["ok"])
            self.assertEqual(result["run_exit_code"], 2)

    def test_task_id_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            run_result = PipelineRunResult(complete=True, summary={"done": True})

            with mock.patch("host.retry_asset.run_pipeline", return_value=run_result):
                result = retry_asset(
                    manifest_path,
                    task_id="foo.prompt.craft",
                    recraft_prompt=False,
                    jobs=1,
                )

            self.assertEqual(result["reset_task_id"], "foo.prompt.craft")
            self.assertTrue(result["run_prompts"])

    def test_missing_asset_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            save_manifest(manifest_path, _sample_manifest())

            with self.assertRaises(ValueError):
                retry_asset(manifest_path, asset="missing")

    def test_safe_cli_allows_host_retry_asset(self) -> None:
        info = normalize_action(
            "python gamefactory.py host retry-asset "
            "--manifest ../pipeline/x.json --asset foo --recraft-prompt --json"
        )
        self.assertTrue(info["ok"])
        self.assertEqual(info["argv"][:2], ["host", "retry-asset"])


if __name__ == "__main__":
    unittest.main()
