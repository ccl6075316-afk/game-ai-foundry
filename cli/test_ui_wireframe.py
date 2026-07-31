"""Tests for ui-wireframe.md generation from project.ui_panels."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import click
from click.testing import CliRunner

from brief_cmds import register_brief_commands
from ui_wireframe import (
    UI_WIREFRAME_DOC_NAME,
    UiWireframeError,
    _assert_safe_output_path,
    generate_ui_wireframe,
    project_dir_for_brief_path,
    ui_wireframe_path_for,
)


def _draft_with_panels() -> dict:
    return {
        "project": {
            "title": "Demo",
            "ui_panels": [
                {"id": "hud", "title": "HUD", "kind": "hud", "slots": ["体力"]},
                {"id": "menu", "title": "主菜单", "slots": ["开始"]},
            ],
        },
        "assets": [],
    }


def _wireframe_md() -> str:
    return "# Demo UI 示意\n\n## HUD\n\n```\n+--------+\n| 体力   |\n+--------+\n```\n"


class GenerateUiWireframeTests(unittest.TestCase):
    def test_empty_panels_returns_error_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            draft = {"project": {"title": "X"}, "assets": []}
            result = generate_ui_wireframe(draft, project_dir, config={})
            self.assertFalse(result["ok"])
            self.assertIn("ui_panels", result.get("error", ""))
            self.assertEqual(result["panel_count"], 0)
            self.assertFalse(ui_wireframe_path_for(project_dir).is_file())

    def test_success_writes_beside_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            project_dir = repo / "projects" / "demo"
            project_dir.mkdir(parents=True)
            (project_dir / "brief.draft.json").write_text(
                json.dumps(_draft_with_panels(), ensure_ascii=False), encoding="utf-8"
            )
            md = _wireframe_md()
            with patch(
                "ui_wireframe.generate_ui_wireframe_markdown",
                return_value=md,
            ):
                result = generate_ui_wireframe(_draft_with_panels(), project_dir, config={})
            self.assertTrue(result["ok"])
            self.assertEqual(result["panel_count"], 2)
            out = Path(result["path"])
            self.assertEqual(out.name, UI_WIREFRAME_DOC_NAME)
            self.assertEqual(out.parent.resolve(), project_dir.resolve())
            self.assertIn("HUD", out.read_text(encoding="utf-8"))

    def test_session_draft_brief_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            session = {"draft_brief": _draft_with_panels()}
            with patch(
                "ui_wireframe.generate_ui_wireframe_markdown",
                return_value=_wireframe_md(),
            ):
                result = generate_ui_wireframe(session, project_dir, config={})
            self.assertTrue(result["ok"])
            self.assertEqual(result["panel_count"], 2)

    def test_assert_safe_output_rejects_mismatched_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            demo = repo / "projects" / "demo"
            other = repo / "projects" / "other"
            demo.mkdir(parents=True)
            other.mkdir(parents=True)
            out = ui_wireframe_path_for(other)
            with self.assertRaises(UiWireframeError) as ctx:
                _assert_safe_output_path(out, demo, root=repo)
            self.assertIn("beside brief", str(ctx.exception).lower())

    def test_project_dir_for_brief_path(self) -> None:
        p = project_dir_for_brief_path(Path("/tmp/projects/x/brief.json"))
        self.assertEqual(p.name, "x")
        self.assertEqual(p.parent.name, "projects")


class ChatUiWireframeCmdTests(unittest.TestCase):
    def test_chat_cmd_resolves_external_brief_via_paths_for_brief_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ext_root = tmp_path / "ext-game"
            ext_root.mkdir()
            session_file = tmp_path / "sess.json"
            session_file.write_text(
                json.dumps({"id": "sess", "draft_brief": _draft_with_panels()}, ensure_ascii=False),
                encoding="utf-8",
            )
            brief_key = "external:deadbeef/brief.json"
            seen: dict[str, object] = {}

            def fake_paths_for_brief_key(key: str, workspace=None):
                seen["key"] = key
                seen["workspace"] = workspace
                return {
                    "brief": ext_root / "brief.json",
                    "project_root": ext_root,
                }

            def fake_generate(session, project_dir, *, config=None):
                seen["project_dir"] = Path(project_dir).resolve()
                return {
                    "ok": True,
                    "path": str(ext_root / "ui-wireframe.md"),
                    "panel_count": 2,
                }

            @click.group()
            def root() -> None:
                pass

            register_brief_commands(root)
            runner = CliRunner()

            with patch("project_paths.paths_for_brief_key", fake_paths_for_brief_key):
                with patch("ui_wireframe.generate_ui_wireframe", fake_generate):
                    result = runner.invoke(
                        root,
                        [
                            "brief",
                            "chat",
                            "ui-wireframe",
                            "--brief-rel",
                            brief_key,
                            "-s",
                            str(session_file),
                        ],
                        obj={"config": {}},
                    )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(seen.get("key"), brief_key)
            self.assertEqual(seen.get("project_dir"), ext_root.resolve())


class GenerateUiWireframeMarkdownTests(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        from ui_wireframe import generate_ui_wireframe_markdown

        with self.assertRaises(UiWireframeError):
            generate_ui_wireframe_markdown(
                _draft_with_panels(),
                _draft_with_panels()["project"]["ui_panels"],
                config={},
            )


if __name__ == "__main__":
    unittest.main()
