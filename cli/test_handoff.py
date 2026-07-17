"""Tests for handoff file bus + dispatch parsing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from handoff import (
    apply_product_host_dispatch,
    create_handoff,
    extract_dispatch_payload,
    list_handoffs,
    open_handoffs_for_prompt,
    set_handoff_status,
    strip_dispatch_fence,
)


class HandoffTests(unittest.TestCase):
    def test_extract_dispatch_from_fence(self) -> None:
        text = (
            "这是纯 Bug，建议派程序员修碰撞。\n\n"
            "```json\n"
            '{"triage":"bug","dispatch":{"to":"programmer","task_id":"player_move",'
            '"asset_names":[],"cli_hints":["godot validate"]},'
            '"progress_note":"穿模反馈已分诊"}\n'
            "```"
        )
        payload = extract_dispatch_payload(text)
        assert payload is not None
        self.assertEqual(payload["triage"], "bug")
        self.assertEqual(payload["dispatch"]["to"], "programmer")
        cleaned = strip_dispatch_fence(text)
        self.assertIn("纯 Bug", cleaned)
        self.assertNotIn("```json", cleaned)

    def test_create_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            doc = create_handoff(
                triage="bug",
                title="Fix jump",
                summary="collision wrong",
                task_id="player_jump",
                base_dir=base,
            )
            self.assertTrue(Path(doc["_path"]).is_file())
            items = list_handoffs(status="open", base_dir=base)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["id"], "player_jump")
            set_handoff_status(Path(doc["_path"]), "done")
            self.assertEqual(list_handoffs(status="open", base_dir=base), [])
            self.assertEqual(len(list_handoffs(status="done", base_dir=base)), 1)

    def test_target_instance_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            create_handoff(
                triage="bug",
                title="For A",
                summary="a",
                target_instance_id="prog-a",
                handoff_id="ho-a",
                base_dir=base,
            )
            create_handoff(
                triage="bug",
                title="Broadcast",
                summary="b",
                handoff_id="ho-b",
                base_dir=base,
            )
            create_handoff(
                triage="bug",
                title="For C",
                summary="c",
                target_instance_id="prog-c",
                handoff_id="ho-c",
                base_dir=base,
            )
            for_a = list_handoffs(status="open", target_instance_id="prog-a", base_dir=base)
            ids = {i["id"] for i in for_a}
            self.assertEqual(ids, {"ho-a", "ho-b"})
            docs = open_handoffs_for_prompt(target_instance_id="prog-a", base_dir=base)
            self.assertEqual(len(docs), 2)

    def test_apply_programmer_done_updates_task(self) -> None:
        from handoff import apply_programmer_done

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            progress_path = base / "progress.json"
            progress_path.write_text(
                json.dumps(
                    {
                        "progress_meta": {"slug": "demo"},
                        "phases": {
                            "godot_tasks": [
                                {"id": "player_jump", "title": "Jump", "status": "in_progress"}
                            ]
                        },
                        "memory": [],
                    }
                ),
                encoding="utf-8",
            )
            doc = create_handoff(
                triage="bug",
                title="Fix jump",
                summary="x",
                task_id="player_jump",
                handoff_id="player_jump",
                progress_path=str(progress_path),
                base_dir=base,
            )
            result = apply_programmer_done(
                "player_jump",
                progress_path=progress_path,
                progress_note="fixed",
                base_dir=base,
            )
            self.assertEqual(result["task_done"], "player_jump")
            prog = json.loads(progress_path.read_text(encoding="utf-8"))
            self.assertEqual(prog["phases"]["godot_tasks"][0]["status"], "done")
            self.assertEqual(
                json.loads(Path(doc["_path"]).read_text(encoding="utf-8"))["handoff_meta"]["status"],
                "done",
            )

    def test_apply_writes_progress_and_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            progress_path = base / "progress.json"
            progress_path.write_text(
                json.dumps(
                    {
                        "progress_meta": {"slug": "demo"},
                        "phases": {
                            "godot_tasks": [
                                {"id": "player_jump", "title": "Jump", "status": "pending"}
                            ]
                        },
                        "memory": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            payload = {
                "triage": "bug",
                "dispatch": {
                    "to": "programmer",
                    "task_id": "player_jump",
                    "target_instance_id": "prog-1",
                    "asset_names": [],
                    "cli_hints": ["python gamefactory.py godot validate --project games/demo"],
                },
                "progress_note": "用户反馈跳跃穿模",
            }
            result = apply_product_host_dispatch(
                payload,
                assistant_message="已分诊为 Bug。",
                progress_path=progress_path,
                brief_path=None,
                from_session_id="sess-1",
                base_dir=base / "handoffs",
            )
            self.assertTrue(result["applied"])
            self.assertEqual(result["target_instance_id"], "prog-1")
            self.assertTrue(result["progress_note_written"])
            self.assertEqual(result["task_updated"], "player_jump")
            self.assertTrue(result["handoff_path"])
            prog = json.loads(progress_path.read_text(encoding="utf-8"))
            self.assertTrue(any("穿模" in m for m in prog["memory"]))
            self.assertEqual(prog["phases"]["godot_tasks"][0]["status"], "in_progress")
            hos = open_handoffs_for_prompt(base_dir=base / "handoffs", target_instance_id="prog-1")
            self.assertEqual(len(hos), 1)
            self.assertEqual(
                hos[0]["handoff_meta"]["target_instance_id"],
                "prog-1",
            )

    def test_run_turn_applies_dispatch(self) -> None:
        from agent_turn import run_turn

        with tempfile.TemporaryDirectory() as tmp:
            conv = Path(tmp) / "product_host"
            conv.mkdir()
            handoffs = Path(tmp) / "handoffs"
            progress_path = Path(tmp) / "progress.json"
            progress_path.write_text(
                json.dumps(
                    {
                        "progress_meta": {"slug": "x"},
                        "phases": {"godot_tasks": [{"id": "t1", "status": "pending"}]},
                        "memory": [],
                    }
                ),
                encoding="utf-8",
            )
            reply = (
                "分诊为 Bug，派程序员。\n"
                "```json\n"
                '{"triage":"bug","dispatch":{"to":"programmer","task_id":"t1",'
                '"asset_names":[],"cli_hints":[]},"progress_note":"bug jump"}\n'
                "```"
            )
            with (
                patch("agent_turn.conversations_dir", return_value=conv),
                patch("agent_turn._find_default_progress", return_value=progress_path),
                patch("agent_turn._find_default_brief", return_value=None),
                patch("agent_turn._which_executor_bin", return_value="/bin/hermes"),
                patch(
                    "agent_turn._run_cmd",
                    return_value=type(
                        "P",
                        (),
                        {"returncode": 0, "stdout": reply, "stderr": ""},
                    )(),
                ),
                patch("handoff._HANDOFF_DIR", handoffs),
            ):
                # apply uses base_dir=None → _HANDOFF_DIR patched
                result = run_turn(
                    role_kind="product_host",
                    session_id="s1",
                    message="跳跃穿模",
                    config={"agents": {"orchestrator": {"executor": "hermes"}}},
                    progress_path=progress_path,
                    timeout=30,
                )
            self.assertIn("handoff", result["assistant_message"].lower())
            self.assertTrue(result.get("dispatch", {}).get("handoff_path"))
            self.assertTrue((handoffs / "t1.json").is_file() or list(handoffs.glob("*.json")))


if __name__ == "__main__":
    unittest.main()
