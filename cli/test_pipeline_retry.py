"""Tests for pipeline suggest-retry helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline_retry import _pick_reset_task_id, suggest_retry_commands


class PipelineRetryTests(unittest.TestCase):
    def test_pick_prefers_failed_generate(self) -> None:
        tasks = [
            {"id": "hero.prompt.craft", "asset": "hero", "status": "done"},
            {"id": "hero.image.generate", "asset": "hero", "status": "failed"},
            {"id": "hero.image.trim", "asset": "hero", "status": "pending"},
        ]
        self.assertEqual(_pick_reset_task_id(tasks, "hero"), "hero.image.generate")

    def test_suggest_includes_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "demo.json"
            manifest.write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "slime.image.generate", "asset": "slime", "status": "failed"},
                            {"id": "slime.image.trim", "asset": "slime", "status": "pending"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            cmds = suggest_retry_commands(
                manifest_rel=str(manifest),
                asset_names=["slime"],
            )
            self.assertTrue(any("pipeline reset" in c and "slime.image.generate" in c for c in cmds))
            self.assertTrue(any("pipeline run" in c for c in cmds))


if __name__ == "__main__":
    unittest.main()
