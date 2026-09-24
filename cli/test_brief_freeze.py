"""Tests for deterministic Brief freeze."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import click
from click.testing import CliRunner

from brief_cmds import register_brief_commands
from test_fixtures import SMOKE_BRIEF


def _brief_cli() -> click.Group:
    @click.group()
    @click.pass_context
    def root(ctx: click.Context) -> None:
        ctx.ensure_object(dict)
        ctx.obj.setdefault("config", {})

    register_brief_commands(root)
    return root


class BriefFreezeTests(unittest.TestCase):
    def test_freeze_success_writes_brief_meta_and_stable_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "draft.json"
            output_path = root / "nested" / "brief.json"
            input_path.write_text(json.dumps(SMOKE_BRIEF), encoding="utf-8")
            result = CliRunner().invoke(
                _brief_cli(),
                ["brief", "freeze", "--input", str(input_path), "-o", str(output_path), "--json"],
            )
            self.assertEqual(result.exit_code, 0, result.output)
            payload = json.loads(result.output)
            self.assertEqual(set(payload), {"ok", "input", "output", "brief_meta", "gaps"})
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["input"], str(input_path.resolve()))
            self.assertEqual(payload["output"], str(output_path.resolve()))
            self.assertEqual(payload["gaps"], [])
            self.assertEqual(payload["brief_meta"]["contract_version"], 1)
            self.assertEqual(payload["brief_meta"]["source"], "manual")
            self.assertTrue(payload["brief_meta"]["frozen_at"])
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["brief_meta"], payload["brief_meta"])

    def test_freeze_validation_failure_does_not_create_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "draft.json"
            output_path = root / "missing" / "brief.json"
            invalid = json.loads(json.dumps(SMOKE_BRIEF))
            invalid["project"].pop("genre", None)
            input_path.write_text(json.dumps(invalid), encoding="utf-8")
            result = CliRunner().invoke(
                _brief_cli(),
                ["brief", "freeze", "--input", str(input_path), "-o", str(output_path), "--json"],
            )
            self.assertEqual(result.exit_code, 1, result.output)
            payload = json.loads(result.output)
            self.assertEqual(set(payload), {"ok", "input", "output", "brief_meta", "gaps"})
            self.assertFalse(payload["ok"])
            self.assertIsNone(payload["brief_meta"])
            self.assertTrue(payload["gaps"])
            self.assertFalse(output_path.exists())
            self.assertFalse(output_path.parent.exists())

    def test_freeze_help_exposes_deterministic_options(self) -> None:
        result = CliRunner().invoke(_brief_cli(), ["brief", "freeze", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--input", result.output)
        self.assertIn("--output", result.output)
        self.assertIn("--json", result.output)


if __name__ == "__main__":
    unittest.main()
