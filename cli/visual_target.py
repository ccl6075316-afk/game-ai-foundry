"""Visual target candidates — predicted in-game frames from brief (godogen Visual Target)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brief import ProjectContext, load_brief_document

VISUAL_TARGET_MANIFEST = "manifest.json"

# Composition variants (same brief contract, different key moments).
_VARIANTS: tuple[dict[str, str], ...] = (
    {
        "id": "a",
        "label": "opening_moment",
        "focus": "Opening gameplay moment at level start — player visible, environment readable.",
    },
    {
        "id": "b",
        "label": "action_beat",
        "focus": "Mid-action beat from the core loop — movement or combat energy.",
    },
    {
        "id": "c",
        "label": "session_goal",
        "focus": "Frame that best illustrates the session goal and win condition mood.",
    },
    {
        "id": "d",
        "label": "alternate_composition",
        "focus": "Same game but alternate camera framing and lighting emphasis.",
    },
)


class VisualTargetError(RuntimeError):
    pass


def _load_project(brief_path: Path) -> ProjectContext:
    data = load_brief_document(brief_path)
    raw = data.get("project", data)
    if not isinstance(raw, dict):
        raise VisualTargetError("Brief missing project section")
    return ProjectContext.from_dict(raw)


def _slug_from_brief(brief_path: Path, title: str) -> str:
    if title.strip():
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        if slug:
            return slug
    return brief_path.stem.replace(".json", "").replace("-brief", "")


def _viewport_size(project) -> str:
    vp = project.viewport or {}
    try:
        w, h = int(vp.get("width", 0)), int(vp.get("height", 0))
        if w > 0 and h > 0:
            return f"{w}x{h}"
    except (TypeError, ValueError):
        pass
    return "1280x720"


def _base_scene_description(project) -> str:
    parts = [
        f"Game title: {project.title}".strip(),
        f"Genre: {project.genre}" if project.genre else "",
        f"Description: {project.description}" if project.description else "",
        f"Art direction: {project.art_direction}" if project.art_direction else "",
        f"Gameplay loop: {project.gameplay_loop}" if project.gameplay_loop else "",
        f"Session goal: {project.session_goal}" if project.session_goal else "",
    ]
    return " ".join(p for p in parts if p)


def resolve_visual_reference_path(brief_path: Path) -> Path | None:
    """Resolve project.visual_reference relative to repo root (parent of resources/)."""
    project = _load_project(brief_path)
    ref = (project.visual_reference or "").strip()
    if not ref:
        return None
    p = Path(ref)
    if p.is_file():
        return p.resolve()
    repo_root = brief_path.resolve().parent.parent
    candidate = (repo_root / ref).resolve()
    return candidate if candidate.is_file() else None


def build_candidate_prompts(brief_path: Path, *, count: int = 3) -> list[dict[str, str]]:
    """Rule-based full-screen mock prompts from brief (no LLM)."""
    project = _load_project(brief_path)
    base = _base_scene_description(project)
    dim = (project.dimension or "2d").lower()
    style = (
        f"Full-screen in-game screenshot of a {dim} video game. "
        "Looks like real gameplay capture, not a poster or concept sheet. "
        "No UI chrome outside the game frame, no watermark, no text labels. "
        "Flat readable composition suitable as visual north star for asset generation."
    )
    n = max(1, min(count, len(_VARIANTS)))
    out: list[dict[str, str]] = []
    for variant in _VARIANTS[:n]:
        prompt = (
            f"{style} {variant['focus']} "
            f"{base} "
            "Warm cohesive palette matching art direction."
        ).strip()
        out.append(
            {
                "id": variant["id"],
                "label": variant["label"],
                "prompt_summary": variant["focus"],
                "prompt": prompt,
            }
        )
    return out


def default_output_dir(brief_path: Path) -> Path:
    project = _load_project(brief_path)
    slug = _slug_from_brief(brief_path, project.title)
    return Path("..") / "output" / slug / "visual-target"


def generate_visual_targets(
    brief_path: Path,
    output_dir: Path,
    *,
    count: int = 3,
    config: dict[str, Any],
    proxy: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate candidate PNGs + manifest."""
    from gamefactory import (
        DEFAULT_API_BASE,
        DEFAULT_SIZE,
        generate_image,
        resolve_image_proxy,
        resolve_image_setting,
    )
    import os

    brief_path = brief_path.resolve()
    project = _load_project(brief_path)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates_spec = build_candidate_prompts(brief_path, count=count)
    size = _viewport_size(project)

    model = resolve_image_setting(config, None, "model", "GAMEFACTORY_IMAGE_MODEL")
    api_key = (
        resolve_image_setting(config, None, "api_key", "GAMEFACTORY_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    api_base = resolve_image_setting(
        config, None, "api_base", "GAMEFACTORY_API_BASE", DEFAULT_API_BASE
    )
    resolved_proxy = resolve_image_proxy(config, proxy)

    if not dry_run:
        if not model or not api_key:
            raise VisualTargetError(
                "Image API not configured (config image.api_key or OPENROUTER_API_KEY)"
            )

    generated: list[dict[str, Any]] = []
    for spec in candidates_spec:
        out_path = output_dir / f"candidate_{spec['id']}.png"
        entry: dict[str, Any] = {
            **spec,
            "path": str(out_path),
            "size": size,
        }
        if dry_run:
            entry["status"] = "dry_run"
        else:
            assert model and api_key and api_base
            generate_image(
                model=model,
                prompt=spec["prompt"],
                output=out_path,
                size=size,
                api_key=api_key,
                api_base=api_base,
                proxy=resolved_proxy,
            )
            entry["status"] = "generated"
        generated.append(entry)

    manifest: dict[str, Any] = {
        "brief_path": str(brief_path),
        "slug": _slug_from_brief(brief_path, project.title),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "viewport_size": size,
        "candidates": generated,
        "selected_id": None,
        "notes": (
            "Visual Target candidates (godogen-style). "
            "User picks one → brief visual-target pick → sets project.visual_reference."
        ),
    }
    manifest_path = output_dir / VISUAL_TARGET_MANIFEST
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def load_visual_target_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "candidates" not in data:
        raise VisualTargetError("Invalid visual-target manifest")
    return data


def find_manifest_for_brief(brief_path: Path, manifest_path: Path | None) -> Path:
    if manifest_path is not None:
        if not manifest_path.is_file():
            raise VisualTargetError(f"Manifest not found: {manifest_path}")
        return manifest_path.resolve()
    default = default_output_dir(brief_path) / VISUAL_TARGET_MANIFEST
    if default.is_file():
        return default.resolve()
    raise VisualTargetError(
        f"No manifest at {default}. Run `brief visual-target generate` first."
    )


def apply_visual_target_pick(
    brief_path: Path,
    candidate_id: str,
    manifest_path: Path,
    *,
    write_brief: bool = True,
) -> dict[str, Any]:
    """Set project.visual_reference + project.visual_target on brief."""
    brief_path = brief_path.resolve()
    manifest = load_visual_target_manifest(manifest_path)
    cid = candidate_id.strip().lower()
    chosen: dict[str, Any] | None = None
    for c in manifest.get("candidates", []):
        if isinstance(c, dict) and str(c.get("id", "")).lower() == cid:
            chosen = c
            break
    if chosen is None:
        raise VisualTargetError(f"Unknown candidate id '{candidate_id}'")

    src = Path(str(chosen["path"]))
    if not src.is_file():
        raise VisualTargetError(f"Candidate image missing: {src}")

    output_dir = manifest_path.parent.resolve()
    selected_path = output_dir / "selected.png"
    selected_path.write_bytes(src.read_bytes())

    repo_root = brief_path.resolve().parent.parent
    try:
        rel_ref = selected_path.relative_to(repo_root)
        ref_str = str(rel_ref)
    except ValueError:
        ref_str = str(selected_path)

    data = load_brief_document(brief_path)
    project = data.setdefault("project", {})
    if not isinstance(project, dict):
        raise VisualTargetError("brief project section invalid")

    project["visual_reference"] = ref_str
    project["visual_target"] = {
        "selected_id": cid,
        "selected_path": ref_str,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [
            {
                "id": c.get("id"),
                "label": c.get("label"),
                "path": c.get("path"),
                "prompt_summary": c.get("prompt_summary"),
            }
            for c in manifest.get("candidates", [])
            if isinstance(c, dict)
        ],
        "manifest_path": str(manifest_path.resolve()),
    }

    manifest["selected_id"] = cid
    manifest["selected_path"] = str(selected_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if write_brief:
        brief_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "brief_path": str(brief_path),
        "visual_reference": ref_str,
        "selected_id": cid,
        "selected_image": str(selected_path),
    }
