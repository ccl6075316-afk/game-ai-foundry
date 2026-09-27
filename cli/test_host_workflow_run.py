"""Tests for the one-shot external-agent workflow bridge."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from host.workflow_run import run_workflow
from workflow.contract import build_response


def _response(command: str, status: str, next_action: str, *, ok: bool = True) -> dict:
    return build_response(
        command=command,
        ok=ok,
        stage="design" if command in {"context", "validate"} else "assets",
        status=status,
        next_action=next_action,
        summary={"missing": [], "manifest": {"failed_ids": []}},
    )


class HostWorkflowRunTests(unittest.TestCase):
    @staticmethod
    def _cmd(argv: list[str]) -> str:
        return argv[1] if argv and argv[0] == "workflow" else argv[0]

    def test_dry_run_only_executes_context_and_validate(self) -> None:
        calls: list[list[str]] = []

        def runner(argv: list[str]) -> dict:
            calls.append(argv)
            return {"exit_code": 0, "payload": _response(self._cmd(argv), "done", "derive_production")}

        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.json"
            brief.write_text("{}", encoding="utf-8")
            result = run_workflow(brief, dry_run=True, runner=runner)

        self.assertTrue(result["ok"])
        self.assertEqual([self._cmd(call) for call in calls], ["context", "validate"])

    def test_full_chain_uses_single_confirmation(self) -> None:
        calls: list[list[str]] = []

        def runner(argv: list[str]) -> dict:
            calls.append(argv)
            command = self._cmd(argv)
            if command == "context":
                payload = _response("context", "done", "derive_production")
                payload["summary"] = {"missing": ["production"], "manifest": {"failed_ids": []}}
                return {"exit_code": 0, "payload": payload}
            responses = {
                "validate": _response("validate", "done", "run"),
                "init": _response("init", "done", "run"),
                "run": _response("run", "done", "human_review"),
                "status": _response("status", "done", "human_review"),
            }
            return {"exit_code": 0, "payload": responses[command]}

        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.json"
            brief.write_text("{}", encoding="utf-8")
            result = run_workflow(brief, i_confirm=True, runner=runner)

        self.assertTrue(result["ok"])
        self.assertEqual(
            [self._cmd(call) for call in calls],
            ["context", "validate", "init", "validate", "run", "status"],
        )

    def test_detach_skips_auto_resume_and_passes_job_id_to_status(self) -> None:
        calls: list[list[str]] = []

        def runner(argv: list[str]) -> dict:
            calls.append(argv)
            command = self._cmd(argv)
            if command == "context":
                payload = _response("context", "done", "derive_production")
                payload["summary"] = {"missing": ["production"], "manifest": {"failed_ids": []}}
                return {"exit_code": 0, "payload": payload}
            if command == "run":
                self.assertIn("--detach", argv)
                payload = _response("run", "running", "poll")
                payload["summary"] = {
                    "job_id": "jobdeadbeef01",
                    "jobs_dir": "/tmp/jobs",
                    "manifest": {"failed_ids": []},
                }
                return {"exit_code": 0, "payload": payload}
            if command == "status":
                self.assertIn("--job-id", argv)
                self.assertIn("jobdeadbeef01", argv)
                return {"exit_code": 0, "payload": _response("status", "running", "poll")}
            responses = {
                "validate": _response("validate", "done", "run"),
                "init": _response("init", "done", "run"),
            }
            return {"exit_code": 0, "payload": responses[command]}

        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.json"
            brief.write_text("{}", encoding="utf-8")
            result = run_workflow(brief, i_confirm=True, detach=True, runner=runner)

        self.assertTrue(result["ok"])
        self.assertEqual(result["next_action"], "poll")
        self.assertEqual(
            [self._cmd(call) for call in calls],
            ["context", "validate", "init", "validate", "run", "status"],
        )
        self.assertNotIn("resume", [self._cmd(call) for call in calls])

    def test_missing_confirmation_blocks_before_init(self) -> None:
        calls: list[list[str]] = []

        def runner(argv: list[str]) -> dict:
            calls.append(argv)
            return {"exit_code": 0, "payload": _response(self._cmd(argv), "done", "derive_production")}

        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.json"
            brief.write_text("{}", encoding="utf-8")
            result = run_workflow(brief, runner=runner)

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"][0]["code"], "confirmation_required")
        self.assertEqual([self._cmd(call) for call in calls], ["context", "validate"])


if __name__ == "__main__":
    unittest.main()
