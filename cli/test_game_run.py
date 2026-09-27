"""Tests for the no-GUI quick game runner project resolution."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game_run import GameRunInputError, resolve_game_project


class GameRunResolutionTests(unittest.TestCase):
    def _repo(self, root: Path) -> Path:
        (root / "projects").mkdir()
        (root / "games").mkdir()
        return root

    def _godot_project(self, root: Path, *parts: str) -> Path:
        project = root.joinpath(*parts)
        project.mkdir(parents=True)
        (project / "project.godot").write_text("", encoding="utf-8")
        return project.resolve()

    def test_resolves_project_path_and_game_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(Path(tmp))
            project = self._godot_project(root, "projects", "fishing", "game")

            self.assertEqual(
                resolve_game_project(root / "projects" / "fishing", root=root),
                project,
            )
            self.assertEqual(resolve_game_project(project, root=root), project)

    def test_resolves_project_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(Path(tmp))
            project = self._godot_project(root, "games", "prison-demo")

            self.assertEqual(resolve_game_project("prison-demo", root=root), project)

    def test_uses_current_project_before_global_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(Path(tmp))
            current = self._godot_project(root, "projects", "current", "game")
            self._godot_project(root, "games", "other")

            self.assertEqual(
                resolve_game_project(None, root=root, cwd=current / "scenes"),
                current,
            )

    def test_uses_progress_project_when_it_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(Path(tmp))
            project = self._godot_project(root, "projects", "from-progress", "game")
            progress = root / "progress.json"
            progress.write_text(
                json.dumps({"progress_meta": {"project_path": str(project.parent)}}),
                encoding="utf-8",
            )
            self._godot_project(root, "games", "other")

            self.assertEqual(resolve_game_project(None, root=root, cwd=root), project)

    def test_ambiguous_automatic_project_lists_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(Path(tmp))
            self._godot_project(root, "projects", "one", "game")
            self._godot_project(root, "games", "two")

            with self.assertRaisesRegex(GameRunInputError, "Multiple game projects") as raised:
                resolve_game_project(None, root=root, cwd=root)

            self.assertIn("one", str(raised.exception))
            self.assertIn("two", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
