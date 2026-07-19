"""Tests for safe_cli whitelist + progress sync."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from production import (
    apply_production_delta,
    create_production_delta,
    derive_production,
    save_production,
)
from progress import init_progress, load_progress, save_progress, sync_progress_from_production
from safe_cli import filter_runnable_actions, normalize_action, parse_gamefactory_argv
from test_fixtures import EXAMPLE_BRIEF


class SafeCliTests(unittest.TestCase):
    def test_parse_and_allow(self) -> None:
        argv = parse_gamefactory_argv(
            "python gamefactory.py pipeline status --manifest ../pipeline/x.json --json"
        )
        self.assertEqual(argv[0], "pipeline")
        self.assertTrue(
            normalize_action("python gamefactory.py godot validate --project ../games/x")["ok"]
        )
        self.assertFalse(normalize_action("rm -rf /")["ok"])
        self.assertTrue(
            normalize_action(
                "python gamefactory.py config set --key image.constraints.size_multiple --value 16"
            )["ok"]
        )
        self.assertFalse(normalize_action("python gamefactory.py config set --key secrets.api_key --value x")["ok"])
        self.assertTrue(normalize_action("python gamefactory.py config get --key image.model")["ok"])

    def test_filter_skips_comments(self) -> None:
        items = filter_runnable_actions(
            [
                "# note",
                "python gamefactory.py pipeline status --json",
                "evil; rm -rf /",
            ]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["argv"][0], "pipeline")


class ProgressSyncTests(unittest.TestCase):
    def test_sync_adds_delta_tasks(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            prod_path = base / "production.json"
            prog_path = base / "progress.json"
            save_production(data, prod_path)
            prog = init_progress(brief_path=EXAMPLE_BRIEF, production_path=prod_path)
            save_progress(prog, prog_path)
            before = len(prog["phases"]["godot_tasks"])

            delta = create_production_delta(
                change_id="010-sync",
                user_intent="Add shield",
                godot_tasks=["Add shield pickup"],
            )
            merged = apply_production_delta(data, delta)
            result = sync_progress_from_production(prog, merged)
            self.assertEqual(len(result["added"]), 1)
            self.assertEqual(len(prog["phases"]["godot_tasks"]), before + 1)
            save_progress(prog, prog_path)
            loaded = load_progress(prog_path)
            self.assertTrue(
                any(str(t.get("id", "")).startswith("delta_010") for t in loaded["phases"]["godot_tasks"])
            )


if __name__ == "__main__":
    unittest.main()
