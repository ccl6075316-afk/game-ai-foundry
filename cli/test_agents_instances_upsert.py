"""Tests for agents.instances upsert (IT toolbox)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agents_instances_upsert import upsert_agent_instance


class AgentsInstancesUpsertTests(unittest.TestCase):
    def _cfg(self, path: Path, instance_id: str = "it-1") -> None:
        path.write_text(
            json.dumps(
                {
                    "agents": {
                        "instances": {
                            instance_id: {
                                "role_kind": "it",
                                "executor": "pi",
                                "provider": "deepseek",
                            }
                        }
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def test_rejects_without_i_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self._cfg(path)
            res = upsert_agent_instance(
                instance_id="it-1",
                thinking_level="medium",
                i_confirm=False,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("i-confirm", res["error"])

    def test_rejects_missing_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self._cfg(path)
            res = upsert_agent_instance(
                instance_id="nope",
                thinking_level="high",
                i_confirm=True,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("不存在", res["error"])

    def test_writes_thinking_and_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self._cfg(path)
            res = upsert_agent_instance(
                instance_id="it-1",
                model="deepseek-v4-pro",
                thinking_level="medium",
                i_confirm=True,
                config_path=path,
            )
            self.assertTrue(res["ok"], res)
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = data["agents"]["instances"]["it-1"]
            self.assertEqual(entry["thinking_level"], "medium")
            self.assertEqual(entry["model"], "deepseek-v4-pro")

    def test_rejects_non_pi_executor_for_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self._cfg(path)
            res = upsert_agent_instance(
                instance_id="it-1",
                executor="hermes",
                i_confirm=True,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("Pi", res["error"])


if __name__ == "__main__":
    unittest.main()
