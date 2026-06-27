"""Assets manifest — brief-driven usage contract + pipeline stage ledger."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brief import (
    AssetSpec,
    AssetType,
    ProjectContext,
    load_brief,
    load_brief_full,
    resolve_animation_loop,
    resolve_animation_name,
    resolve_generate_method,
    validate_brief_for_export,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLI_DIR = _REPO_ROOT / "cli"
MANIFEST_VERSION = 1


def _rel_to_repo(path: Path, *, base: Path | None = None) -> str:
    root = base or _REPO_ROOT
    path = path.resolve()
    try:
        return str(path.relative_to(root.resolve()))
    except ValueError:
        return str(path)

# Pipeline step → stage metadata (paths come from task artifacts).
_STEP_STAGE: dict[str, dict[str, Any]] = {
    "prompt.craft": {
        "stage": "prompt.plan",
        "role": "pipeline_intermediate",
        "artifact_key": "plan",
        "next_stage": "image.generate",
        "next_consumer": "image-generator",
    },
    "image.generate": {
        "stage": "image.raw",
        "role": "pipeline_intermediate",
        "artifact_key": "output",
        "next_stage": "image.trim",
        "next_consumer": "orchestrator",
        "notes": "Pure-white validate must pass before trim/matte.",
    },
    "image.trim": {
        "stage": "image.trimmed",
        "role": "pipeline_intermediate",
        "artifact_key": "output",
        "next_stage": "image.remove-bg",
        "next_consumer": "orchestrator",
    },
    "image.remove-bg": {
        "stage": "image.nobg",
        "role": "gameplay_ready",
        "artifact_key": "output",
        "next_stage": "godot.assemble",
        "next_consumer": "godot-assembler",
    },
    "image.slice": {
        "stage": "image.tiles",
        "role": "gameplay_ready",
        "artifact_key": "output_dir",
        "next_stage": "godot.assemble",
        "next_consumer": "godot-assembler",
    },
    "video.generate": {
        "stage": "video.source",
        "role": "pipeline_intermediate",
        "artifact_key": "output",
        "next_stage": "video.split-frames",
        "next_consumer": "orchestrator",
        "notes": "Reference still for i2v must be *_raw.png — never trimmed.",
    },
    "video.split-frames": {
        "stage": "video.frames",
        "role": "pipeline_intermediate",
        "artifact_key": "output_dir",
        "next_stage": "video.matte-frames",
        "next_consumer": "orchestrator",
    },
    "video.matte-frames": {
        "stage": "video.frames_nobg",
        "role": "gameplay_ready",
        "artifact_key": "output_dir",
        "next_stage": "godot.assemble",
        "next_consumer": "godot-assembler",
    },
    "godot.assemble": {
        "stage": "godot.imported",
        "role": "runtime",
        "artifact_key": "project_path",
        "next_stage": None,
        "next_consumer": "godot-developer",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _brief_asset_entry(spec: AssetSpec) -> dict[str, Any]:
    loop = resolve_animation_loop(spec)
    return {
        "name": spec.name,
        "type": spec.type.value,
        "usage": spec.usage,
        "usage_description": spec.usage_description,
        "generate_method": resolve_generate_method(spec),
        "display_size": spec.display_size,
        "description": spec.description,
        "reference_asset": spec.reference_asset,
        "animation_method": spec.animation_method if spec.action else "",
        "animation_name": resolve_animation_name(spec) if spec.action else "",
        "animation_loop": loop if spec.action else None,
        "action": spec.action,
    }


def build_assets_manifest(
    brief_path: Path,
    *,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Initialize assets manifest from a validated brief."""
    brief_path = brief_path.resolve()
    project, assets, graphs = load_brief_full(brief_path)
    validate_brief_for_export(project, assets, animation_graphs=graphs)

    if output_dir is None:
        output_dir = _REPO_ROOT / "output" / brief_path.stem
    output_dir = output_dir.resolve()

    return {
        "manifest_version": MANIFEST_VERSION,
        "updated_at": _utc_now(),
        "brief": _rel_to_repo(brief_path),
        "output_dir": _rel_to_repo(output_dir),
        "project": {
            "title": project.title,
            "description": project.description,
            "art_direction": project.art_direction,
            "dimension": project.dimension,
        },
        "assets": {spec.name: {"brief": _brief_asset_entry(spec), "stages": [], "runtime": None} for spec in assets},
    }


def save_assets_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _utc_now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_assets_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("manifest_version") != MANIFEST_VERSION:
        raise ValueError(f"Unsupported assets manifest version in {path}")
    return data


def assets_manifest_path_for_output(output_dir: Path) -> Path:
    return output_dir.resolve() / "assets-manifest.json"


def _artifact_to_repo_rel(artifact_path: str) -> str:
    resolved = (_CLI_DIR / artifact_path).resolve()
    return _rel_to_repo(resolved)


def _stage_for_background(spec_entry: dict[str, Any], step: str, meta: dict[str, Any]) -> dict[str, Any]:
    """Backgrounds skip trim/matte — adjust next_stage hints."""
    out = dict(meta)
    if step == "image.generate":
        out["next_stage"] = None
        out["next_consumer"] = "godot-assembler"
        out["role"] = "gameplay_ready"
    return out


def apply_task_to_assets_manifest(
    assets_manifest: dict[str, Any],
    task: dict[str, Any],
    *,
    brief_assets: dict[str, AssetSpec] | None = None,
) -> bool:
    """Record a completed pipeline task as a stage entry. Returns True if updated."""
    if task.get("status") != "done":
        return False

    asset_name = str(task.get("asset", ""))
    step = str(task.get("step", ""))
    if not asset_name or asset_name not in assets_manifest.get("assets", {}):
        return False

    meta = _STEP_STAGE.get(step)
    if not meta:
        return False

    artifacts = task.get("artifacts") or {}
    art_key = meta.get("artifact_key", "output")
    art_rel = artifacts.get(art_key) or artifacts.get("output") or artifacts.get("output_dir")
    if not art_rel:
        return False

    entry = assets_manifest["assets"][asset_name]
    spec_meta = entry.get("brief") or {}
    stage_meta = dict(meta)
    if spec_meta.get("type") == "background" and step.startswith("image."):
        stage_meta = _stage_for_background(spec_meta, step, stage_meta)

    stage_record: dict[str, Any] = {
        "task_id": task.get("id"),
        "stage": stage_meta["stage"],
        "status": "done",
        "path_cli": art_rel,
        "path_repo": _artifact_to_repo_rel(art_rel),
        "role": stage_meta.get("role"),
        "next_stage": stage_meta.get("next_stage"),
        "next_consumer": stage_meta.get("next_consumer"),
    }
    if stage_meta.get("notes"):
        stage_record["notes"] = stage_meta["notes"]
    if brief_assets and asset_name in brief_assets:
        spec = brief_assets[asset_name]
        stage_record["usage"] = spec.usage
        if step == "video.matte-frames" or (step == "image.remove-bg" and spec.type == AssetType.CHARACTER):
            stage_record["clip_name"] = resolve_animation_name(spec) if spec.action else "idle"
            stage_record["loop"] = resolve_animation_loop(spec) if spec.action else None

    stages: list[dict[str, Any]] = entry.setdefault("stages", [])
    stages[:] = [s for s in stages if s.get("task_id") != task.get("id")]
    stages.append(stage_record)
    return True


def invalidate_asset_stages_from_task(
    assets_manifest: dict[str, Any],
    task_id: str,
    *,
    cascade_ids: list[str] | None = None,
) -> None:
    """Remove stage records when pipeline tasks are reset."""
    drop = {task_id}
    if cascade_ids:
        drop.update(cascade_ids)
    for entry in assets_manifest.get("assets", {}).values():
        stages = entry.get("stages") or []
        entry["stages"] = [s for s in stages if s.get("task_id") not in drop]
        if any(s.get("task_id") in drop for s in stages):
            entry["runtime"] = None


def apply_godot_assemble_runtime(
    assets_manifest: dict[str, Any],
    *,
    assemble_result: dict[str, Any],
    godot_plan: dict[str, Any],
) -> None:
    """After godot assemble, attach res:// paths and clip bindings."""
    project_path = assemble_result.get("project_path", "")
    for anim in assemble_result.get("animations") or []:
        if not isinstance(anim, dict):
            continue
        asset_key = str(anim.get("merged_from", anim.get("asset", ""))).split(",")[0].strip()
        if "merged_from" in anim:
            character = str(godot_plan.get("character_asset", ""))
            if character and character in assets_manifest.get("assets", {}):
                assets_manifest["assets"][character]["runtime"] = {
                    "project_path": project_path,
                    "sprite_frames": anim.get("sprite_frames"),
                    "merged_clips": anim.get("animation_name", "").split(","),
                }
            continue
        name = str(anim.get("asset", ""))
        if name not in assets_manifest.get("assets", {}):
            continue
        assets_manifest["assets"][name]["runtime"] = {
            "project_path": project_path,
            "sprite_frames": anim.get("sprite_frames"),
            "frames_dir": anim.get("frames_dir"),
            "clip_name": anim.get("animation_name"),
        }
    for bg in assemble_result.get("backgrounds") or []:
        if not isinstance(bg, dict):
            continue
        name = str(bg.get("asset", ""))
        if name in assets_manifest.get("assets", {}):
            assets_manifest["assets"][name]["runtime"] = {
                "project_path": project_path,
                "res_path": f"res://{bg.get('path', '')}",
            }
    idle = assemble_result.get("idle_still") or godot_plan.get("idle_still")
    char = str(godot_plan.get("character_asset", ""))
    if char and char in assets_manifest.get("assets", {}) and idle:
        entry = assets_manifest["assets"][char]
        runtime = dict(entry.get("runtime") or {})
        runtime["idle_still"] = idle if isinstance(idle, str) and idle.startswith("assets/") else runtime.get("idle_still")
        entry["runtime"] = runtime


def refresh_assets_manifest_from_pipeline(
    manifest: dict[str, Any],
    *,
    invalidated_task_ids: list[str] | None = None,
) -> Path | None:
    """Rebuild stage ledger from pipeline manifest task statuses."""
    from pipeline_manifest import TASK_DONE, tasks_list

    paths = manifest.get("paths") or {}
    output_rel = str(paths.get("output_dir", ""))
    brief_rel = str(manifest.get("brief", ""))
    if not output_rel or not brief_rel:
        return None

    output_dir = (_REPO_ROOT / output_rel).resolve()
    brief_path = (_REPO_ROOT / brief_rel).resolve()
    manifest_path = assets_manifest_path_for_output(output_dir)

    if manifest_path.exists():
        assets_manifest = load_assets_manifest(manifest_path)
    else:
        assets_manifest = build_assets_manifest(brief_path, output_dir=output_dir)

    if invalidated_task_ids:
        for tid in invalidated_task_ids:
            invalidate_asset_stages_from_task(
                assets_manifest,
                tid,
                cascade_ids=invalidated_task_ids,
            )

    _, assets = load_brief(brief_path)
    asset_map = {a.name: a for a in assets}
    for task in tasks_list(manifest):
        if task.get("status") == TASK_DONE:
            apply_task_to_assets_manifest(assets_manifest, task, brief_assets=asset_map)

    handoff_cli = manifest.get("godot_assemble_file")
    if handoff_cli:
        handoff_path = (_CLI_DIR / handoff_cli).resolve()
        if handoff_path.is_file():
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            plan = handoff.get("plan") or {}
            for task in tasks_list(manifest):
                if task.get("step") != "godot.assemble" or task.get("status") != TASK_DONE:
                    continue
                result = task.get("result") or {}
                if isinstance(result, dict) and (
                    result.get("project_path") or result.get("animations")
                ):
                    apply_godot_assemble_runtime(
                        assets_manifest,
                        assemble_result=result,
                        godot_plan=plan,
                    )

    save_assets_manifest(manifest_path, assets_manifest)
    return manifest_path


def update_assets_manifest_after_assemble(
    assemble_path: Path,
    assemble_result: dict[str, Any],
    *,
    handoff: dict[str, Any] | None = None,
) -> Path | None:
    """Standalone godot assemble CLI — write runtime bindings to assets manifest."""
    if handoff is None:
        handoff = json.loads(assemble_path.read_text(encoding="utf-8"))
    plan = handoff.get("plan") or {}

    stem = assemble_path.stem
    if stem.startswith("godot_"):
        stem = stem[len("godot_") :]
    output_dir = _REPO_ROOT / "output" / stem
    manifest_path = assets_manifest_path_for_output(output_dir)
    if not manifest_path.is_file():
        return None

    assets_manifest = load_assets_manifest(manifest_path)
    apply_godot_assemble_runtime(
        assets_manifest,
        assemble_result=assemble_result,
        godot_plan=plan,
    )
    save_assets_manifest(manifest_path, assets_manifest)
    return manifest_path
