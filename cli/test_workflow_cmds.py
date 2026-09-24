"""Tests for deterministic external-agent workflow commands."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

import gamefactory
from gamefactory import cli as root_cli
from project_paths import default_paths_for_brief
from test_fixtures import EXAMPLE_BRIEF
from workflow.contract import (
    FAILURE_KINDS,
    NEXT_ACTIONS,
    RESPONSE_FIELDS,
    STAGES,
    STATUSES,
    build_response,
    make_failure,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    snapshot: dict[str, tuple[bytes, int]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        snapshot[str(path.relative_to(root))] = (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
    return snapshot


def _payload(result: object) -> dict:
    assert result is not None
    output = getattr(result, "output", "")
    return json.loads(output)


class WorkflowCmdTests(unittest.TestCase):
    def setUp(self) -> None:
        projects_root = REPO_ROOT / "projects"
        projects_root.mkdir(exist_ok=True)
        self._temp = tempfile.TemporaryDirectory(prefix="workflow-cmds-", dir=projects_root)
        self.root = Path(self._temp.name)
        self.brief = self.root / "brief.json"
        brief_data = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))
        brief_data.get("project", {}).pop("visual_reference", None)
        self.brief.write_text(json.dumps(brief_data, ensure_ascii=False), encoding="utf-8")
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            json.dumps({"host": {"model": "deepseek-chat"}}),
            encoding="utf-8",
        )
        self.paths = default_paths_for_brief(self.brief)
        self.manifest = Path(self.paths["manifest"])
        self.production = Path(self.paths["production"])
        self.progress = Path(self.paths["progress"])
        init = self._invoke(
            "workflow",
            "init",
            "--brief",
            str(self.brief),
            "--json",
        )
        self.assertEqual(init.exit_code, 0, init.output)
        self.init_payload = _payload(init)
        self._assert_contract(self.init_payload)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _invoke(self, *args: str):
        with patch("gamefactory.CONFIG_PATH", self.config_path):
            return CliRunner().invoke(root_cli, list(args))

    def _assert_contract(self, payload: dict) -> None:
        self.assertEqual(set(payload), set(RESPONSE_FIELDS))
        self.assertEqual(payload["schema_version"], 1)
        self.assertIsInstance(payload["ok"], bool)
        self.assertIsInstance(payload["command"], str)
        self.assertIn(payload["stage"], STAGES)
        self.assertIn(payload["status"], STATUSES)
        self.assertIn(payload["next_action"], NEXT_ACTIONS)
        self.assertIsInstance(payload["inputs"], dict)
        self.assertIsInstance(payload["outputs"], list)
        self.assertIsInstance(payload["summary"], dict)
        self.assertIsInstance(payload["failures"], list)
        for failure in payload["failures"]:
            self.assertIsInstance(failure, dict)
            self.assertIn("code", failure)
            self.assertIn("kind", failure)
            self.assertIn(failure["kind"], FAILURE_KINDS)
            self.assertIn("message", failure)

    def test_contract_rejects_illegal_enums_and_missing_failure_kind(self) -> None:
        base = {
            "command": "status",
            "ok": True,
            "stage": "assets",
            "status": "pending",
            "next_action": "run",
        }
        for field, value in (
            ("status", "error"),
            ("stage", "brief"),
            ("next_action", "review"),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_response(**{**base, field: value})
        with self.assertRaises(ValueError):
            build_response(
                **base,
                failures=[{"code": "brief_invalid", "message": "bad"}],
            )
        with self.assertRaises(ValueError):
            build_response(
                **base,
                failures=[
                    {
                        "code": "brief_invalid",
                        "kind": "unknown",
                        "message": "bad",
                    }
                ],
            )
        self.assertEqual(make_failure("brief_invalid", "bad")["kind"], "validation")
        self.assertEqual(make_failure("unsupported_stage", "bad")["kind"], "config")
        self.assertEqual(make_failure("custom", "bad")["kind"], "unknown")

    def test_six_commands_have_legal_help_and_json_outputs(self) -> None:
        for command in ("context", "init", "run", "resume", "status", "validate"):
            with self.subTest(command=command):
                result = self._invoke("workflow", command, "--help")
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("--json", result.output)
                self.assertIn("--help", result.output)

        unsupported = self._invoke(
            "workflow",
            "run",
            "--manifest",
            str(self.manifest),
            "--stage",
            "audio",
            "--json",
        )
        self.assertEqual(unsupported.exit_code, 1, unsupported.output)
        payload = _payload(unsupported)
        self._assert_contract(payload)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["stage"], "assets")
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["next_action"], "fix_input")
        self.assertEqual(payload["failures"][0]["code"], "unsupported_stage")
        self.assertEqual(payload["failures"][0]["kind"], "config")

        failure_commands = (
            ("context", "--brief", str(self.root / "missing.json")),
            (
                "resume",
                "--manifest",
                str(self.root / "missing.json"),
                "--task-id",
                "task",
            ),
            (
                "status",
                "--manifest",
                str(self.root / "missing.json"),
            ),
            (
                "validate",
                "--brief",
                str(self.brief),
                "--production",
                str(self.root / "missing-production.json"),
            ),
        )
        for command in failure_commands:
            with self.subTest(failure_command=command[0]):
                result = self._invoke("workflow", *command, "--json")
                self.assertEqual(result.exit_code, 1, result.output)
                failure_payload = _payload(result)
                self._assert_contract(failure_payload)
                self.assertFalse(failure_payload["ok"])
                self.assertEqual(failure_payload["status"], "blocked")
                self.assertEqual(failure_payload["next_action"], "fix_input")
                self.assertEqual(failure_payload["failures"][0]["kind"], "validation")
                expected_stage = (
                    "assets" if command[0] in {"resume", "status"} else "design"
                )
                self.assertEqual(failure_payload["stage"], expected_stage)

    def test_real_root_context_status_validate_write_neither_tree_nor_config(self) -> None:
        config_before = (
            self.config_path.read_bytes(),
            self.config_path.stat().st_mtime_ns,
        )
        before = _snapshot(self.root)
        commands = (
            ("context", "--brief", str(self.brief)),
            ("status", "--manifest", str(self.manifest)),
            (
                "validate",
                "--brief",
                str(self.brief),
                "--production",
                str(self.production),
                "--manifest",
                str(self.manifest),
            ),
        )
        expected_results = {
            "context": ("pending", "run"),
            "status": ("pending", "run"),
            "validate": ("pending", "run"),
        }
        for command in commands:
            with self.subTest(command=command[0]):
                result = self._invoke("workflow", *command, "--json")
                self.assertEqual(result.exit_code, 0, result.output)
                payload = _payload(result)
                self._assert_contract(payload)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["command"], command[0])
                expected_stage = (
                    "assets" if command[0] == "status" else "design"
                )
                self.assertEqual(payload["stage"], expected_stage)
                self.assertEqual(
                    (payload["status"], payload["next_action"]),
                    expected_results[command[0]],
                )

        self.assertEqual(_snapshot(self.root), before)
        self.assertEqual(
            (self.config_path.read_bytes(), self.config_path.stat().st_mtime_ns),
            config_before,
        )
        with patch("gamefactory.CONFIG_PATH", self.config_path):
            migrated = gamefactory.load_config()
        self.assertEqual(migrated["host"]["model"], "deepseek-v4-flash")
        self.assertEqual(
            (self.config_path.read_bytes(), self.config_path.stat().st_mtime_ns),
            config_before,
        )

    def test_missing_production_is_ok_and_directs_read_only_commands_to_derive(self) -> None:
        self.production.unlink()
        before = _snapshot(self.root)
        context = self._invoke(
            "workflow",
            "context",
            "--brief",
            str(self.brief),
            "--json",
        )
        self.assertEqual(context.exit_code, 0, context.output)
        context_payload = _payload(context)
        self._assert_contract(context_payload)
        self.assertTrue(context_payload["ok"])
        self.assertEqual(
            (context_payload["status"], context_payload["next_action"]),
            ("blocked", "derive_production"),
        )

        validate = self._invoke(
            "workflow",
            "validate",
            "--brief",
            str(self.brief),
            "--json",
        )
        self.assertEqual(validate.exit_code, 0, validate.output)
        validate_payload = _payload(validate)
        self._assert_contract(validate_payload)
        self.assertTrue(validate_payload["ok"])
        self.assertEqual(
            (validate_payload["status"], validate_payload["next_action"]),
            ("done", "derive_production"),
        )
        self.assertEqual(_snapshot(self.root), before)

    def test_root_help_has_no_legacy_context_double_entry(self) -> None:
        result = self._invoke("--help")
        self.assertEqual(result.exit_code, 0, result.output)
        command_lines = [
            line.strip().split()[0]
            for line in result.output.splitlines()
            if line.startswith("  ") and line.strip()
        ]
        self.assertNotIn("context", command_lines)
        self.assertIn("workflow", command_lines)
        workflow_help = self._invoke("workflow", "--help")
        self.assertIn("context", workflow_help.output)

    def test_init_stage_is_production_and_repeats_without_clearing_progress(self) -> None:
        self.assertEqual(self.init_payload["stage"], "production")
        progress_before = (
            self.progress.read_bytes(),
            self.progress.stat().st_mtime_ns,
        )
        manifest_before = (
            self.manifest.read_bytes(),
            self.manifest.stat().st_mtime_ns,
        )
        result = self._invoke(
            "workflow",
            "init",
            "--brief",
            str(self.brief),
            "--manifest",
            str(self.manifest),
            "--json",
        )
        self.assertEqual(result.exit_code, 0, result.output)
        payload = _payload(result)
        self._assert_contract(payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["created"], [])
        self.assertEqual(
            (self.progress.read_bytes(), self.progress.stat().st_mtime_ns),
            progress_before,
        )
        self.assertEqual(
            (self.manifest.read_bytes(), self.manifest.stat().st_mtime_ns),
            manifest_before,
        )
        progress = json.loads(self.progress.read_text(encoding="utf-8"))
        self.assertEqual(progress["phases"]["pipeline_run"]["status"], "pending")

    def test_init_manifest_write_failure_rolls_back_new_production(self) -> None:
        progress_before = (
            self.progress.read_bytes(),
            self.progress.stat().st_mtime_ns,
        )
        self.production.unlink()
        self.manifest.unlink()
        with patch(
            "workflow_cmds.save_manifest",
            side_effect=OSError("manifest write failed"),
        ):
            result = self._invoke(
                "workflow",
                "init",
                "--brief",
                str(self.brief),
                "--manifest",
                str(self.manifest),
                "--json",
            )
        self.assertEqual(result.exit_code, 1, result.output)
        payload = _payload(result)
        self._assert_contract(payload)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["next_action"], "fix_input")
        self.assertEqual(payload["summary"]["created"], [])
        self.assertIsInstance(payload["summary"]["outputs"], list)
        self.assertEqual(payload["outputs"], payload["summary"]["outputs"])
        self.assertFalse(self.production.exists())
        self.assertFalse(self.manifest.exists())
        self.assertEqual(
            (self.progress.read_bytes(), self.progress.stat().st_mtime_ns),
            progress_before,
        )

    def test_init_progress_write_failure_preserves_existing_state(self) -> None:
        production_before = (
            self.production.read_bytes(),
            self.production.stat().st_mtime_ns,
        )
        manifest_before = (
            self.manifest.read_bytes(),
            self.manifest.stat().st_mtime_ns,
        )
        self.progress.unlink()
        with patch(
            "workflow_cmds.save_progress",
            side_effect=OSError("progress write failed"),
        ):
            result = self._invoke(
                "workflow",
                "init",
                "--brief",
                str(self.brief),
                "--manifest",
                str(self.manifest),
                "--json",
            )
        self.assertEqual(result.exit_code, 1, result.output)
        payload = _payload(result)
        self._assert_contract(payload)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["summary"]["created"], [])
        self.assertFalse(self.progress.exists())
        self.assertEqual(
            (self.production.read_bytes(), self.production.stat().st_mtime_ns),
            production_before,
        )
        self.assertEqual(
            (self.manifest.read_bytes(), self.manifest.stat().st_mtime_ns),
            manifest_before,
        )

    def test_status_maps_all_legal_manifest_states_deterministically(self) -> None:
        expected = {
            "pending": ("pending", "run"),
            "running": ("running", "run"),
            "failed": ("failed", "resume"),
            "done": ("done", "human_review"),
            "paused": ("paused", "resume"),
            "blocked": ("blocked", "fix_input"),
        }

        for mode in expected:
            with self.subTest(mode=mode):
                manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
                tasks = manifest["tasks"]
                for task in tasks:
                    task["status"] = "pending"
                if mode == "running":
                    tasks[0]["status"] = "running"
                elif mode == "failed":
                    tasks[0]["status"] = "failed"
                elif mode == "done":
                    for task in tasks:
                        task["status"] = "done"
                elif mode in {"paused", "blocked"}:
                    tasks[0]["status"] = mode
                self.manifest.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                result = self._invoke(
                    "workflow",
                    "status",
                    "--manifest",
                    str(self.manifest),
                    "--json",
                )
                self.assertEqual(result.exit_code, 0, result.output)
                payload = _payload(result)
                self._assert_contract(payload)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["stage"], "assets")
                self.assertEqual(
                    (payload["status"], payload["next_action"]),
                    expected[mode],
                )

    def test_resume_delegates_to_existing_retry_runner(self) -> None:
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        task_id = manifest["tasks"][0]["id"]
        for task in manifest["tasks"]:
            task["status"] = "done"
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        runner_result = {
            "ok": True,
            "asset": manifest["tasks"][0].get("asset"),
            "reset_task_id": task_id,
            "recraft_prompt": True,
            "run_prompts": True,
            "reset_ids": [task_id],
            "run_exit_code": 0,
            "complete": True,
            "paused": False,
            "blocked": False,
        }
        with patch("workflow_cmds.retry_asset", return_value=runner_result) as retry_mock:
            result = self._invoke(
                "workflow",
                "resume",
                "--manifest",
                str(self.manifest),
                "--task-id",
                task_id,
                "--recraft-prompt",
                "--json",
            )
        self.assertEqual(result.exit_code, 0, result.output)
        payload = _payload(result)
        self._assert_contract(payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["stage"], "assets")
        self.assertEqual(
            (payload["status"], payload["next_action"]),
            ("done", "human_review"),
        )
        retry_mock.assert_called_once_with(
            self.manifest.resolve(),
            task_id=task_id,
            recraft_prompt=True,
        )

    def test_run_delegates_to_existing_asset_runner(self) -> None:
        def complete_manifest(path: Path, **kwargs: object) -> dict:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            for task in manifest["tasks"]:
                task["status"] = "done"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            return {
                "ok": True,
                "stopped_reason": "complete",
                "repair_rounds": 0,
                "complete": True,
                "paused": False,
                "blocked": False,
                "run_exit_code": 0,
            }

        with patch("workflow_cmds.run_assets", side_effect=complete_manifest) as run_mock:
            result = self._invoke(
                "workflow",
                "run",
                "--manifest",
                str(self.manifest),
                "--stage",
                "assets",
                "--no-auto-fix",
                "--run-prompts",
                "--jobs",
                "2",
                "--json",
            )
        self.assertEqual(result.exit_code, 0, result.output)
        payload = _payload(result)
        self._assert_contract(payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["stage"], "assets")
        self.assertEqual(
            (payload["status"], payload["next_action"]),
            ("done", "human_review"),
        )
        run_mock.assert_called_once_with(
            self.manifest.resolve(),
            jobs=2,
            run_prompts=True,
            run_game_dev=False,
            auto_fix=False,
        )

    def test_readme_quick_start_gates_init_on_successful_validation(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        quick_start = readme.split("## Quick Start", 1)[1].split("## 主要能力", 1)[0]
        validate_at = quick_start.index("workflow validate")
        init_at = quick_start.index("workflow init")
        between = quick_start[validate_at:init_at]
        self.assertLess(validate_at, init_at)
        self.assertIn("ok=true", between)
        self.assertIn("校验通过", between)
        self.assertIn("failures", between)

        skill = (
            REPO_ROOT / "resources" / "skills" / "gamefactory-toolkit" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for enum_group in (STATUSES, STAGES, NEXT_ACTIONS, FAILURE_KINDS):
            for value in enum_group:
                self.assertIn(f"`{value}`", skill)
        for legacy in (
            "`status=invalid`",
            "`status=incomplete`",
            "`status=ready`",
            "`status=complete`",
            '"stage": "brief"',
        ):
            self.assertNotIn(legacy, skill)


if __name__ == "__main__":
    unittest.main()
