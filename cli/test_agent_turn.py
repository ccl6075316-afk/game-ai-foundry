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
    record_turn_exchange,
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

    def test_codex_sandbox_from_arg(self) -> None:
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
                sandbox="read-only",
            )
        self.assertIn("--sandbox", captured["argv"])
        idx = captured["argv"].index("--sandbox")
        self.assertEqual(captured["argv"][idx + 1], "read-only")


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
        self.assertIn("--force", captured["argv"])

    def test_cursor_auto_review_mode(self) -> None:
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
                permission_mode="auto_review",
            )
        self.assertIn("--auto-review", captured["argv"])
        self.assertNotIn("--force", captured["argv"])

    def test_cursor_plan_mode(self) -> None:
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
                permission_mode="plan",
            )
        self.assertIn("--mode", captured["argv"])
        idx = captured["argv"].index("--mode")
        self.assertEqual(captured["argv"][idx + 1], "plan")
        self.assertNotIn("--force", captured["argv"])


class TestExecutorSafetyConfig(unittest.TestCase):
    def test_resolve_defaults(self) -> None:
        from agent_turn import (
            resolve_codex_sandbox,
            resolve_cursor_permission_mode,
            resolve_hermes_yolo,
        )

        self.assertEqual(resolve_codex_sandbox({}), "workspace-write")
        self.assertEqual(resolve_cursor_permission_mode({}), "force")
        self.assertTrue(resolve_hermes_yolo({}))

    def test_resolve_from_executors(self) -> None:
        from agent_turn import (
            resolve_codex_sandbox,
            resolve_cursor_permission_mode,
            resolve_hermes_yolo,
        )

        cfg = {
            "agents": {
                "executors": {
                    "codex": {"sandbox": "danger-full-access"},
                    "cursor": {"permission_mode": "ask"},
                    "hermes": {"yolo": False},
                }
            }
        }
        self.assertEqual(resolve_codex_sandbox(cfg), "danger-full-access")
        self.assertEqual(resolve_cursor_permission_mode(cfg), "ask")
        self.assertFalse(resolve_hermes_yolo(cfg))

    def test_hermes_yolo_false_refuses_without_run(self) -> None:
        with (
            patch("agent_turn._which_executor_bin", return_value="hermes"),
            patch("agent_turn._run_cmd") as run_cmd,
        ):
            from agent_turn import AgentTurnError, run_hermes_turn

            with self.assertRaises(AgentTurnError) as ctx:
                run_hermes_turn(
                    "hi",
                    role_kind="product_host",
                    executor_session_id=None,
                    timeout=30,
                    config={"agents": {"executors": {"hermes": {"yolo": False}}}},
                )
            self.assertIn("yolo", str(ctx.exception).lower())
            self.assertIn("ACP", str(ctx.exception))
            run_cmd.assert_not_called()

    def test_run_executor_turn_passes_sandbox(self) -> None:
        captured: dict[str, list[str]] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        cfg = {"agents": {"executors": {"codex": {"sandbox": "read-only"}}}}
        with (
            patch("agent_turn._which_executor_bin", return_value="codex"),
            patch("agent_turn._run_cmd", side_effect=fake_run),
        ):
            from agent_turn import run_executor_turn

            run_executor_turn(
                "codex",
                "hi",
                role_kind="programmer",
                executor_session_id=None,
                config=cfg,
                resolved_auth={"model": "gpt-5.3"},
            )
        idx = captured["argv"].index("--sandbox")
        self.assertEqual(captured["argv"][idx + 1], "read-only")

    def test_cursor_non_force_refuses_without_run(self) -> None:
        with (
            patch("agent_turn._which_executor_bin", return_value="agent"),
            patch("agent_turn._run_cmd") as run_cmd,
        ):
            from agent_turn import AgentTurnError, run_executor_turn

            cfg = {"agents": {"executors": {"cursor": {"permission_mode": "auto_review"}}}}
            with self.assertRaises(AgentTurnError) as ctx:
                run_executor_turn(
                    "cursor",
                    "hi",
                    role_kind="programmer",
                    executor_session_id=None,
                    config=cfg,
                    resolved_auth={"model": "auto"},
                )
            msg = str(ctx.exception)
            self.assertIn("GUI", msg)
            self.assertIn("force", msg)
            run_cmd.assert_not_called()

    def test_cursor_ask_mode_refuses_without_run(self) -> None:
        with (
            patch("agent_turn._which_executor_bin", return_value="agent"),
            patch("agent_turn._run_cmd") as run_cmd,
        ):
            from agent_turn import AgentTurnError, run_executor_turn

            cfg = {"agents": {"executors": {"cursor": {"permission_mode": "ask"}}}}
            with self.assertRaises(AgentTurnError):
                run_executor_turn(
                    "cursor",
                    "hi",
                    role_kind="programmer",
                    executor_session_id=None,
                    config=cfg,
                )
            run_cmd.assert_not_called()

    def test_cursor_force_still_runs(self) -> None:
        captured: dict[str, list[str]] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        cfg = {"agents": {"executors": {"cursor": {"permission_mode": "force"}}}}
        with (
            patch("agent_turn._which_executor_bin", return_value="agent"),
            patch("agent_turn._run_cmd", side_effect=fake_run),
        ):
            from agent_turn import run_executor_turn

            run_executor_turn(
                "cursor",
                "hi",
                role_kind="programmer",
                executor_session_id=None,
                config=cfg,
                resolved_auth={"model": "auto"},
            )
        self.assertIn("--force", captured["argv"])


class TestInstanceExecutorSafety(unittest.TestCase):
    def test_instance_sandbox_overrides_global(self) -> None:
        captured: dict[str, list[str]] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        cfg = {
            "agents": {
                "executors": {"codex": {"sandbox": "danger-full-access"}},
                "instances": {
                    "dev-1": {
                        "role_kind": "programmer",
                        "executor": "codex",
                        "sandbox": "read-only",
                    },
                },
            }
        }
        with (
            patch("agent_turn._which_executor_bin", return_value="codex"),
            patch("agent_turn._run_cmd", side_effect=fake_run),
        ):
            from agent_turn import run_executor_turn

            run_executor_turn(
                "codex",
                "hi",
                role_kind="programmer",
                executor_session_id=None,
                config=cfg,
                instance_id="dev-1",
                resolved_auth={"model": "gpt-5.3"},
            )
        idx = captured["argv"].index("--sandbox")
        self.assertEqual(captured["argv"][idx + 1], "read-only")

    def test_no_instance_key_same_as_global_only(self) -> None:
        from agent_turn import resolve_codex_sandbox, resolve_cursor_permission_mode, resolve_hermes_yolo

        cfg = {
            "agents": {
                "executors": {
                    "codex": {"sandbox": "danger-full-access"},
                    "cursor": {"permission_mode": "ask"},
                    "hermes": {"yolo": False},
                },
                "instances": {
                    "dev-1": {
                        "role_kind": "programmer",
                        "executor": "codex",
                    },
                },
            }
        }
        self.assertEqual(resolve_codex_sandbox(cfg, instance_id="dev-1"), "danger-full-access")
        self.assertEqual(resolve_cursor_permission_mode(cfg, instance_id="dev-1"), "ask")
        self.assertFalse(resolve_hermes_yolo(cfg, instance_id="dev-1"))

    def test_instance_yolo_false_refuses_without_run(self) -> None:
        with (
            patch("agent_turn._which_executor_bin", return_value="hermes"),
            patch("agent_turn._run_cmd") as run_cmd,
        ):
            from agent_turn import AgentTurnError, run_hermes_turn

            cfg = {
                "agents": {
                    "executors": {"hermes": {"yolo": True}},
                    "instances": {
                        "pm-1": {
                            "role_kind": "product_host",
                            "executor": "hermes",
                            "yolo": False,
                        },
                    },
                }
            }
            with self.assertRaises(AgentTurnError) as ctx:
                run_hermes_turn(
                    "hi",
                    role_kind="product_host",
                    executor_session_id=None,
                    timeout=30,
                    config=cfg,
                    instance_id="pm-1",
                )
            self.assertIn("yolo", str(ctx.exception).lower())
            self.assertIn("instances", str(ctx.exception).lower())
            self.assertIn("ACP", str(ctx.exception))
            run_cmd.assert_not_called()

    def test_instance_sandbox_ignored_for_cursor(self) -> None:
        captured: dict[str, list[str]] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        cfg = {
            "agents": {
                "executors": {"cursor": {"permission_mode": "force"}},
                "instances": {
                    "dev-cursor": {
                        "role_kind": "programmer",
                        "executor": "cursor",
                        "sandbox": "read-only",
                    },
                },
            }
        }
        with (
            patch("agent_turn._which_executor_bin", return_value="agent"),
            patch("agent_turn._run_cmd", side_effect=fake_run),
        ):
            from agent_turn import run_executor_turn

            run_executor_turn(
                "cursor",
                "hi",
                role_kind="programmer",
                executor_session_id=None,
                config=cfg,
                instance_id="dev-cursor",
                resolved_auth={"model": "auto"},
            )
        self.assertIn("--force", captured["argv"])
        self.assertNotIn("--sandbox", captured["argv"])

    def test_instance_non_force_cursor_refuses_without_run(self) -> None:
        with (
            patch("agent_turn._which_executor_bin", return_value="agent"),
            patch("agent_turn._run_cmd") as run_cmd,
        ):
            from agent_turn import AgentTurnError, run_executor_turn

            cfg = {
                "agents": {
                    "executors": {"cursor": {"permission_mode": "force"}},
                    "instances": {
                        "dev-cursor": {
                            "role_kind": "programmer",
                            "executor": "cursor",
                            "permission_mode": "plan",
                        },
                    },
                }
            }
            with self.assertRaises(AgentTurnError) as ctx:
                run_executor_turn(
                    "cursor",
                    "hi",
                    role_kind="programmer",
                    executor_session_id=None,
                    config=cfg,
                    instance_id="dev-cursor",
                )
            self.assertIn("GUI", str(ctx.exception))
            run_cmd.assert_not_called()

    def test_invalid_instance_value_falls_back_to_global(self) -> None:
        from agent_turn import resolve_codex_sandbox, resolve_cursor_permission_mode

        cfg = {
            "agents": {
                "executors": {
                    "codex": {"sandbox": "danger-full-access"},
                    "cursor": {"permission_mode": "ask"},
                },
                "instances": {
                    "dev-1": {
                        "role_kind": "programmer",
                        "executor": "codex",
                        "sandbox": "not-a-sandbox",
                        "permission_mode": "bogus",
                    },
                },
            }
        }
        self.assertEqual(resolve_codex_sandbox(cfg, instance_id="dev-1"), "danger-full-access")
        self.assertEqual(resolve_cursor_permission_mode(cfg, instance_id="dev-1"), "ask")

    def test_record_turn_exchange_persists_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "programmer"
            conv.mkdir()
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._CONV_ROOT", Path(tmp)),
            ):
                result = record_turn_exchange(
                    role_kind="programmer",
                    session_id="acp-s1",
                    user_message="你好",
                    assistant_message="已收到",
                    executor="cursor",
                )
            self.assertTrue(result["ok"])
            self.assertEqual(result["assistant_message"], "已收到")
            self.assertEqual(result["executor"], "cursor")
            path = conv / "acp-s1.json"
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["messages"]), 2)
            self.assertEqual(data["messages"][0]["content"], "你好")
            self.assertEqual(data["messages"][1]["content"], "已收到")

    def test_record_turn_exchange_persists_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "programmer"
            conv.mkdir()
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._CONV_ROOT", Path(tmp)),
            ):
                result = record_turn_exchange(
                    role_kind="programmer",
                    session_id="acp-s1",
                    user_message="你好",
                    assistant_message="已收到",
                    executor="cursor",
                )
            self.assertTrue(result["ok"])
            self.assertEqual(result["assistant_message"], "已收到")
            self.assertEqual(result["executor"], "cursor")
            path = conv / "acp-s1.json"
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["messages"]), 2)
            self.assertEqual(data["messages"][0]["content"], "你好")
            self.assertEqual(data["messages"][1]["content"], "已收到")
