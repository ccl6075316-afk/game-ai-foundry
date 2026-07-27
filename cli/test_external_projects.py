"""Tests for external project registry and layout detection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from external_projects import (
    add_external_project,
    detect_external_layout,
    list_external_projects,
    load_registry,
    normalize_root_abs,
    paths_for_external_entry,
    registry_path,
    remove_external_project,
    save_registry,
)


class ExternalProjectsTests(unittest.TestCase):
    def test_detect_root_as_godot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fish2d"
            root.mkdir()
            (root / "project.godot").write_text("", encoding="utf-8")
            layout = detect_external_layout(root)
            self.assertEqual(layout["godot_rel"], ".")
            self.assertEqual(layout["godot_abs"], root.resolve())
            self.assertFalse(layout["has_brief"])
            self.assertEqual(layout["errors"], [])

    def test_detect_game_subdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "foundry-style"
            game = root / "game"
            game.mkdir(parents=True)
            (game / "project.godot").write_text("", encoding="utf-8")
            layout = detect_external_layout(root)
            self.assertEqual(layout["godot_rel"], "game")
            self.assertEqual(layout["godot_abs"], game.resolve())
            self.assertFalse(layout["has_brief"])
            self.assertEqual(layout["errors"], [])

    def test_detect_godot_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "empty"
            root.mkdir()
            layout = detect_external_layout(root)
            self.assertIsNone(layout["godot_rel"])
            self.assertIn("godot_missing", layout["errors"])

    def test_detect_has_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "with-brief"
            root.mkdir()
            (root / "brief.json").write_text("{}", encoding="utf-8")
            layout = detect_external_layout(root)
            self.assertTrue(layout["has_brief"])
            self.assertEqual(layout["brief_abs"], (root / "brief.json").resolve())

    def test_add_and_dedupe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "external-game"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")

            first = add_external_project(workspace, ext_root)
            self.assertTrue(first["id"].startswith("ext_"))
            self.assertEqual(normalize_root_abs(first["root_abs"]), normalize_root_abs(ext_root))

            second = add_external_project(workspace, ext_root)
            self.assertEqual(second["id"], first["id"])
            self.assertEqual(len(list_external_projects(workspace)), 1)

            reg = load_registry(workspace)
            self.assertEqual(reg["version"], 1)
            self.assertEqual(len(reg["projects"]), 1)

    def test_remove_does_not_delete_disk_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "keep-me"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")
            (ext_root / "brief.json").write_text("{}", encoding="utf-8")

            entry = add_external_project(workspace, ext_root)
            remove_external_project(workspace, entry["id"])

            self.assertEqual(list_external_projects(workspace), [])
            self.assertTrue((ext_root / "project.godot").is_file())
            self.assertTrue((ext_root / "brief.json").is_file())

    def test_paths_for_external_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ext-proj"
            game = root / "game"
            game.mkdir(parents=True)
            (game / "project.godot").write_text("", encoding="utf-8")

            entry = {
                "id": "ext_deadbeef",
                "display_name": "ext-proj",
                "root_abs": normalize_root_abs(root),
                "godot_rel": "game",
                "brief_rel": "brief.json",
                "added_at": "2026-07-27T00:00:00+00:00",
            }
            paths = paths_for_external_entry(entry)
            self.assertTrue(paths["isolated"])
            self.assertEqual(paths["project_root"], root.resolve())
            self.assertEqual(paths["brief"], (root / "brief.json").resolve())
            self.assertEqual(paths["output_dir"], (root / "output").resolve())
            self.assertEqual(paths["plans_dir"], (root / "plans").resolve())
            self.assertEqual(paths["godot_project"], game.resolve())
            self.assertEqual(paths["manifest"], (root / "pipeline" / "manifest.json").resolve())
            self.assertEqual(paths["progress"], (root / "progress.json").resolve())
            self.assertEqual(paths["production"], (root / "production.json").resolve())

    def test_normalize_root_abs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a" / "b"
            p.mkdir(parents=True)
            normalized = normalize_root_abs(p)
            self.assertNotIn("\\", normalized)
            self.assertTrue(Path(normalized).is_absolute())

    def test_registry_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            data = {"version": 1, "projects": [{"id": "ext_abc", "root_abs": "/tmp/x"}]}
            save_registry(workspace, data)
            self.assertTrue(registry_path(workspace).is_file())
            loaded = load_registry(workspace)
            self.assertEqual(loaded["projects"][0]["id"], "ext_abc")


if __name__ == "__main__":
    unittest.main()
