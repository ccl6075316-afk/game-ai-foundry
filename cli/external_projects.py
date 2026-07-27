"""External project registry (workspace-root external-projects.json)."""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRY_FILENAME = "external-projects.json"
REGISTRY_VERSION = 1

_EXTERNAL_BRIEF_KEY_RE = re.compile(r"^external:[^/]+/brief\.json$", re.IGNORECASE)


def registry_path(workspace: Path) -> Path:
    return Path(workspace).resolve() / REGISTRY_FILENAME


def normalize_root_abs(path: str | Path) -> str:
    return str(Path(path).resolve()).replace("\\", "/")


def detect_external_layout(root: Path) -> dict[str, Any]:
    """Detect Godot layout and brief presence under an external root."""
    root = Path(root).resolve()
    errors: list[str] = []
    godot_rel: str | None = None
    godot_abs: Path | None = None

    if (root / "project.godot").is_file():
        godot_rel = "."
        godot_abs = root
    elif (root / "game" / "project.godot").is_file():
        godot_rel = "game"
        godot_abs = root / "game"
    else:
        errors.append("godot_missing")

    brief_abs = root / "brief.json"
    has_brief = brief_abs.is_file()

    return {
        "godot_rel": godot_rel,
        "has_brief": has_brief,
        "godot_abs": godot_abs,
        "brief_abs": brief_abs,
        "errors": errors,
    }


def load_registry(workspace: Path) -> dict[str, Any]:
    path = registry_path(workspace)
    if not path.is_file():
        return {"version": REGISTRY_VERSION, "projects": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid registry: {path}")
    projects = data.get("projects")
    if not isinstance(projects, list):
        raise ValueError(f"invalid registry projects: {path}")
    return {
        "version": int(data.get("version") or REGISTRY_VERSION),
        "projects": projects,
    }


def save_registry(workspace: Path, data: dict[str, Any]) -> Path:
    path = registry_path(workspace)
    payload = {
        "version": int(data.get("version") or REGISTRY_VERSION),
        "projects": data.get("projects") or [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def list_external_projects(workspace: Path) -> list[dict[str, Any]]:
    return list(load_registry(workspace).get("projects") or [])


def get_external_by_id(workspace: Path, ext_id: str) -> dict[str, Any] | None:
    for entry in list_external_projects(workspace):
        if isinstance(entry, dict) and entry.get("id") == ext_id:
            return entry
    return None


def external_entry_for_brief_path(brief_path: Path, workspace: Path) -> dict[str, Any] | None:
    brief = Path(brief_path).resolve()
    for entry in list_external_projects(workspace):
        if not isinstance(entry, dict):
            continue
        root_abs = entry.get("root_abs")
        if not root_abs:
            continue
        root = Path(str(root_abs)).resolve()
        try:
            brief.relative_to(root)
        except ValueError:
            continue
        return entry
    return None


def _generate_id() -> str:
    return f"ext_{secrets.token_hex(4)}"


def add_external_project(workspace: Path, root: str | Path) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    normalized = normalize_root_abs(root)
    registry = load_registry(workspace)
    projects: list[dict[str, Any]] = list(registry.get("projects") or [])

    for entry in projects:
        if isinstance(entry, dict) and normalize_root_abs(entry.get("root_abs", "")) == normalized:
            return entry

    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"external root not found: {root_path}")

    layout = detect_external_layout(root_path)
    godot_rel = layout.get("godot_rel") or "."
    entry: dict[str, Any] = {
        "id": _generate_id(),
        "display_name": root_path.name or "external",
        "root_abs": normalized,
        "godot_rel": godot_rel,
        "brief_rel": "brief.json",
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    projects.append(entry)
    save_registry(workspace, {"version": REGISTRY_VERSION, "projects": projects})
    return entry


def remove_external_project(workspace: Path, ext_id: str) -> bool:
    registry = load_registry(workspace)
    projects: list[dict[str, Any]] = list(registry.get("projects") or [])
    kept = [p for p in projects if not (isinstance(p, dict) and p.get("id") == ext_id)]
    if len(kept) == len(projects):
        return False
    save_registry(workspace, {"version": REGISTRY_VERSION, "projects": kept})
    return True


def paths_for_external_entry(entry: dict[str, Any]) -> dict[str, Any]:
    root = Path(str(entry["root_abs"])).resolve()
    godot_rel = str(entry.get("godot_rel") or ".")
    brief_rel = str(entry.get("brief_rel") or "brief.json")
    if godot_rel == ".":
        godot_project = root
    else:
        godot_project = root / godot_rel
    brief = root / brief_rel
    return {
        "project_root": root,
        "brief": brief,
        "output_dir": root / "output",
        "plans_dir": root / "plans",
        "godot_project": godot_project,
        "manifest": root / "pipeline" / "manifest.json",
        "progress": root / "progress.json",
        "production": root / "production.json",
        "isolated": True,
    }


def is_external_brief_key(s: str) -> bool:
    return bool(_EXTERNAL_BRIEF_KEY_RE.match(str(s).replace("\\", "/")))


def parse_external_brief_key(s: str) -> str | None:
    key = str(s).replace("\\", "/")
    if not is_external_brief_key(key):
        return None
    return key.split(":", 1)[1].split("/", 1)[0]
