"""Resolve a Godot game project for the CLI quick-run command."""

from __future__ import annotations

import json
from pathlib import Path

from project_paths import find_default_progress, repo_root


class GameRunInputError(ValueError):
    """Raised when the requested game project cannot be resolved safely."""


def godot_project_for_root(root: Path) -> Path | None:
    """Return the Godot directory for a project root, if present."""
    root = root.expanduser().resolve()
    for candidate in (root, root / "game"):
        if (candidate / "project.godot").is_file():
            return candidate.resolve()
    return None


def discover_game_projects(root: Path | None = None) -> list[Path]:
    """Find runnable Godot projects in the repository's standard locations."""
    repo = (root or repo_root()).resolve()
    found: dict[Path, None] = {}

    for base in (repo / "projects", repo / "games"):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if not child.is_dir():
                continue
            project = godot_project_for_root(child)
            if project is not None:
                found[project] = None

    return sorted(found, key=lambda path: str(path).lower())


def _project_from_progress(progress_path: Path) -> Path | None:
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    meta = data.get("progress_meta") if isinstance(data, dict) else None
    if not isinstance(meta, dict):
        return None
    raw = str(meta.get("project_path") or "").strip()
    if not raw:
        return None
    project = Path(raw).expanduser()
    if not project.is_absolute():
        project = progress_path.parent / project
    return godot_project_for_root(project)


def _match_project_name(project: Path, requested: str) -> bool:
    name = requested.strip().lower().replace("\\", "/").rstrip("/")
    if not name:
        return False
    project_name = project.name.lower()
    root_name = project.parent.name.lower()
    return name in {project_name, root_name, f"{root_name}/game"}


def _explicit_project(requested: str, *, root: Path) -> Path:
    raw = Path(requested).expanduser()
    path_candidates = [raw]
    if not raw.is_absolute():
        path_candidates.extend((Path.cwd() / raw, root / raw))

    for candidate in path_candidates:
        if candidate.exists():
            if candidate.is_file() and candidate.name == "project.godot":
                return candidate.parent.resolve()
            project = godot_project_for_root(candidate)
            if project is not None:
                return project
            raise GameRunInputError(
                f"Godot project not found under '{candidate}'. "
                "Expected project.godot or game/project.godot."
            )

    matches = [
        project
        for project in discover_game_projects(root)
        if _match_project_name(project, requested)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        choices = "\n".join(f"  - {project}" for project in matches)
        raise GameRunInputError(f"Project name '{requested}' is ambiguous:\n{choices}")

    available = discover_game_projects(root)
    choices = "\n".join(f"  - {project}" for project in available) or "  (none)"
    raise GameRunInputError(
        f"Game project '{requested}' was not found. Available projects:\n{choices}"
    )


def _automatic_project(*, root: Path, cwd: Path) -> Path:
    current = cwd.expanduser().resolve()
    for candidate in (current, *current.parents):
        project = godot_project_for_root(candidate)
        if project is not None:
            return project
        if candidate == root:
            break

    progress_path = find_default_progress(root=root)
    if progress_path is not None:
        project = _project_from_progress(progress_path)
        if project is not None:
            return project

    available = discover_game_projects(root)
    if len(available) == 1:
        return available[0]
    if not available:
        raise GameRunInputError(
            "No runnable Godot project found. Pass one with: play --project <project>"
        )

    choices = "\n".join(f"  - {project}" for project in available)
    raise GameRunInputError(
        "Multiple game projects are available; choose one with "
        f"`play --project <project>`:\n{choices}"
    )


def resolve_game_project(
    requested: str | Path | None = None,
    *,
    root: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve an explicit project or discover the current/default game."""
    repo = (root or repo_root()).resolve()
    if requested is not None and str(requested).strip():
        return _explicit_project(str(requested), root=repo)
    return _automatic_project(root=repo, cwd=cwd or Path.cwd())
