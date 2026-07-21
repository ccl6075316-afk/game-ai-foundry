"""Tests for agents.executors upsert (IT toolbox)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agents_executors_upsert import upsert_agent_executor


class AgentsExecutorsUpsertTests(unittest.TestCase):
    def test_rejects_without_i_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            res = upsert_agent_executor(
                executor="pi",
                provider="deepseek",
                i_confirm=False,
                config_path=path,
            )
            self.assertFalse(res["ok"])
            self.assertIn("i-confirm", res["error"])
            self.assertFalse(path.exists())

    def test_rejects_unknown_executor(self) -> None:
        res = upsert_agent_executor(executor="bash", provider="deepseek", i_confirm=True)
        self.assertFalse(res["ok"])
        self.assertIn("未知", res["error"])

    def test_writes_pi_preset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"agents": {"executors": {}}}, indent=2), encoding="utf-8")
            res = upsert_agent_executor(
                executor="pi",
                provider="deepseek",
                model="deepseek-chat",
                i_confirm=True,
                config_path=path,
            )
            self.assertTrue(res["ok"])
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                data["agents"]["executors"]["pi"],
                {"provider": "deepseek", "model": "deepseek-chat"},
            )

    def test_codex_use_third_party(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            res = upsert_agent_executor(
                executor="codex",
                provider="openrouter",
                use_third_party=True,
                i_confirm=True,
                config_path=path,
            )
            self.assertTrue(res["ok"])
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = data["agents"]["executors"]["codex"]
            self.assertEqual(entry["provider"], "openrouter")
            self.assertTrue(entry["use_third_party"])


if __name__ == "__main__":
    unittest.main()
