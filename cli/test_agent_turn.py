"""Tests for agent_turn host (mocked executor CLIs)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_turn import (
    AgentTurnError,
    build_prompt,
    new_session,
    resolve_executor_for_role,
    run_turn,
    session_path_for,
    session_status,
)


class AgentTurnTests(unittest.TestCase):
    def test_resolve_executor_override(self) -> None:
        self.assertEqual(
            resolve_executor_for_role("product_host", {}, "codex"),
            "codex",
        )

    def test_build_prompt_includes_role(self) -> None:
        session = new_session("product_host", "s1")
        session["messages"] = [{"role": "user", "content": "跳跃穿模了"}]
        prompt = build_prompt(
            role_kind="product_host",
            user_message="再确认一下",
            session=session,
        )
        self.assertIn("项目经理", prompt)
        self.assertIn("再确认一下", prompt)

    def test_run_turn_hermes_mocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "product_host"
            conv.mkdir()
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._CONV_ROOT", Path(tmp)),
                patch("agent_turn._which_executor_bin", return_value="/bin/hermes"),
                patch(
                    "agent_turn._run_cmd",
                    return_value=type(
                        "P",
                        (),
                        {
                            "returncode": 0,
                            "stdout": "分诊为 A 纯 Bug，建议派程序员修碰撞。\nSession ID: abc12345\n",
                            "stderr": "",
                        },
                    )(),
                ),
            ):
                result = run_turn(
                    role_kind="product_host",
                    session_id="gui-sess-1",
                    message="跳跃穿模了",
                    config={"agents": {"orchestrator": {"executor": "hermes"}}},
                    timeout=30,
                )
            self.assertTrue(result["ok"])
            self.assertIn("分诊", result["assistant_message"])
            self.assertEqual(result["executor"], "hermes")
            st = session_status("product_host", "gui-sess-1")
            # status uses real conversations dir — patch path via file we wrote under tmp
            # Instead assert file under patched dir:
            path = conv / "gui-sess-1.json"
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["messages"]), 2)

    def test_missing_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "programmer"
            conv.mkdir()
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._which_executor_bin", return_value=None),
            ):
                with self.assertRaises(AgentTurnError):
                    run_turn(
                        role_kind="programmer",
                        session_id="p1",
                        message="修一下",
                        config={"agents": {"godot-developer": {"executor": "codex"}}},
                        executor="codex",
                        timeout=10,
                    )

    def test_it_defaults_to_pi(self) -> None:
        self.assertEqual(resolve_executor_for_role("it", {}), "pi")
        self.assertEqual(
            resolve_executor_for_role("it", {"agents": {"it": {"executor": "hermes"}}}),
            "hermes",
        )

    def test_it_hermes_rejected(self) -> None:
        from agent_turn import run_hermes_turn

        with patch("agent_turn._which_executor_bin", return_value="/bin/hermes"):
            with self.assertRaises(AgentTurnError) as ctx:
                run_hermes_turn(
                    "查一下环境",
                    role_kind="it",
                    executor_session_id=None,
                    timeout=5,
                )
        self.assertIn("Pi", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
