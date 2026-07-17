"""Suggest targeted pipeline reset/run commands from manifest + asset names."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest_tasks(manifest_path: Path) -> list[dict[str, Any]]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    tasks = data.get("tasks")
    return [t for t in tasks if isinstance(t, dict)] if isinstance(tasks, list) else []


def _pick_reset_task_id(tasks: list[dict[str, Any]], asset: str) -> str | None:
    """Prefer failed task for asset; else image.generate; else first matching."""
    asset_l = asset.strip().lower()
    matched = [
        t
        for t in tasks
        if str(t.get("asset") or "").strip().lower() == asset_l
        or str(t.get("id") or "").lower().startswith(f"{asset_l}.")
    ]
    if not matched:
        # fuzzy: id contains asset
        matched = [t for t in tasks if asset_l in str(t.get("id") or "").lower()]
    if not matched:
        return None
    failed = [t for t in matched if str(t.get("status") or "") == "failed"]
    pool = failed or matched
    for prefer in (".image.generate", ".prompt", ".video.generate", ".assemble"):
        for t in pool:
            tid = str(t.get("id") or "")
            if prefer in tid:
                return tid
    return str(pool[0].get("id") or "") or None


def suggest_retry_commands(
    *,
    manifest_rel: str,
    asset_names: list[str],
    jobs: int = 2,
) -> list[str]:
    """Return whitelisted CLI lines (python gamefactory.py …)."""
    # manifest_rel like ../pipeline/slug.json (from cli cwd) or pipeline/slug.json
    candidates = [
        Path(manifest_rel),
        Path("..") / manifest_rel.lstrip("./"),
    ]
    # also accept repo-relative pipeline/foo.json from cli/
    if not manifest_rel.startswith(".."):
        candidates.append(Path("..") / manifest_rel)

    manifest_path: Path | None = None
    for c in candidates:
        if c.is_file():
            manifest_path = c
            break
    if not manifest_path:
        return [
            f"python gamefactory.py pipeline status --manifest {manifest_rel} --json",
            f"python gamefactory.py pipeline run --manifest {manifest_rel} --jobs {jobs}",
        ]

    tasks = load_manifest_tasks(manifest_path)
    # normalize path for commands (prefer ../pipeline/…)
    try:
        rel = manifest_path.as_posix()
        if not rel.startswith(".."):
            rel = f"../{manifest_path.name}" if manifest_path.parent.name != "pipeline" else f"../pipeline/{manifest_path.name}"
            if manifest_path.parent.name == "pipeline":
                rel = f"../pipeline/{manifest_path.name}"
    except Exception:
        rel = manifest_rel

    cmds: list[str] = [
        f"python gamefactory.py pipeline status --manifest {rel} --json",
    ]
    seen: set[str] = set()
    for asset in asset_names:
        name = str(asset).strip()
        if not name:
            continue
        tid = _pick_reset_task_id(tasks, name)
        if not tid or tid in seen:
            continue
        seen.add(tid)
        cmds.append(
            f"python gamefactory.py pipeline reset --manifest {rel} --task-id {tid} --cascade"
        )
    if seen:
        cmds.append(f"python gamefactory.py pipeline run --manifest {rel} --jobs {jobs}")
    else:
        cmds.append(f"python gamefactory.py pipeline run --manifest {rel} --jobs {jobs}")
    return cmds
