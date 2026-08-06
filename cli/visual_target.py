"""Visual target candidates — predicted in-game frames from brief (godogen Visual Target)."""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brief import ProjectContext, load_brief_document
from plan_io import build_handoff, prompt_from_handoff, save_handoff
from roles import IMAGE_GENERATOR_ROLE, PROMPT_CRAFTER_ROLE
from shared_context import build_visual_target_context

VISUAL_TARGET_MANIFEST = "manifest.json"

# Cap concurrent craft+generate workers. Default candidate count is 3; 3 keeps
# wall-clock ≈ one image while avoiding hammering image APIs (5 often rate-limits).
VISUAL_TARGET_MAX_PARALLEL = 3

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


def _safe_scene_dir(scene_id: str) -> str:
    """Filesystem-safe unique folder for a scene id.

    Exact ``[A-Za-z0-9_-]+`` ids stay readable (``combat`` → ``combat``).
    Any other id (CJK, punctuation, path separators) gets a stable hash suffix
    so distinct ids never share one ``visual-target/`` subdirectory
    (e.g. ``foo/bar`` vs ``foo_bar``, ``combat`` vs ``combat!``).
    """
    raw = (scene_id or "").strip()
    if not raw:
        return "scene"
    if re.fullmatch(r"[A-Za-z0-9_-]+", raw):
        return raw
    ascii_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_")
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    if ascii_slug:
        return f"{ascii_slug}_{digest}"
    return f"scene_{digest}"


def find_scene_entry(project: ProjectContext, scene_id: str | None) -> dict[str, Any] | None:
    """Return the scenes[] row for scene_id, or None."""
    sid = (scene_id or "").strip()
    if not sid:
        return None
    for scene in project.scenes or []:
        if isinstance(scene, dict) and str(scene.get("id") or "").strip() == sid:
            return scene
    return None


def require_scene_entry(project: ProjectContext, scene_id: str) -> dict[str, Any]:
    entry = find_scene_entry(project, scene_id)
    if entry is None:
        known = [
            str(s.get("id") or "").strip()
            for s in (project.scenes or [])
            if isinstance(s, dict) and str(s.get("id") or "").strip()
        ]
        hint = ", ".join(known[:12]) if known else "(no project.scenes[])"
        raise VisualTargetError(
            f"Unknown scene_id {scene_id!r}. Known scenes: {hint}"
        )
    return entry


def _base_scene_description(
    project: ProjectContext,
    *,
    scene: dict[str, Any] | None = None,
) -> str:
    desc = (project.description or "").strip()
    structured = bool(getattr(project, "scenes", None) or getattr(project, "systems", None))
    if structured and len(desc) > 280:
        desc = desc[:277].rstrip() + "..."
    parts = [
        f"Game title: {project.title}".strip(),
        f"Genre: {project.genre}" if project.genre else "",
        (f"Overview: {desc}" if structured else f"Description: {desc}") if desc else "",
        f"Art direction: {project.art_direction}" if project.art_direction else "",
        f"Gameplay loop: {project.gameplay_loop}" if project.gameplay_loop else "",
        f"Session goal: {project.session_goal}" if project.session_goal else "",
    ]
    if scene:
        sid = str(scene.get("id") or "").strip()
        title = str(scene.get("title") or "").strip()
        parts.append(f"Focus screen/scene: {title or sid} (id={sid})")
        summary = str(scene.get("summary") or "").strip()
        if summary:
            parts.append(f"Scene summary: {summary}")
        notes = str(scene.get("notes") or "").strip()
        if notes:
            parts.append(f"Scene notes: {notes[:400]}")
    else:
        try:
            from brief import brief_structure_summaries

            for _source, criterion in brief_structure_summaries(
                project, max_scenes=3, max_systems=2
            ):
                parts.append(criterion)
        except Exception:
            pass
    return " ".join(p for p in parts if p)


def _resolve_ref_string(ref: str, brief_path: Path) -> Path | None:
    """Resolve a visual_reference path string to an existing file."""
    from project_paths import repo_root as foundry_root

    ref = (ref or "").strip()
    if not ref:
        return None
    p = Path(ref)
    if p.is_file():
        return p.resolve()
    root = foundry_root()
    candidate = (root / ref).resolve()
    if candidate.is_file():
        return candidate
    for base in (brief_path.resolve().parent, brief_path.resolve().parent.parent):
        alt = (base / ref).resolve()
        if alt.is_file():
            return alt
    return None


def resolve_visual_reference_path(
    brief_path: Path,
    *,
    scene_id: str | None = None,
) -> Path | None:
    """Resolve visual_reference for a scene (if given) or the global project field."""
    project = _load_project(brief_path)
    sid = (scene_id or "").strip()
    if sid:
        scene = find_scene_entry(project, sid)
        if scene is None:
            return None
        return _resolve_ref_string(str(scene.get("visual_reference") or ""), brief_path)
    return _resolve_ref_string(project.visual_reference or "", brief_path)


def resolve_visual_reference_for_asset(
    brief_path: Path,
    *,
    scene_ids: list[str] | None = None,
) -> Path | None:
    """Pick north-star image: first matching scenes[].visual_reference, else global."""
    for sid in scene_ids or []:
        path = resolve_visual_reference_path(brief_path, scene_id=str(sid).strip())
        if path is not None:
            return path
    return resolve_visual_reference_path(brief_path)


def brief_has_any_visual_reference(brief_path: Path) -> bool:
    """True when global or any scene north-star path resolves on disk."""
    if resolve_visual_reference_path(brief_path) is not None:
        return True
    project = _load_project(brief_path)
    for scene in project.scenes or []:
        if not isinstance(scene, dict):
            continue
        sid = str(scene.get("id") or "").strip()
        if sid and resolve_visual_reference_path(brief_path, scene_id=sid) is not None:
            return True
    return False


def visual_target_brief_status(brief_path: Path) -> dict[str, Any]:
    """Status payload for GUI: global + per-scene north-star readiness."""
    brief_path = brief_path.resolve()
    project = _load_project(brief_path)
    global_ref = (project.visual_reference or "").strip()
    global_path = resolve_visual_reference_path(brief_path)
    scenes_out: list[dict[str, Any]] = []
    for scene in project.scenes or []:
        if not isinstance(scene, dict):
            continue
        sid = str(scene.get("id") or "").strip()
        if not sid:
            continue
        sref = str(scene.get("visual_reference") or "").strip()
        spath = resolve_visual_reference_path(brief_path, scene_id=sid)
        scenes_out.append(
            {
                "id": sid,
                "title": str(scene.get("title") or "").strip(),
                "visual_reference": sref,
                "ready": spath is not None,
            }
        )
    return {
        "ok": True,
        "brief_path": str(brief_path),
        "visual_reference": global_ref,
        "global_ready": global_path is not None,
        "ready": brief_has_any_visual_reference(brief_path),
        "scenes": scenes_out,
    }


def get_variant(variant_id: str) -> dict[str, str]:
    for v in _VARIANTS:
        if v["id"] == variant_id:
            return dict(v)
    raise VisualTargetError(f"Unknown variant '{variant_id}'")


def variant_specs(*, count: int = 3) -> list[dict[str, str]]:
    n = max(1, min(count, len(_VARIANTS)))
    return [dict(v) for v in _VARIANTS[:n]]


def _scaffold_prompt(
    project: ProjectContext,
    variant: dict[str, str],
    *,
    scene: dict[str, Any] | None = None,
) -> str:
    from prompt_craft import (
        assemble_visual_target_prompt,
        structured_fields_from_project_scaffold,
    )

    fields = structured_fields_from_project_scaffold(project, variant, scene=scene)
    return assemble_visual_target_prompt(fields)


def build_visual_target_plan(
    brief_path: Path,
    variant: dict[str, str],
    *,
    craft: bool,
    config: dict[str, Any],
    proxy: str | None = None,
    scene: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build image-generator plan dict (scaffold or prompt-crafter LLM)."""
    project = _load_project(brief_path)
    size = _viewport_size(project)
    context = build_visual_target_context(project, variant, scene=scene)
    negative_hints = [
        "No pure white studio background.",
        "No character-only sprite on white.",
        "No poster borders, letterbox bars, or watermarks.",
        "No outer app chrome or title cards.",
    ]

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
        from prompt_craft import assemble_visual_target_prompt

        # Re-assemble with plan negatives when structured (prose path keeps as-is).
        if crafted.get("fields"):
            prompt = assemble_visual_target_prompt(
                crafted["fields"],
                extra_constraints=negative_hints,
            )
            prompt_source = str(crafted.get("prompt_source") or "llm_structured")
        else:
            prompt = str(crafted["prompt"])
            # Still append screenshot constraints for prose fallback
            prompt = (
                f"{prompt.rstrip()} Constraints: {'; '.join(negative_hints)}"
            )
            prompt_source = str(crafted.get("prompt_source") or "llm")
    else:
        from prompt_craft import (
            assemble_visual_target_prompt,
            structured_fields_from_project_scaffold,
        )

        fields = structured_fields_from_project_scaffold(
            project, variant, scene=scene
        )
        prompt = assemble_visual_target_prompt(fields, extra_constraints=negative_hints)
        prompt_source = "scaffold"

    scene_id = str((scene or {}).get("id") or "").strip()
    asset_name = (
        f"visual_target_{_safe_scene_dir(scene_id)}_{variant['id']}"
        if scene_id
        else f"visual_target_{variant['id']}"
    )
    return {
        "kind": "visual_target",
        "asset_name": asset_name,
        "asset_type": "visual_target",
        "variant": {
            "id": variant["id"],
            "label": variant["label"],
            "focus": variant["focus"],
        },
        "scene_id": scene_id or None,
        "prompt": prompt,
        "image_size": size,
        "prompt_source": prompt_source,
        "role": PROMPT_CRAFTER_ROLE,
        "consumer_role": IMAGE_GENERATOR_ROLE,
        "negative_hints": negative_hints,
        "validation": {
            "require_pure_white_background": False,
            "skip_validate": True,
        },
        "pipeline": [{"step": "generate_image"}],
        "requires_background_removal": False,
        "requires_reference_image": False,
    }


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


def default_output_dir(brief_path: Path, *, scene_id: str | None = None) -> Path:
    from project_paths import default_paths_for_brief, is_isolated_brief

    if is_isolated_brief(brief_path):
        base = default_paths_for_brief(brief_path)["output_dir"] / "visual-target"
    else:
        project = _load_project(brief_path)
        slug = _slug_from_brief(brief_path, project.title)
        base = Path("..") / "output" / slug / "visual-target"
    sid = (scene_id or "").strip()
    if sid:
        return base / _safe_scene_dir(sid)
    return base


def default_plans_dir(brief_path: Path, *, scene_id: str | None = None) -> Path:
    from project_paths import default_paths_for_brief, is_isolated_brief

    if is_isolated_brief(brief_path):
        base = default_paths_for_brief(brief_path)["plans_dir"] / "visual_target"
    else:
        slug = _slug_from_brief(brief_path, _load_project(brief_path).title)
        base = Path("..") / "plans" / f"visual_target_{slug}"
    sid = (scene_id or "").strip()
    if sid:
        return base / _safe_scene_dir(sid)
    return base


def clear_visual_target_run_artifacts(output_dir: Path, plans_root: Path) -> None:
    """Remove generate artifacts for one visual-target output scope.

    Does not delete sibling scene subdirectories under a global visual-target root.
    Does not delete ``selected.png`` (pick output): brief ``visual_reference`` may
    still point at it until the user re-picks. Image API failures are common;
    leftover partial generate runs must not block retries.
    """
    if output_dir.is_dir():
        manifest = output_dir / VISUAL_TARGET_MANIFEST
        if manifest.is_file():
            try:
                manifest.unlink()
            except OSError:
                pass
        try:
            leftovers = list(output_dir.glob("candidate_*.png"))
        except OSError:
            leftovers = []
        for path in leftovers:
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass
    if plans_root.is_dir():
        try:
            handoffs = list(plans_root.glob("candidate_*.json"))
        except OSError:
            handoffs = []
        for path in handoffs:
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass


def _rmdir_if_empty(path: Path) -> None:
    """Drop an empty directory left by a failed / cleared generate."""
    try:
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    except OSError:
        pass


def _rollback_failed_visual_target_run(
    output_dir: Path,
    plans_root: Path,
    *,
    scene_id: str | None,
) -> None:
    clear_visual_target_run_artifacts(output_dir, plans_root)
    # Scene-scoped dirs are leaf folders; remove them when empty so a failed
    # --scene run does not leave a hollow visual-target/<scene>/ behind.
    if scene_id:
        _rmdir_if_empty(output_dir)
        _rmdir_if_empty(plans_root)


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
    scene_id: str | None = None,
) -> dict[str, Any]:
    """prompt-crafter → image-generator: craft handoffs, generate candidate PNGs + manifest."""
    from gamefactory import generate_image, resolve_image_proxy
    from image_model_route import resolve_image_credentials

    brief_path = brief_path.resolve()
    project = _load_project(brief_path)
    slug = _slug_from_brief(brief_path, project.title)
    sid = (scene_id or "").strip() or None
    scene = require_scene_entry(project, sid) if sid else None
    output_dir = output_dir.resolve()
    plans_root = (
        plans_dir or default_plans_dir(brief_path, scene_id=sid)
    ).resolve()
    variants = variant_specs(count=count)
    size = _viewport_size(project)

    creds = resolve_image_credentials(config, "default")
    model = creds.model
    api_key = creds.api_key
    api_base = creds.api_base
    resolved_proxy = resolve_image_proxy(config, proxy)

    # Always start clean: prior partial/failed runs (or stale candidates) must
    # not affect this attempt or confuse list/pick for the same scope.
    clear_visual_target_run_artifacts(output_dir, plans_root)

    try:
        if not dry_run and (not model or not api_key):
            raise VisualTargetError(
                "Image API not configured (config image.api_key or OPENROUTER_API_KEY)"
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        plans_root.mkdir(parents=True, exist_ok=True)

        def _run_one(variant: dict[str, str]) -> dict[str, Any]:
            vid = variant["id"]
            plan = build_visual_target_plan(
                brief_path,
                variant,
                craft=craft,
                config=config,
                proxy=proxy,
                scene=scene,
            )
            context = build_visual_target_context(project, variant, scene=scene)
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
            return entry

        workers = max(1, min(VISUAL_TARGET_MAX_PARALLEL, len(variants)))
        by_index: dict[int, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_run_one, variant): idx
                for idx, variant in enumerate(variants)
            }
            errors: list[BaseException] = []
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    by_index[idx] = fut.result()
                except BaseException as exc:  # noqa: BLE001 — collect then re-raise
                    errors.append(exc)
            if errors:
                raise errors[0]
        generated = [by_index[i] for i in range(len(variants))]

        notes = (
            "Visual Target: prompt-crafter handoff → image-generator. "
            "Pick one → brief visual-target pick → project.visual_reference"
            + (f" or scenes[{sid}].visual_reference." if sid else ".")
        )
        manifest: dict[str, Any] = {
            "brief_path": str(brief_path),
            "slug": slug,
            "scene_id": sid,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "viewport_size": size,
            "craft": craft,
            "parallel": workers,
            "plans_dir": str(plans_root),
            "candidates": generated,
            "selected_id": None,
            "notes": notes,
        }
        manifest_path = output_dir / VISUAL_TARGET_MANIFEST
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        manifest["manifest_path"] = str(manifest_path)
        return manifest
    except Exception:
        _rollback_failed_visual_target_run(output_dir, plans_root, scene_id=sid)
        raise


def load_visual_target_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "candidates" not in data:
        raise VisualTargetError("Invalid visual-target manifest")
    return data


def _manifest_matches_brief(manifest_path: Path, brief_path: Path) -> bool:
    """True if manifest.brief_path points at this brief (or field missing/legacy)."""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    raw = str(data.get("brief_path") or "").strip()
    if not raw:
        return True
    try:
        return Path(raw).resolve() == brief_path.resolve()
    except OSError:
        return brief_path.name in raw.replace("\\", "/")


def _list_visual_target_manifests(brief_path: Path) -> list[Path]:
    """Global + per-scene manifests under the brief's visual-target output dir."""
    base = default_output_dir(brief_path)
    found: list[Path] = []
    global_m = base / VISUAL_TARGET_MANIFEST
    if global_m.is_file():
        found.append(global_m)
    if base.is_dir():
        try:
            children = list(base.iterdir())
        except OSError:
            children = []
        for child in children:
            if not child.is_dir():
                continue
            m = child / VISUAL_TARGET_MANIFEST
            if m.is_file():
                found.append(m)
    return found


def find_manifest_for_brief(
    brief_path: Path,
    manifest_path: Path | None,
    *,
    scene_id: str | None = None,
    scene_ids: list[str] | None = None,
) -> Path:
    """Locate a visual-target manifest for pick/list.

    - Explicit ``manifest_path`` wins.
    - With ``scene_id`` / ``scene_ids``: try each scene subdir in order.
    - With no scene: use the global ``visual-target/manifest.json`` only.
      Scene picks must pass ``--scene`` (GUI also pins ``--manifest`` from generate).
    """
    if manifest_path is not None:
        if not manifest_path.is_file():
            raise VisualTargetError(f"Manifest not found: {manifest_path}")
        return manifest_path.resolve()

    brief_path = brief_path.resolve()
    sids = _normalize_scene_ids(scene_id=scene_id, scene_ids=scene_ids)
    if sids:
        tried: list[str] = []
        for sid in sids:
            candidate = default_output_dir(brief_path, scene_id=sid) / VISUAL_TARGET_MANIFEST
            tried.append(str(candidate))
            if candidate.is_file():
                return candidate.resolve()
        raise VisualTargetError(
            "No manifest for scene(s) "
            + ", ".join(sids)
            + ". Tried: "
            + "; ".join(tried)
            + ". Run `brief visual-target generate --scene <id>` first."
        )

    # No --scene: prefer the global manifest only. Per-scene picks must pass
    # --scene (or --manifest). Newest-wins across scene dirs would block an
    # intentional global pick once any newer scene manifest exists.
    base = default_output_dir(brief_path)
    global_m = base / VISUAL_TARGET_MANIFEST
    if global_m.is_file() and _manifest_matches_brief(global_m, brief_path):
        return global_m.resolve()

    scene_manifests = [
        m
        for m in _list_visual_target_manifests(brief_path)
        if m.resolve() != global_m.resolve() and _manifest_matches_brief(m, brief_path)
    ]
    if scene_manifests:
        scene_manifests.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        newest = scene_manifests[0]
        try:
            hint_id = str(
                json.loads(newest.read_text(encoding="utf-8")).get("scene_id") or ""
            ).strip()
        except (OSError, json.JSONDecodeError, TypeError):
            hint_id = newest.parent.name
        raise VisualTargetError(
            f"No global manifest at {global_m}. "
            f"Found scene manifest(s); pass --scene {hint_id or '<id>'} "
            "(or --manifest <path>). Run `brief visual-target generate` for global."
        )
    raise VisualTargetError(
        f"No manifest at {global_m} (or visual-target/<scene>/). "
        "Run `brief visual-target generate` first."
    )


def _normalize_scene_ids(
    scene_id: str | None = None,
    scene_ids: list[str] | None = None,
) -> list[str]:
    """Dedupe scene ids; accept singular + plural for call-site convenience."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in list(scene_ids or []) + ([scene_id] if scene_id else []):
        sid = str(raw or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def _apply_ref_to_scenes(
    project: dict[str, Any],
    scene_ids: list[str],
    ref_str: str,
    *,
    only_empty: bool = False,
) -> tuple[list[str], list[str]]:
    """Write the same visual_reference path onto listed scenes.

    Returns ``(applied, skipped)``. With ``only_empty=True``, scenes that already
    have a *different* path are left untouched (same path counts as applied).
    """
    scenes = project.get("scenes")
    if not isinstance(scenes, list):
        scenes = []
        project["scenes"] = scenes
    index_by_id: dict[str, int] = {}
    for i, row in enumerate(scenes):
        if isinstance(row, dict):
            rid = str(row.get("id") or "").strip()
            if rid:
                index_by_id[rid] = i
    applied: list[str] = []
    skipped: list[str] = []
    missing = [sid for sid in scene_ids if sid not in index_by_id]
    if missing:
        hint = ", ".join(sorted(index_by_id)[:12]) or "(no project.scenes[])"
        raise VisualTargetError(
            f"Unknown scene_id(s) {missing!r}. Known scenes: {hint}"
        )
    for sid in scene_ids:
        i = index_by_id[sid]
        updated = dict(scenes[i])
        existing = str(updated.get("visual_reference") or "").strip()
        if only_empty and existing and existing != ref_str:
            skipped.append(sid)
            continue
        updated["visual_reference"] = ref_str
        scenes[i] = updated
        applied.append(sid)
    return applied, skipped


_MATCH_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "your",
        "you",
        "are",
        "was",
        "scene",
        "screen",
        "game",
        "play",
        "player",
        "ui",
        "hud",
        "full",
        "viewport",
        "mock",
        "image",
        "pixel",
        "art",
        "style",
        "的",
        "了",
        "和",
        "与",
        "在",
        "是",
        "为",
        "一个",
        "场景",
        "界面",
        "画面",
        "游戏",
        "玩家",
    }
)


def _match_tokens(text: str) -> set[str]:
    """Lightweight tokens for EN words + CJK uni/bigrams (offline scene matching)."""
    s = (text or "").lower()
    out: set[str] = set()
    for w in re.findall(r"[a-z0-9_]{2,}", s):
        if w not in _MATCH_STOPWORDS:
            out.add(w)
    for run in re.findall(r"[\u4e00-\u9fff]+", s):
        for ch in run:
            if ch not in _MATCH_STOPWORDS:
                out.add(ch)
        if len(run) >= 2:
            for i in range(len(run) - 1):
                bg = run[i : i + 2]
                if bg not in _MATCH_STOPWORDS:
                    out.add(bg)
    return out


def _scene_match_text(scene: dict[str, Any]) -> str:
    parts = [
        str(scene.get("id") or ""),
        str(scene.get("title") or ""),
        str(scene.get("summary") or ""),
        str(scene.get("notes") or ""),
    ]
    return " ".join(p.strip() for p in parts if str(p).strip())


def score_scene_against_prompt(scene: dict[str, Any], prompt: str) -> float:
    """0..1 overlap score between scene description and north-star prompt text."""
    scene_tok = _match_tokens(_scene_match_text(scene))
    prompt_tok = _match_tokens(prompt)
    if not scene_tok or not prompt_tok:
        return 0.0
    overlap = scene_tok & prompt_tok
    if not overlap:
        sid = str(scene.get("id") or "").strip().lower()
        title = str(scene.get("title") or "").strip().lower()
        pl = (prompt or "").lower()
        if sid and sid in pl:
            return 0.55
        if title and len(title) >= 2 and title in pl:
            return 0.5
        return 0.0
    coverage = len(overlap) / max(len(scene_tok), 1)
    jaccard = len(overlap) / max(len(scene_tok | prompt_tok), 1)
    return min(1.0, 0.65 * coverage + 0.35 * jaccard)


def match_scenes_for_north_star(
    scenes: list[dict[str, Any]],
    *,
    prompt: str,
    primary_scene_id: str | None = None,
    only_empty: bool = True,
    skip_ids: set[str] | None = None,
    min_score: float = 0.18,
    min_overlap_tokens: int = 2,
) -> list[dict[str, Any]]:
    """Suggest scenes that should share a north star (prompt × scene description).

    Returns ranked ``[{id, title, score, reason}]``. Does not write the brief.
    Empty ``visual_reference`` scenes only when ``only_empty`` (default).
    """
    skip = set(skip_ids or set())
    primary = (primary_scene_id or "").strip() or None
    prompt_tok = _match_tokens(prompt)
    primary_tok: set[str] = set()
    if primary:
        for sc in scenes:
            if isinstance(sc, dict) and str(sc.get("id") or "").strip() == primary:
                primary_tok = _match_tokens(_scene_match_text(sc))
                break

    ranked: list[dict[str, Any]] = []
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        sid = str(sc.get("id") or "").strip()
        if not sid or sid in skip:
            continue
        if only_empty and str(sc.get("visual_reference") or "").strip():
            continue
        score = score_scene_against_prompt(sc, prompt)
        # Cluster with primary: scenes similar to the source scene also qualify
        if primary and primary_tok:
            st = _match_tokens(_scene_match_text(sc))
            if st:
                cluster = len(st & primary_tok) / max(len(st), 1)
                if cluster >= 0.35:
                    score = max(score, 0.22 + 0.5 * cluster)
        scene_tok = _match_tokens(_scene_match_text(sc))
        overlap_n = len(scene_tok & prompt_tok) if prompt_tok else 0
        literal = False
        pl = (prompt or "").lower()
        if sid.lower() in pl or (
            str(sc.get("title") or "").strip().lower() in pl
            and len(str(sc.get("title") or "").strip()) >= 2
        ):
            literal = True
        if sid == primary:
            ranked.append(
                {
                    "id": sid,
                    "title": str(sc.get("title") or "").strip(),
                    "score": 1.0,
                    "reason": "primary",
                }
            )
            continue
        if score < min_score and not literal:
            continue
        if overlap_n < min_overlap_tokens and not literal and score < 0.4:
            continue
        ranked.append(
            {
                "id": sid,
                "title": str(sc.get("title") or "").strip(),
                "score": round(score, 3),
                "reason": "literal" if literal else "prompt_overlap",
            }
        )
    ranked.sort(key=lambda r: (-float(r["score"]), str(r["id"])))
    return ranked


def match_scenes_for_north_star_llm(
    scenes: list[dict[str, Any]],
    *,
    prompt: str,
    primary_scene_id: str | None = None,
    only_empty: bool = True,
    skip_ids: set[str] | None = None,
    config: dict[str, Any] | None = None,
    proxy: str | None = None,
) -> list[str] | None:
    """Optional LLM refine. Returns scene ids or None if unavailable/failed."""
    candidates = []
    skip = set(skip_ids or set())
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        sid = str(sc.get("id") or "").strip()
        if not sid or sid in skip:
            continue
        if only_empty and str(sc.get("visual_reference") or "").strip():
            continue
        candidates.append(
            {
                "id": sid,
                "title": str(sc.get("title") or "").strip(),
                "summary": str(sc.get("summary") or "").strip(),
                "notes": str(sc.get("notes") or "").strip(),
            }
        )
    if not candidates:
        return []
    try:
        from llm_config import resolve_prompt_api_settings
        from llm_json import try_parse_llm_json_object
        from proxy_utils import http_post
    except ImportError:
        return None

    api = resolve_prompt_api_settings(config or {}, proxy=proxy)
    if not api.get("api_key"):
        return None

    system = (
        "You match one gameplay north-star screenshot prompt to brief scenes. "
        "Return JSON only: {\"scene_ids\": [\"...\"]}. "
        "Include a scene only if this single image is a good style/layout anchor for it. "
        "Do NOT force-fit contrasting screens (e.g. calm hub vs intense combat vs aquarium). "
        "When unsure, omit the scene. Empty list is ok."
    )
    user = json.dumps(
        {
            "primary_scene_id": primary_scene_id,
            "north_star_prompt": (prompt or "")[:2500],
            "scenes": candidates,
        },
        ensure_ascii=False,
    )
    try:
        resp = http_post(
            api.get("proxy"),
            f"{str(api['api_base']).rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": str(api["prompt_model"]),
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60,
        )
        if resp.status_code != 200:
            return None
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = try_parse_llm_json_object(str(content))
        if not isinstance(parsed, dict):
            return None
        raw_ids = parsed.get("scene_ids")
        if not isinstance(raw_ids, list):
            return None
        allowed = {c["id"] for c in candidates}
        out: list[str] = []
        seen: set[str] = set()
        for item in raw_ids:
            sid = str(item or "").strip()
            if sid in allowed and sid not in seen:
                seen.add(sid)
                out.append(sid)
        return out
    except Exception:
        return None


def suggest_auto_match_scene_ids(
    project: dict[str, Any],
    *,
    prompt: str,
    primary_scene_id: str | None = None,
    skip_ids: set[str] | None = None,
    config: dict[str, Any] | None = None,
    proxy: str | None = None,
    use_llm: bool = True,
) -> tuple[list[str], str]:
    """Return (scene_ids to assign, method) — llm | heuristic."""
    scenes = project.get("scenes") if isinstance(project.get("scenes"), list) else []
    scenes = [s for s in scenes if isinstance(s, dict)]
    skip = set(skip_ids or set())
    primary = (primary_scene_id or "").strip() or None

    if use_llm:
        llm_ids = match_scenes_for_north_star_llm(
            scenes,
            prompt=prompt,
            primary_scene_id=primary,
            only_empty=True,
            skip_ids=skip,
            config=config,
            proxy=proxy,
        )
        # Non-empty LLM answer wins; empty list falls through to heuristic
        # (conservative models often return [] and would otherwise skip matches).
        if llm_ids:
            return llm_ids, "llm"

    ranked = match_scenes_for_north_star(
        scenes,
        prompt=prompt,
        primary_scene_id=primary,
        only_empty=True,
        skip_ids=skip,
    )
    return [str(r["id"]) for r in ranked if r.get("id") != primary], "heuristic"


def assign_visual_reference_to_scenes(
    brief_path: Path,
    *,
    scene_ids: list[str],
    from_scene: str | None = None,
    from_global: bool = False,
    ref: str | None = None,
    write_brief: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Share one existing north-star path across scenes (same path string, no file copy).

    By default only fills empty scene refs (``overwrite=False``) so a prior
    scene-specific pick is not silently replaced.
    """
    brief_path = brief_path.resolve()
    targets = _normalize_scene_ids(scene_ids=scene_ids)
    if not targets:
        raise VisualTargetError("assign requires at least one --scene")

    data = load_brief_document(brief_path)
    project = data.setdefault("project", {})
    if not isinstance(project, dict):
        raise VisualTargetError("brief project section invalid")

    ref_str = ""
    source = ""
    explicit = (ref or "").strip()
    src_scene = (from_scene or "").strip() or None
    if explicit:
        resolved = _resolve_ref_string(explicit, brief_path)
        if resolved is None:
            raise VisualTargetError(f"Reference image not found: {explicit}")
        from project_paths import repo_root as foundry_root

        root = foundry_root()
        try:
            ref_str = str(resolved.relative_to(root)).replace("\\", "/")
        except ValueError:
            ref_str = str(resolved)
        source = "ref"
    elif src_scene:
        resolved = resolve_visual_reference_path(brief_path, scene_id=src_scene)
        if resolved is None:
            raise VisualTargetError(
                f"Source scene {src_scene!r} has no usable visual_reference"
            )
        # Prefer the path string already stored on the source scene (stable share).
        for row in project.get("scenes") or []:
            if isinstance(row, dict) and str(row.get("id") or "").strip() == src_scene:
                stored = str(row.get("visual_reference") or "").strip()
                if stored:
                    ref_str = stored
                break
        if not ref_str:
            ref_str = str(resolved).replace("\\", "/")
        source = f"scene:{src_scene}"
    elif from_global:
        resolved = resolve_visual_reference_path(brief_path)
        if resolved is None:
            raise VisualTargetError("project.visual_reference is empty or missing on disk")
        stored = str(project.get("visual_reference") or "").strip()
        ref_str = stored or str(resolved).replace("\\", "/")
        source = "global"
    else:
        raise VisualTargetError(
            "assign needs --from-scene, --from-global, or --ref"
        )

    applied, skipped = _apply_ref_to_scenes(
        project, targets, ref_str, only_empty=not overwrite
    )
    # Do not seed global from assign — scene refs alone satisfy soft-gates,
    # and seeding would make unrelated scene_ids assets fall back to the wrong image.

    if write_brief:
        brief_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return {
        "brief_path": str(brief_path),
        "visual_reference": ref_str,
        "scene_ids": applied,
        "skipped_scene_ids": skipped,
        "source": source,
    }


def apply_visual_target_pick(
    brief_path: Path,
    candidate_id: str,
    manifest_path: Path,
    *,
    write_brief: bool = True,
    scene_id: str | None = None,
    scene_ids: list[str] | None = None,
    auto_match_scenes: bool = True,
    config: dict[str, Any] | None = None,
    proxy: str | None = None,
) -> dict[str, Any]:
    """Set global and/or scene-scoped visual_reference from a candidate.

    Multiple ``scene_ids`` receive the *same* path string (shared north star).
    When ``auto_match_scenes`` (default), also assign empty scenes whose
    title/summary/notes match the candidate prompt (LLM if available, else heuristic).
    """
    brief_path = brief_path.resolve()
    manifest = load_visual_target_manifest(manifest_path)
    # Generate-time scope (must survive auto_match — do not flip global→scene).
    generate_scene_id = str(manifest.get("scene_id") or "").strip() or None
    raw_gen_ids = manifest.get("scene_ids")
    generate_scene_ids = (
        _normalize_scene_ids(
            scene_ids=[str(x) for x in raw_gen_ids if str(x).strip()]
        )
        if isinstance(raw_gen_ids, list)
        else []
    )
    # Prefer explicit CLI args; else restore full scene_ids / scene_id from manifest.
    sids = _normalize_scene_ids(scene_id=scene_id, scene_ids=scene_ids)
    if not sids:
        if generate_scene_ids:
            sids = list(generate_scene_ids)
        elif generate_scene_id:
            sids = [generate_scene_id]
    sid = sids[0] if sids else None
    pick_targets = list(sids)
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

    from project_paths import repo_root as foundry_root

    root = foundry_root()
    try:
        rel_ref = selected_path.relative_to(root)
        ref_str = str(rel_ref).replace("\\", "/")
    except ValueError:
        ref_str = str(selected_path)

    data = load_brief_document(brief_path)
    project = data.setdefault("project", {})
    if not isinstance(project, dict):
        raise VisualTargetError("brief project section invalid")

    target_meta = {
        "selected_id": cid,
        "selected_path": ref_str,
        "image_size": manifest.get("viewport_size"),
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "scene_id": sid,
        "scene_ids": pick_targets,
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

    if pick_targets:
        # Explicit / generate-scoped pick always writes listed scenes (user intent).
        _apply_ref_to_scenes(project, pick_targets, ref_str, only_empty=False)
        # Do NOT seed project.visual_reference from a scene pick — soft-gates
        # already accept any scene ref, and seeding makes other scene_ids assets
        # fall back to the wrong north-star for style img2img.
        project["visual_target"] = target_meta
    else:
        project["visual_reference"] = ref_str
        project["visual_target"] = target_meta

    auto_matched: list[str] = []
    match_method = ""
    if auto_match_scenes and isinstance(project.get("scenes"), list):
        prompt_text = " ".join(
            str(x).strip()
            for x in (
                chosen.get("prompt"),
                chosen.get("prompt_summary"),
                chosen.get("label"),
            )
            if str(x or "").strip()
        )
        matched, match_method = suggest_auto_match_scene_ids(
            project,
            prompt=prompt_text,
            primary_scene_id=sid,
            skip_ids=set(pick_targets),
            config=config,
            proxy=proxy,
            use_llm=True,
        )
        empty_ok = [mid for mid in matched if mid not in pick_targets]
        if empty_ok:
            applied_auto, _skipped = _apply_ref_to_scenes(
                project, empty_ok, ref_str, only_empty=True
            )
            auto_matched = applied_auto
            if auto_matched:
                # Keep scene_ids = intentional pick scope; auto_match is separate
                # so CLI/GUI do not treat a global pick as scene-scoped.
                target_meta["auto_matched_scene_ids"] = auto_matched
                target_meta["auto_match_method"] = match_method
                project["visual_target"] = target_meta

    manifest["selected_id"] = cid
    manifest["selected_path"] = str(selected_path)
    # Keep generate scope stable: global generate stays global on remanifest.
    if generate_scene_ids or generate_scene_id:
        manifest["scene_id"] = generate_scene_id or generate_scene_ids[0]
        manifest["scene_ids"] = generate_scene_ids or [generate_scene_id]
    else:
        manifest["scene_id"] = None
        manifest["scene_ids"] = []
    if auto_matched:
        manifest["auto_matched_scene_ids"] = auto_matched
        manifest["auto_match_method"] = match_method
    else:
        # Clear stale auto_match from a previous pick on the same manifest.
        manifest.pop("auto_matched_scene_ids", None)
        manifest.pop("auto_match_method", None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if write_brief:
        brief_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "brief_path": str(brief_path),
        "visual_reference": ref_str,
        "selected_id": cid,
        "selected_image": str(selected_path),
        "scene_id": sid,
        # Intentional pick/generate scope only — not auto_matched ids.
        "scene_ids": pick_targets,
        "auto_matched_scene_ids": auto_matched,
        "auto_match_method": match_method or None,
    }
