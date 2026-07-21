"""Tests for agent_turn host (mocked executor CLIs)."""

from __future__ import annotations

import json
import subprocess
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

    def test_instance_overlay_executor(self) -> None:
        config = {
            "agents": {
                "it": {"executor": "pi"},
                "instances": {
                    "ops-deepseek": {
                        "role_kind": "it",
                        "executor": "hermes",
                        "provider": "deepseek",
                        "model": "deepseek-chat",
                    },
                },
            },
            "provider_accounts": {
                "deepseek": {"api_key": "sk-test"},
            },
        }
        self.assertEqual(
            resolve_executor_for_role("it", config, instance_id="ops-deepseek"),
            "hermes",
        )

    def test_cli_executor_override_wins_over_instance(self) -> None:
        config = {
            "agents": {
                "instances": {
                    "ops-1": {"role_kind": "it", "executor": "hermes"},
                },
            },
        }
        self.assertEqual(
            resolve_executor_for_role("it", config, override="codex", instance_id="ops-1"),
            "codex",
        )

    def test_different_instance_ids_resolve_different_providers(self) -> None:
        from agent_auth_resolve import resolve_agent_auth

        config = {
            "agents": {
                "it": {"executor": "pi", "provider": "openrouter"},
                "instances": {
                    "ops-or": {"role_kind": "it", "provider": "openrouter", "model": "openai/gpt-4o-mini"},
                    "ops-ds": {"role_kind": "it", "provider": "deepseek", "model": "deepseek-chat"},
                },
            },
            "provider_accounts": {
                "openrouter": {"api_key": "sk-or"},
                "deepseek": {"api_key": "sk-ds"},
            },
        }
        or_auth = resolve_agent_auth(config, role_kind="it", instance_id="ops-or")
        ds_auth = resolve_agent_auth(config, role_kind="it", instance_id="ops-ds")
        self.assertEqual(or_auth["provider"], "openrouter")
        self.assertEqual(ds_auth["provider"], "deepseek")
        self.assertNotEqual(or_auth["provider"], ds_auth["provider"])

    def test_run_turn_pi_passes_instance_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "it"
            conv.mkdir()
            captured: dict[str, object] = {}

            def fake_pi_turn(*args: object, **kwargs: object) -> tuple[str, None, str]:
                captured.update(kwargs)
                return "环境正常", None, ""

            config = {
                "agents": {
                    "it": {"executor": "pi", "provider": "deepseek"},
                    "instances": {
                        "it-1": {
                            "role_kind": "it",
                            "provider": "deepseek",
                            "model": "deepseek-chat",
                        },
                    },
                },
                "provider_accounts": {"deepseek": {"api_key": "sk-ds"}},
            }
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._CONV_ROOT", Path(tmp)),
                patch("agent_turn.run_pi_executor_turn", side_effect=fake_pi_turn),
            ):
                result = run_turn(
                    role_kind="it",
                    session_id="it-s1",
                    message="查一下 doctor",
                    config=config,
                    instance_id="it-1",
                    timeout=30,
                )
            self.assertTrue(result["ok"])
            self.assertEqual(captured.get("instance_id"), "it-1")

    def test_run_turn_hermes_passes_model_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "product_host"
            conv.mkdir()
            argv_seen: list[list[str]] = []

            def fake_run_cmd(argv: list[str], **kwargs: object) -> object:
                argv_seen.append(list(argv))
                return type(
                    "P",
                    (),
                    {
                        "returncode": 0,
                        "stdout": "好的，已分诊。\nSession ID: sess-99\n",
                        "stderr": "",
                    },
                )()

            config = {
                "agents": {
                    "orchestrator": {"executor": "hermes", "provider": "deepseek", "model": "deepseek-chat"},
                    "instances": {
                        "pm-1": {
                            "role_kind": "product_host",
                            "executor": "hermes",
                            "provider": "deepseek",
                            "model": "deepseek-chat",
                        },
                    },
                },
                "provider_accounts": {"deepseek": {"api_key": "sk-ds", "api_base": "https://api.deepseek.com/v1"}},
            }
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._CONV_ROOT", Path(tmp)),
                patch("agent_turn._which_executor_bin", return_value="/bin/hermes"),
                patch("agent_turn._run_cmd", side_effect=fake_run_cmd),
            ):
                run_turn(
                    role_kind="product_host",
                    session_id="pm-s1",
                    message="下一步",
                    config=config,
                    instance_id="pm-1",
                    timeout=30,
                )
            self.assertTrue(argv_seen)
            flat = " ".join(argv_seen[0])
            self.assertIn("-m", argv_seen[0])
            self.assertIn("deepseek-chat", flat)

    def test_run_turn_pi_auth_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "it"
            conv.mkdir()
            config = {
                "agents": {
                    "it": {"executor": "pi", "provider": "deepseek"},
                    "instances": {
                        "it-bad": {"role_kind": "it", "provider": "deepseek"},
                    },
                },
            }
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._CONV_ROOT", Path(tmp)),
            ):
                with self.assertRaises(AgentTurnError) as ctx:
                    run_turn(
                        role_kind="it",
                        session_id="it-err",
                        message="查环境",
                        config=config,
                        instance_id="it-bad",
                        timeout=10,
                    )
            self.assertIn("API Key", str(ctx.exception))


class TestCodexModel(unittest.TestCase):
    def test_codex_empty_model_uses_mid_default(self) -> None:
        captured: dict[str, list[str]] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        with (
            patch("agent_turn._which_executor_bin", return_value="codex"),
            patch("agent_turn._run_cmd", side_effect=fake_run),
        ):
            from agent_turn import run_codex_turn

            run_codex_turn(
                "hi",
                executor_session_id=None,
                timeout=30,
                model="",
            )
        self.assertIn("-m", captured["argv"])
        self.assertIn("gpt-5.3", captured["argv"])

    def test_codex_passes_model_flag(self) -> None:
        captured: dict[str, list[str]] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        with (
            patch("agent_turn._which_executor_bin", return_value="codex"),
            patch("agent_turn._run_cmd", side_effect=fake_run),
        ):
            from agent_turn import run_codex_turn

            run_codex_turn(
                "hi",
                executor_session_id=None,
                timeout=30,
                model="gpt-5.5",
            )
        self.assertIn("-m", captured["argv"])
        self.assertIn("gpt-5.5", captured["argv"])


class TestCursorModel(unittest.TestCase):
    def test_cursor_passes_model_flag(self) -> None:
        captured: dict[str, list[str]] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        with (
            patch("agent_turn._which_executor_bin", return_value="agent"),
            patch("agent_turn._run_cmd", side_effect=fake_run),
        ):
            from agent_turn import run_cursor_turn

            run_cursor_turn(
                "hi",
                executor_session_id=None,
                timeout=30,
                model="opus-4.5",
            )
        self.assertTrue(
            "--model" in captured["argv"] or "-m" in captured["argv"]
        )
        self.assertIn("opus-4.5", captured["argv"])


if __name__ == "__main__":
    unittest.main()
