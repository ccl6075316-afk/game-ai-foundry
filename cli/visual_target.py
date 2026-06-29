"""Visual target candidates — predicted in-game frames from brief (godogen Visual Target)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brief import ProjectContext, load_brief_document
from plan_io import build_handoff, prompt_from_handoff, save_handoff
from roles import IMAGE_GENERATOR_ROLE, PROMPT_CRAFTER_ROLE
from shared_context import build_visual_target_context

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


def get_variant(variant_id: str) -> dict[str, str]:
    for v in _VARIANTS:
        if v["id"] == variant_id:
            return dict(v)
    raise VisualTargetError(f"Unknown variant '{variant_id}'")


def variant_specs(*, count: int = 3) -> list[dict[str, str]]:
    n = max(1, min(count, len(_VARIANTS)))
    return [dict(v) for v in _VARIANTS[:n]]


def _scaffold_prompt(project: ProjectContext, variant: dict[str, str]) -> str:
    base = _base_scene_description(project)
    dim = (project.dimension or "2d").lower()
    style = (
        f"Full-screen in-game screenshot of a {dim} video game. "
        "Looks like real gameplay capture, not a poster or concept sheet. "
        "No UI chrome outside the game frame, no watermark, no text labels. "
        "Flat readable composition suitable as visual north star for asset generation."
    )
    return (
        f"{style} {variant['focus']} "
        f"{base} "
        "Warm cohesive palette matching art direction."
    ).strip()


def build_visual_target_plan(
    brief_path: Path,
    variant: dict[str, str],
    *,
    craft: bool,
    config: dict[str, Any],
    proxy: str | None = None,
) -> dict[str, Any]:
    """Build image-generator plan dict (scaffold or prompt-crafter LLM)."""
    project = _load_project(brief_path)
    size = _viewport_size(project)
    context = build_visual_target_context(project, variant)

    if craft:
        from llm_config import resolve_prompt_api_settings
        from prompt_craft import PromptCraftError, craft_visual_target_prompt

        api = resolve_prompt_api_settings(config, proxy=proxy)
        if not api.get("api_key"):
            raise VisualTargetError(
                "prompt-crafter requires API key (config.host/prompt or OPENROUTER_API_KEY). "
                "Use --no-craft for rule-based prompts."
            )
        try:
            crafted = craft_visual_target_prompt(
                context=context,
                model=str(api["prompt_model"]),
                api_key=str(api["api_key"]),
                api_base=str(api["api_base"]),
                proxy=api.get("proxy"),
            )
        except PromptCraftError as exc:
            raise VisualTargetError(str(exc)) from exc
        prompt = crafted["prompt"]
        prompt_source = "llm"
    else:
        prompt = _scaffold_prompt(project, variant)
        prompt_source = "scaffold"

    return {
        "kind": "visual_target",
        "asset_name": f"visual_target_{variant['id']}",
        "asset_type": "visual_target",
        "variant": {
            "id": variant["id"],
            "label": variant["label"],
            "focus": variant["focus"],
        },
        "prompt": prompt,
        "image_size": size,
        "prompt_source": prompt_source,
        "role": PROMPT_CRAFTER_ROLE,
        "consumer_role": IMAGE_GENERATOR_ROLE,
        "negative_hints": [
            "No pure white studio background.",
            "No character-only sprite on white.",
            "No poster borders or watermarks.",
        ],
        "validation": {
            "require_pure_white_background": False,
            "skip_validate": True,
        },
        "pipeline": [{"step": "generate_image"}],
        "requires_background_removal": False,
        "requires_reference_image": False,
    }


def default_plans_dir(brief_path: Path) -> Path:
    slug = _slug_from_brief(brief_path, _load_project(brief_path).title)
    return Path("..") / "plans" / f"visual_target_{slug}"


def handoff_path_for_variant(plans_dir: Path, variant_id: str) -> Path:
    return plans_dir / f"candidate_{variant_id}.json"


def build_candidate_prompts(brief_path: Path, *, count: int = 3) -> list[dict[str, str]]:
    """Rule-based prompts (scaffold only) — used by tests and --no-craft."""
    project = _load_project(brief_path)
    out: list[dict[str, str]] = []
    for variant in variant_specs(count=count):
        out.append(
            {
                "id": variant["id"],
                "label": variant["label"],
                "prompt_summary": variant["focus"],
                "prompt": _scaffold_prompt(project, variant),
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
    craft: bool = True,
    plans_dir: Path | None = None,
) -> dict[str, Any]:
    """prompt-crafter → image-generator: craft handoffs, generate candidate PNGs + manifest."""
    from gamefactory import (
        DEFAULT_API_BASE,
        generate_image,
        resolve_image_proxy,
        resolve_image_setting,
    )
    import os

    brief_path = brief_path.resolve()
    project = _load_project(brief_path)
    slug = _slug_from_brief(brief_path, project.title)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    plans_root = (plans_dir or default_plans_dir(brief_path)).resolve()
    plans_root.mkdir(parents=True, exist_ok=True)

    variants = variant_specs(count=count)
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

    if not dry_run and (not model or not api_key):
        raise VisualTargetError(
            "Image API not configured (config image.api_key or OPENROUTER_API_KEY)"
        )

    generated: list[dict[str, Any]] = []
    for variant in variants:
        vid = variant["id"]
        plan = build_visual_target_plan(
            brief_path, variant, craft=craft, config=config, proxy=proxy
        )
        context = build_visual_target_context(project, variant)
        handoff = build_handoff(plan, context=context)
        handoff_path = handoff_path_for_variant(plans_root, vid)
        save_handoff(handoff_path, handoff)

        out_path = output_dir / f"candidate_{vid}.png"
        prompt = prompt_from_handoff(handoff)
        entry: dict[str, Any] = {
            "id": vid,
            "label": variant["label"],
            "prompt_summary": variant["focus"],
            "prompt": prompt,
            "prompt_source": plan.get("prompt_source", "scaffold"),
            "handoff_path": str(handoff_path),
            "path": str(out_path),
            "size": plan.get("image_size", size),
        }
        if dry_run:
            entry["status"] = "dry_run"
        else:
            assert model and api_key and api_base
            generate_image(
                model=model,
                prompt=prompt,
                output=out_path,
                size=str(plan.get("image_size", size)),
                api_key=api_key,
                api_base=api_base,
                proxy=resolved_proxy,
            )
            entry["status"] = "generated"
        generated.append(entry)

    manifest: dict[str, Any] = {
        "brief_path": str(brief_path),
        "slug": slug,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "viewport_size": size,
        "craft": craft,
        "plans_dir": str(plans_root),
        "candidates": generated,
        "selected_id": None,
        "notes": (
            "Visual Target: prompt-crafter handoff → image-generator. "
            "Pick one → brief visual-target pick → project.visual_reference."
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
        "image_size": manifest.get("viewport_size"),
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
