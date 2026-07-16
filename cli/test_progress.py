"""Tests for progress ledger."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from production import derive_production, save_production
from progress import (
    init_progress,
    load_progress,
    save_progress,
    update_task_status,
    update_validation_layer,
)
from test_fixtures import EXAMPLE_BRIEF


class ProgressTest(unittest.TestCase):
    def test_init_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prod_path = Path(tmp) / "production.json"
            save_production(derive_production(EXAMPLE_BRIEF), prod_path)
            data = init_progress(brief_path=EXAMPLE_BRIEF, production_path=prod_path)
            self.assertEqual(len(data["phases"]["godot_tasks"]), 6)
            update_task_status(data, "input_map", "done")
            update_validation_layer(data, "validate", "pass")
            out = Path(tmp) / "progress.json"
            save_progress(data, out)
            loaded = load_progress(out)
            task = next(t for t in loaded["phases"]["godot_tasks"] if t["id"] == "input_map")
            self.assertEqual(task["status"], "done")
            self.assertEqual(loaded["phases"]["validation"]["validate"], "pass")


if __name__ == "__main__":
    unittest.main()
