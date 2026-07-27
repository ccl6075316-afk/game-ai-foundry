"""Tests for projects/<slug>/ path isolation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from external_projects import add_external_project
from project_paths import (
    default_paths_for_brief,
    paths_for_brief_key,
    project_root_for_brief,
    resolve_isolated_brief_for_legacy,
    slug_for_brief,
)


class ProjectPathsTests(unittest.TestCase):
    def test_isolated_brief_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = root / "projects" / "black-whistle" / "brief.json"
            brief.parent.mkdir(parents=True)
            brief.write_text("{}", encoding="utf-8")
            self.assertEqual(
                project_root_for_brief(brief, root=root),
                (root / "projects" / "black-whistle").resolve(),
            )
            paths = default_paths_for_brief(brief, root=root)
            self.assertTrue(paths["isolated"])
            self.assertEqual(paths["output_dir"], (root / "projects" / "black-whistle" / "output").resolve())
            self.assertEqual(paths["plans_dir"], (root / "projects" / "black-whistle" / "plans").resolve())
            self.assertEqual(paths["godot_project"], (root / "projects" / "black-whistle" / "game").resolve())
            self.assertEqual(
                paths["manifest"],
                (root / "projects" / "black-whistle" / "pipeline" / "manifest.json").resolve(),
            )
            self.assertEqual(slug_for_brief(brief, root=root), "black-whistle")

    def test_flat_brief_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = root / "resources" / "magic-prince-brief.json"
            brief.parent.mkdir(parents=True)
            brief.write_text("{}", encoding="utf-8")
            self.assertIsNone(project_root_for_brief(brief, root=root))
            paths = default_paths_for_brief(brief, root=root)
            self.assertFalse(paths["isolated"])
            self.assertEqual(paths["output_dir"], (root / "output" / "magic-prince-brief").resolve())
            self.assertEqual(paths["plans_dir"], (root / "plans").resolve())
            self.assertEqual(paths["godot_project"], (root / "games" / "magic-prince-brief").resolve())
            self.assertEqual(paths["manifest"], (root / "pipeline" / "magic-prince.json").resolve())


    def test_resolve_prefers_migrated_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "projects" / "black-whistle" / "brief.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "brief_meta": {
                            "migrated_from": "cli/resources/game-mrqbshf2-brief.json",
                            "legacy_names": ["game-mrqbshf2-brief.json", "game-mrqbshf2"],
                        },
                        "project": {"title": "黑哨"},
                        "assets": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            hit = resolve_isolated_brief_for_legacy(
                "resources/game-mrqbshf2-brief.json",
                root=root,
            )
            self.assertEqual(hit, dest.resolve())

    def test_external_brief_key_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "my-external"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")

            entry = add_external_project(workspace, ext_root)
            key = f"external:{entry['id']}/brief.json"
            paths = paths_for_brief_key(key, workspace)
            self.assertTrue(paths["isolated"])
            self.assertEqual(paths["project_root"], ext_root.resolve())
            self.assertEqual(paths["output_dir"], (ext_root / "output").resolve())
            self.assertEqual(paths["godot_project"], ext_root.resolve())

    def test_external_brief_abs_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "outside"
            ext_root.mkdir()
            (ext_root / "game" / "project.godot").parent.mkdir(parents=True)
            (ext_root / "game" / "project.godot").write_text("", encoding="utf-8")
            brief = ext_root / "brief.json"
            brief.write_text("{}", encoding="utf-8")

            add_external_project(workspace, ext_root)
            paths = default_paths_for_brief(brief, root=workspace)
            self.assertTrue(paths["isolated"])
            self.assertEqual(paths["godot_project"], (ext_root / "game").resolve())
            self.assertEqual(paths["output_dir"], (ext_root / "output").resolve())


if __name__ == "__main__":
    unittest.main()
