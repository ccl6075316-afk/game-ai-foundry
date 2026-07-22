"""Pipeline manifest — brief → DAG tasks for concurrent asset production."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from asset_pipeline import _plan_metadata
from brief import (
    ANIMATION_METHOD_IMG2IMG,
    ANIMATION_METHOD_VIDEO,
    AssetSpec,
    AssetType,
    ProjectContext,
    effective_style_anchor_kind,
    find_asset,
    is_runtime_only_asset,
    load_brief,
    load_brief_full,
    resolve_animation_loop,
    resolve_animation_name,
    resolve_asset_file_key,
    resolve_style_img2img_path,
    should_use_style_img2img,
    validate_brief_for_export,
)
from roles import (
    GODOT_ASSEMBLER_ROLE,
    GODOT_DEVELOPER_ROLE,
    IMAGE_GENERATOR_ROLE,
    ORCHESTRATOR_ROLE,
    PROMPT_CRAFTER_ROLE,
    VIDEO_GENERATOR_ROLE,
)
from plan_io import build_godot_handoff, save_handoff

MANIFEST_VERSION = 1
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLI_DIR = _REPO_ROOT / "cli"

TASK_PENDING = "pending"
TASK_RUNNING = "running"
TASK_DONE = "done"
TASK_FAILED = "failed"
TASK_SKIPPED = "skipped"


class AssetKind(str, Enum):
    STATIC = "static"
    VIDEO_ANIMATION = "video_animation"
    CHARACTER_POSE = "character_pose"


@dataclass
class PipelineTask:
    id: str
    asset: str
    step: str
    role: str
    depends_on: list[str] = field(default_factory=list)
    layer: int = 0
    status: str = TASK_PENDING
    command: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    started_at: str | None = None
    finished_at: str | None = None
    asset_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def repo_root() -> Path:
    return _REPO_ROOT


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel_to_repo(path: Path, *, base: Path | None = None) -> str:
    root = base or _REPO_ROOT
    path = path.resolve()
    try:
        return str(path.relative_to(root.resolve()))
    except ValueError:
        return str(path)


def cli_relative(path: Path) -> str:
    """Path as used in commands run from cli/ (gamefactory working directory)."""
    path = path.resolve()
    cli = _CLI_DIR.resolve()
    try:
        return str(path.relative_to(cli))
    except ValueError:
        pass
    root = _REPO_ROOT.resolve()
    try:
        return "../" + str(path.relative_to(root))
    except ValueError:
        return str(path)


def classify_asset(spec: AssetSpec) -> AssetKind:
    if spec.type == AssetType.CHARACTER_POSE:
        return AssetKind.CHARACTER_POSE
    if spec.type == AssetType.CHARACTER and spec.action.strip():
        if spec.animation_method == ANIMATION_METHOD_VIDEO:
            return AssetKind.VIDEO_ANIMATION
        if spec.animation_method == ANIMATION_METHOD_IMG2IMG:
            return AssetKind.CHARACTER_POSE
    return AssetKind.STATIC


def _asset_artifacts(output_dir: Path, plans_dir: Path, file_key: str) -> dict[str, str]:
    return {
        "plan": cli_relative(plans_dir / f"{file_key}.json"),
        "raw_image": cli_relative(output_dir / f"{file_key}_raw.png"),
        "trimmed_image": cli_relative(output_dir / f"{file_key}_trimmed.png"),
        "nobg_image": cli_relative(output_dir / f"{file_key}_nobg.png"),
        "video": cli_relative(output_dir / f"{file_key}.mp4"),
        "frames_dir": cli_relative(output_dir / f"{file_key}_frames"),
        "frames_nobg_dir": cli_relative(output_dir / f"{file_key}_nobg"),
        "slice_dir": cli_relative(output_dir / f"{file_key}_tiles"),
    }


def _brief_cli_path(brief_path: Path) -> str:
    return cli_relative(brief_path)


def _add_task(
    tasks: list[PipelineTask],
    *,
    asset: str,
    asset_id: str,
    step: str,
    role: str,
    depends_on: list[str],
    command: str,
    artifacts: dict[str, str],
    layer: int,
) -> str:
    task_id = f"{asset_id}.{step}"
    tasks.append(
        PipelineTask(
            id=task_id,
            asset=asset,
            asset_id=asset_id,
            step=step,
            role=role,
            depends_on=depends_on,
            layer=layer,
            command=command,
            artifacts=artifacts,
        )
    )
    return task_id


def _image_generate_task_id(asset_ids: dict[str, str], asset_name: str) -> str:
    aid = asset_ids.get(asset_name)
    if not aid:
        raise ValueError(f"Unknown asset name '{asset_name}' (no id mapping)")
    return f"{aid}.image.generate"


def _layer_from_deps(dep_ids: list[str], tasks_by_id: dict[str, PipelineTask]) -> int:
    if not dep_ids:
        return 0
    return max(tasks_by_id[did].layer for did in dep_ids) + 1


def _post_image_tasks(
    tasks: list[PipelineTask],
    tasks_by_id: dict[str, PipelineTask],
    *,
    project: ProjectContext,
    spec: AssetSpec,
    paths: dict[str, str],
    brief_cli: str,
    image_task_id: str,
    assets: list[AssetSpec],
) -> None:
    meta = _plan_metadata(project, spec, assets=assets)
    pipeline = meta.get("pipeline") or []
    prev_id = image_task_id
    name = spec.name
    file_key = resolve_asset_file_key(spec)

    for step_def in pipeline:
        if not isinstance(step_def, dict):
            continue
        step_name = step_def.get("step")
        if step_name in ("generate_image", "validate"):
            continue
        if step_name == "trim":
            dep = [prev_id]
            layer = _layer_from_deps(dep, tasks_by_id)
            tid = _add_task(
                tasks,
                asset=name,
                asset_id=file_key,
                step="image.trim",
                role=ORCHESTRATOR_ROLE,
                depends_on=dep,
                layer=layer,
                command=(
                    f"python gamefactory.py image trim "
                    f"--input {paths['raw_image']} --output {paths['trimmed_image']}"
                ),
                artifacts={
                    "input": paths["raw_image"],
                    "output": paths["trimmed_image"],
                },
            )
            tasks_by_id[tid] = tasks[-1]
            prev_id = tid
        elif step_name == "remove_bg":
            src = paths.get("trimmed_image", paths["raw_image"])
            dep = [prev_id]
            layer = _layer_from_deps(dep, tasks_by_id)
            tid = _add_task(
                tasks,
                asset=name,
                asset_id=file_key,
                step="image.remove-bg",
                role=ORCHESTRATOR_ROLE,
                depends_on=dep,
                layer=layer,
                command=(
                    f"python gamefactory.py image remove-bg "
                    f"--input {src} --output {paths['nobg_image']}"
                ),
                artifacts={"input": src, "output": paths["nobg_image"]},
            )
            tasks_by_id[tid] = tasks[-1]
            prev_id = tid
        elif step_name == "slice":
            from brief import resolve_icon_grid

            grid = resolve_icon_grid(
                str(step_def.get("grid") or spec.grid or "2x2"),
                len(spec.items or []),
            )
            dep = [prev_id]
            layer = _layer_from_deps(dep, tasks_by_id)
            tid = _add_task(
                tasks,
                asset=name,
                asset_id=file_key,
                step="image.slice",
                role=ORCHESTRATOR_ROLE,
                depends_on=dep,
                layer=layer,
                command=(
                    f"python gamefactory.py image slice "
                    f"--input {paths['raw_image']} --mode grid "
                    f"--rows {grid.split('x')[0]} --cols {grid.split('x')[1]} "
                    f"--output-dir {paths['slice_dir']}"
                ),
                artifacts={"input": paths["raw_image"], "output_dir": paths["slice_dir"]},
            )
            tasks_by_id[tid] = tasks[-1]
            prev_id = tid


def _icon_kit_item_tasks(
    tasks: list[PipelineTask],
    tasks_by_id: dict[str, PipelineTask],
    *,
    project: ProjectContext,
    spec: AssetSpec,
    brief_cli: str,
    output_dir: Path,
    plans_dir: Path,
    config: dict[str, Any] | None,
) -> None:
    """Expand icon_kit into per-item single-object generate + post (no slice)."""
    from brief import unique_item_slugs
    from image_model_route import effective_generate_tier, resolve_image_model_for_tier

    if not spec.items:
        raise ValueError(f"icon_kit '{spec.name}' requires an 'items' list.")

    name = spec.name
    file_key = resolve_asset_file_key(spec)
    slugs = unique_item_slugs([str(x) for x in spec.items])
    tier = effective_generate_tier(
        generate_tier=spec.generate_tier or None,
        for_icon_kit_item=True,
    )
    model = resolve_image_model_for_tier(config, tier)
    model_flag = f" --model {model}" if model else ""

    for label, slug in zip([str(x) for x in spec.items], slugs, strict=True):
        item_key = f"{file_key}__{slug}"
        paths = _asset_artifacts(output_dir, plans_dir, item_key)
        # Escape item for CLI: use simple quoting via json
        item_arg = json.dumps(label, ensure_ascii=False)
        prompt_id = _add_task(
            tasks,
            asset=name,
            asset_id=item_key,
            step="prompt.craft",
            role=PROMPT_CRAFTER_ROLE,
            depends_on=[],
            layer=0,
            command=(
                f"python gamefactory.py prompt craft "
                f"--brief {brief_cli} --asset {file_key} --item {item_arg} "
                f"-o {paths['plan']}"
            ),
            artifacts={"plan": paths["plan"], "kit_item": label, "kit_item_slug": slug},
        )
        tasks_by_id[prompt_id] = tasks[-1]

        image_deps = [prompt_id]
        image_layer = _layer_from_deps(image_deps, tasks_by_id)
        image_id = _add_task(
            tasks,
            asset=name,
            asset_id=item_key,
            step="image.generate",
            role=IMAGE_GENERATOR_ROLE,
            depends_on=image_deps,
            layer=image_layer,
            command=(
                f"python gamefactory.py image generate "
                f"--plan-file {paths['plan']} --output {paths['raw_image']} "
                f"--validate{model_flag}"
            ),
            artifacts={
                "plan": paths["plan"],
                "output": paths["raw_image"],
                "kit_item": label,
                "kit_item_slug": slug,
            },
        )
        tasks_by_id[image_id] = tasks[-1]

        # Post: trim → remove-bg → validate_matting (same as character still)
        prev = image_id
        for step_name, step_id, cmd, arts in (
            (
                "image.trim",
                "image.trim",
                (
                    f"python gamefactory.py image trim "
                    f"--input {paths['raw_image']} --output {paths['trimmed_image']}"
                ),
                {"input": paths["raw_image"], "output": paths["trimmed_image"]},
            ),
            (
                "image.remove-bg",
                "image.remove-bg",
                (
                    f"python gamefactory.py image remove-bg --mode color "
                    f"--input {paths['trimmed_image']} --output {paths['nobg_image']}"
                ),
                {"input": paths["trimmed_image"], "output": paths["nobg_image"]},
            ),
            (
                "image.validate-matting",
                "image.validate-matting",
                (
                    f"python gamefactory.py image validate-matting "
                    f"--input {paths['nobg_image']}"
                ),
                {"input": paths["nobg_image"]},
            ),
        ):
            dep = [prev]
            layer = _layer_from_deps(dep, tasks_by_id)
            tid = _add_task(
                tasks,
                asset=name,
                asset_id=item_key,
                step=step_id,
                role=ORCHESTRATOR_ROLE,
                depends_on=dep,
                layer=layer,
                command=cmd,
                artifacts=arts,
            )
            tasks_by_id[tid] = tasks[-1]
            prev = tid


def _static_asset_tasks(
    tasks: list[PipelineTask],
    tasks_by_id: dict[str, PipelineTask],
    *,
    project: ProjectContext,
    spec: AssetSpec,
    brief_cli: str,
    paths: dict[str, str],
    asset_ids: dict[str, str],
    assets: list[AssetSpec],
    brief_path: Path,
    config: dict[str, Any] | None = None,
) -> None:
    from image_model_route import effective_generate_tier, resolve_image_model_for_tier

    name = spec.name
    file_key = resolve_asset_file_key(spec)
    prompt_id = _add_task(
        tasks,
        asset=name,
        asset_id=file_key,
        step="prompt.craft",
        role=PROMPT_CRAFTER_ROLE,
        depends_on=[],
        layer=0,
        command=(
            f"python gamefactory.py prompt craft "
            f"--brief {brief_cli} --asset {file_key} -o {paths['plan']}"
        ),
        artifacts={"plan": paths["plan"]},
    )
    tasks_by_id[prompt_id] = tasks[-1]

    image_deps = [prompt_id]
    ref_flag = ""
    ref_name = spec.reference_asset.strip() if spec.type == AssetType.CHARACTER_POSE else ""
    if ref_name:
        ref_image_task = _image_generate_task_id(asset_ids, ref_name)
        if ref_image_task not in tasks_by_id:
            raise ValueError(
                f"Asset '{name}' references '{ref_name}' but {ref_image_task} is missing."
            )
        image_deps.append(ref_image_task)
        ref_raw = _find_artifacts_for_asset(tasks, ref_name)["output"]
        ref_flag = f" --reference-image {ref_raw}"
    elif should_use_style_img2img(spec, project=project, assets=assets):
        style_path = resolve_style_img2img_path(
            spec,
            project=project,
            assets=assets,
            brief_path=brief_path,
        )
        if not style_path:
            raise ValueError(
                f"Asset '{name}' requires style img2img --reference-image "
                "but the anchor path could not be resolved."
            )
        identity_ref = (spec.identity_anchor or "").strip()
        source_asset: AssetSpec | None = None
        if identity_ref:
            try:
                source_asset = find_asset(assets, identity_ref)
            except ValueError as exc:
                raise ValueError(
                    f"Asset '{name}' identity_anchor '{identity_ref}' not found in assets[]"
                ) from exc
        if source_asset is None:
            kind = effective_style_anchor_kind(spec)
            if kind == "asset":
                anchor_ref = (spec.style_anchor or "").strip()
                try:
                    source_asset = find_asset(assets, anchor_ref)
                except ValueError as exc:
                    raise ValueError(
                        f"Asset '{name}' style_anchor '{anchor_ref}' not found in assets[]"
                    ) from exc
            elif kind == "visual_reference":
                ref_flag = f" --reference-image {style_path}"
            else:
                raise ValueError(
                    f"Asset '{name}' style img2img enabled but style_anchor_kind is invalid."
                )
        if source_asset is not None:
            anchor_name = source_asset.name
            ref_image_task = _image_generate_task_id(asset_ids, anchor_name)
            if ref_image_task not in tasks_by_id:
                anchor_label = identity_ref if identity_ref else (spec.style_anchor or "").strip()
                raise ValueError(
                    f"Asset '{name}' style img2img references '{anchor_label}' "
                    f"but {ref_image_task} is missing."
                )
            image_deps.append(ref_image_task)
            ref_raw = _find_artifacts_for_asset(tasks, anchor_name)["output"]
            ref_flag = f" --reference-image {ref_raw}"

    tier = effective_generate_tier(
        generate_tier=spec.generate_tier or None,
        for_icon_kit_item=False,
    )
    model = resolve_image_model_for_tier(config, tier)
    model_flag = f" --model {model}" if model else ""

    image_layer = _layer_from_deps(image_deps, tasks_by_id)
    image_id = _add_task(
        tasks,
        asset=name,
        asset_id=file_key,
        step="image.generate",
        role=IMAGE_GENERATOR_ROLE,
        depends_on=image_deps,
        layer=image_layer,
        command=(
            f"python gamefactory.py image generate "
            f"--plan-file {paths['plan']} --output {paths['raw_image']} "
            f"--validate{ref_flag}{model_flag}"
        ),
        artifacts={"plan": paths["plan"], "output": paths["raw_image"]},
    )
    tasks_by_id[image_id] = tasks[-1]

    if spec.type != AssetType.CHARACTER_POSE or spec.reference_asset:
        _post_image_tasks(
            tasks,
            tasks_by_id,
            project=project,
            spec=spec,
            paths=paths,
            brief_cli=brief_cli,
            image_task_id=image_id,
            assets=assets,
        )


def _find_artifacts_for_asset(tasks: list[PipelineTask], asset_name: str) -> dict[str, str]:
    for task in tasks:
        if task.asset == asset_name and task.step == "image.generate":
            return dict(task.artifacts)
    raise ValueError(f"No image.generate artifacts for asset '{asset_name}'")


def _video_animation_tasks(
    tasks: list[PipelineTask],
    tasks_by_id: dict[str, PipelineTask],
    *,
    spec: AssetSpec,
    brief_cli: str,
    paths: dict[str, str],
    sprite_frames: int,
    asset_ids: dict[str, str],
) -> None:
    name = spec.name
    file_key = resolve_asset_file_key(spec)
    ref_name = spec.reference_asset.strip()
    if not ref_name:
        raise ValueError(f"Video animation '{name}' requires reference_asset.")

    prompt_id = _add_task(
        tasks,
        asset=name,
        asset_id=file_key,
        step="prompt.craft",
        role=PROMPT_CRAFTER_ROLE,
        depends_on=[],
        layer=0,
        command=(
            f"python gamefactory.py prompt craft --animation "
            f"--brief {brief_cli} --asset {file_key} -o {paths['plan']}"
        ),
        artifacts={"plan": paths["plan"]},
    )
    tasks_by_id[prompt_id] = tasks[-1]

    ref_image_task = _image_generate_task_id(asset_ids, ref_name)
    if ref_image_task not in tasks_by_id:
        raise ValueError(
            f"Animation '{name}' references '{ref_name}' but {ref_image_task} is missing."
        )
    ref_raw = _find_artifacts_for_asset(tasks, ref_name)["output"]

    video_deps = [prompt_id, ref_image_task]
    video_layer = _layer_from_deps(video_deps, tasks_by_id)
    video_id = _add_task(
        tasks,
        asset=name,
        asset_id=file_key,
        step="video.generate",
        role=VIDEO_GENERATOR_ROLE,
        depends_on=video_deps,
        layer=video_layer,
        command=(
            f"python gamefactory.py video generate "
            f"--plan-file {paths['plan']} "
            f"--reference-image {ref_raw} "
            f"--output {paths['video']}"
        ),
        artifacts={
            "plan": paths["plan"],
            "reference_image": ref_raw,
            "output": paths["video"],
        },
    )
    tasks_by_id[video_id] = tasks[-1]

    split_deps = [video_id]
    split_layer = _layer_from_deps(split_deps, tasks_by_id)
    split_id = _add_task(
        tasks,
        asset=name,
        asset_id=file_key,
        step="video.split-frames",
        role=ORCHESTRATOR_ROLE,
        depends_on=split_deps,
        layer=split_layer,
        command=(
            f"python gamefactory.py video split-frames "
            f"--input {paths['video']} --output-dir {paths['frames_dir']} "
            f"--frames {sprite_frames}"
        ),
        artifacts={"input": paths["video"], "output_dir": paths["frames_dir"]},
    )
    tasks_by_id[split_id] = tasks[-1]

    matte_deps = [split_id]
    matte_layer = _layer_from_deps(matte_deps, tasks_by_id)
    matte_id = _add_task(
        tasks,
        asset=name,
        asset_id=file_key,
        step="video.matte-frames",
        role=ORCHESTRATOR_ROLE,
        depends_on=matte_deps,
        layer=matte_layer,
        command=(
            f"python gamefactory.py video matte-frames "
            f"--input-dir {paths['frames_dir']} "
            f"--output-dir {paths['frames_nobg_dir']} "
            f"--engine ai --no-trim"
        ),
        artifacts={
            "input_dir": paths["frames_dir"],
            "output_dir": paths["frames_nobg_dir"],
        },
    )
    tasks_by_id[matte_id] = tasks[-1]


def _artifact_path_to_repo_rel(artifact_path: str) -> str:
    """Convert cli-relative artifact path to repo-relative (for godot handoff)."""
    resolved = (_CLI_DIR / artifact_path).resolve()
    return rel_to_repo(resolved)


def _collect_godot_plan(
    *,
    brief_stem: str,
    project: ProjectContext,
    assets: list[AssetSpec],
    output_dir: Path,
    tasks_by_id: dict[str, PipelineTask],
    godot_project: Path,
    sprite_frames_default: int = 8,
) -> dict[str, Any]:
    animations: list[dict[str, Any]] = []
    backgrounds: list[dict[str, Any]] = []
    character_asset: str | None = None

    for spec in assets:
        kind = classify_asset(spec)
        if kind == AssetKind.VIDEO_ANIMATION:
            file_key = resolve_asset_file_key(spec)
            matte_id = f"{file_key}.video.matte-frames"
            if matte_id in tasks_by_id:
                frames_dir = _artifact_path_to_repo_rel(
                    tasks_by_id[matte_id].artifacts.get("output_dir", "")
                )
            else:
                frames_dir = rel_to_repo(output_dir / f"{file_key}_nobg")
            sprite_count = spec.sprite_frames if spec.sprite_frames > 0 else sprite_frames_default
            animations.append(
                {
                    "asset": spec.name,
                    "frames_dir": frames_dir,
                    "fps": 12,
                    "animation_name": resolve_animation_name(spec),
                    "loop": resolve_animation_loop(spec),
                    "reference_asset": spec.reference_asset.strip(),
                    "sprite_frames": sprite_count,
                    "pre_trimmed": True,
                    "pre_sampled": True,
                    "display_size": (
                        spec.display_size.to_dict() if not spec.display_size.is_empty() else None
                    ),
                }
            )
        elif spec.type == AssetType.BACKGROUND:
            raw = rel_to_repo(output_dir / f"{resolve_asset_file_key(spec)}_raw.png")
            backgrounds.append(
                {
                    "asset": spec.name,
                    "image": raw,
                    "display_size": (
                        spec.display_size.to_dict() if not spec.display_size.is_empty() else None
                    ),
                }
            )

    idle_still_path: str | None = None
    name_to_id = {s.name: resolve_asset_file_key(s) for s in assets}
    for spec in assets:
        if classify_asset(spec) == AssetKind.VIDEO_ANIMATION and spec.reference_asset.strip():
            ref = spec.reference_asset.strip()
            character_asset = ref
            ref_key = name_to_id.get(ref, ref)
            idle_still_path = rel_to_repo(output_dir / f"{ref_key}_nobg.png")
            break

    if not idle_still_path:
        for spec in assets:
            if spec.type.value != "character":
                continue
            if classify_asset(spec) == AssetKind.VIDEO_ANIMATION:
                continue
            character_asset = spec.name
            file_key = resolve_asset_file_key(spec)
            nobg_id = f"{file_key}.image.remove-bg"
            if nobg_id in tasks_by_id:
                out_art = tasks_by_id[nobg_id].artifacts.get("output", "")
                if out_art:
                    idle_still_path = _artifact_path_to_repo_rel(out_art)
                    break
            idle_still_path = rel_to_repo(output_dir / f"{file_key}_nobg.png")
            break

    plan: dict[str, Any] = {
        "project_path": rel_to_repo(godot_project.resolve()),
        "project_name": project.title or brief_stem.replace("_", " ").title(),
        "template": "dotnet",
        "main_scene": "scenes/main.tscn",
        "animations": animations,
        "backgrounds": backgrounds,
    }
    if idle_still_path:
        plan["idle_still"] = idle_still_path
    if character_asset:
        plan["character_asset"] = character_asset
        for spec in assets:
            if spec.name == character_asset and not spec.display_size.is_empty():
                plan["character_display_size"] = spec.display_size.to_dict()
                break
    return plan


def _add_godot_tasks(
    tasks: list[PipelineTask],
    tasks_by_id: dict[str, PipelineTask],
    *,
    brief_stem: str,
    godot_plan: dict[str, Any],
    assemble_handoff_cli: str,
    all_asset_task_ids: list[str],
) -> None:
    if (
        not godot_plan.get("animations")
        and not godot_plan.get("backgrounds")
        and not godot_plan.get("idle_still")
    ):
        return

    deps = list(all_asset_task_ids)
    layer = _layer_from_deps(deps, tasks_by_id) if deps else 0
    assemble_id = f"{brief_stem}.godot.assemble"
    _add_task(
        tasks,
        asset=brief_stem,
        asset_id=brief_stem,
        step="godot.assemble",
        role=GODOT_ASSEMBLER_ROLE,
        depends_on=deps,
        layer=layer,
        command=(
            f"python gamefactory.py godot assemble "
            f"--assemble-file {assemble_handoff_cli} --validate"
        ),
        artifacts={
            "assemble_file": assemble_handoff_cli,
            "project_path": godot_plan.get("project_path", ""),
        },
    )
    tasks_by_id[assemble_id] = tasks[-1]


def _add_godot_dev_tasks(
    tasks: list[PipelineTask],
    tasks_by_id: dict[str, PipelineTask],
    *,
    brief_stem: str,
    brief_cli: str,
    project_path: Path,
    assemble_handoff_cli: str,
) -> None:
    assemble_id = f"{brief_stem}.godot.assemble"
    if assemble_id not in tasks_by_id:
        return

    dev_handoff_cli = cli_relative(_REPO_ROOT / "plans" / f"dev_{brief_stem}.json")
    deps = [assemble_id]
    layer = _layer_from_deps(deps, tasks_by_id)
    dev_id = f"{brief_stem}.godot.dev-context"
    _add_task(
        tasks,
        asset=brief_stem,
        asset_id=brief_stem,
        step="godot.dev-context",
        role=GODOT_DEVELOPER_ROLE,
        depends_on=deps,
        layer=layer,
        command=(
            f"python gamefactory.py godot dev-context "
            f"--brief {brief_cli} "
            f"--project {cli_relative(project_path)} "
            f"--assemble-file {assemble_handoff_cli} "
            f"-o {dev_handoff_cli}"
        ),
        artifacts={
            "dev_handoff": dev_handoff_cli,
            "project_path": rel_to_repo(project_path.resolve()),
        },
    )
    tasks_by_id[dev_id] = tasks[-1]


def build_manifest(
    brief_path: Path,
    *,
    output_dir: Path | None = None,
    plans_dir: Path | None = None,
    sprite_frames_default: int = 8,
    godot_project: Path | None = None,
    include_godot: bool = True,
    include_game_dev: bool = True,
) -> dict[str, Any]:
    """Expand brief into a task DAG manifest."""
    brief_path = brief_path.resolve()
    project, assets, graphs = load_brief_full(brief_path)
    validate_brief_for_export(project, assets, animation_graphs=graphs)

    from project_paths import default_paths_for_brief

    defaults = default_paths_for_brief(brief_path)
    if output_dir is None:
        output_dir = Path(defaults["output_dir"])
    if plans_dir is None:
        plans_dir = Path(defaults["plans_dir"])

    output_dir = output_dir.resolve()
    plans_dir = plans_dir.resolve()
    brief_cli = _brief_cli_path(brief_path)

    tasks: list[PipelineTask] = []
    tasks_by_id: dict[str, PipelineTask] = {}
    asset_ids = {spec.name: resolve_asset_file_key(spec) for spec in assets}

    try:
        from gamefactory import load_config

        pipeline_config = load_config()
    except Exception:  # noqa: BLE001
        pipeline_config = {}

    # Pass 1: static + pose assets (produce reference stills).
    for spec in assets:
        if is_runtime_only_asset(spec):
            continue
        kind = classify_asset(spec)
        if kind == AssetKind.VIDEO_ANIMATION:
            continue
        if spec.type == AssetType.ICON_KIT:
            _icon_kit_item_tasks(
                tasks,
                tasks_by_id,
                project=project,
                spec=spec,
                brief_cli=brief_cli,
                output_dir=output_dir,
                plans_dir=plans_dir,
                config=pipeline_config,
            )
            continue
        paths = _asset_artifacts(output_dir, plans_dir, asset_ids[spec.name])
        _static_asset_tasks(
            tasks,
            tasks_by_id,
            project=project,
            spec=spec,
            brief_cli=brief_cli,
            paths=paths,
            asset_ids=asset_ids,
            assets=assets,
            brief_path=brief_path,
            config=pipeline_config,
        )

    # Pass 2: video animations (depend on reference stills).
    for spec in assets:
        if classify_asset(spec) != AssetKind.VIDEO_ANIMATION:
            continue
        frames = spec.sprite_frames if spec.sprite_frames > 0 else sprite_frames_default
        paths = _asset_artifacts(output_dir, plans_dir, asset_ids[spec.name])
        _video_animation_tasks(
            tasks,
            tasks_by_id,
            spec=spec,
            brief_cli=brief_cli,
            paths=paths,
            sprite_frames=frames,
            asset_ids=asset_ids,
        )

    asset_task_ids = [t.id for t in tasks]

    godot_handoff_cli = ""
    if include_godot:
        if godot_project is None:
            godot_project = Path(defaults["godot_project"])
        godot_plan = _collect_godot_plan(
            brief_stem=brief_path.stem,
            project=project,
            assets=assets,
            output_dir=output_dir,
            tasks_by_id=tasks_by_id,
            godot_project=godot_project,
            sprite_frames_default=sprite_frames_default,
        )
        handoff_path = plans_dir / f"godot_{brief_path.stem}.json"
        save_handoff(handoff_path, build_godot_handoff(godot_plan))
        godot_handoff_cli = cli_relative(handoff_path)
        _add_godot_tasks(
            tasks,
            tasks_by_id,
            brief_stem=brief_path.stem,
            godot_plan=godot_plan,
            assemble_handoff_cli=godot_handoff_cli,
            all_asset_task_ids=asset_task_ids,
        )
        if include_game_dev:
            _add_godot_dev_tasks(
                tasks,
                tasks_by_id,
                brief_stem=brief_path.stem,
                brief_cli=brief_cli,
                project_path=godot_project,
                assemble_handoff_cli=godot_handoff_cli,
            )

    from assets_manifest import (
        assets_manifest_path_for_output,
        build_assets_manifest,
        save_assets_manifest,
    )

    assets_manifest_data = build_assets_manifest(brief_path, output_dir=output_dir)
    assets_manifest_file = assets_manifest_path_for_output(output_dir)
    save_assets_manifest(assets_manifest_file, assets_manifest_data)

    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "brief": rel_to_repo(brief_path),
        "project": {
            "title": project.title,
            "description": project.description,
        },
        "paths": {
            "repo_root": ".",
            "cli_dir": rel_to_repo(_CLI_DIR),
            "output_dir": rel_to_repo(output_dir),
            "plans_dir": rel_to_repo(plans_dir),
            "assets_manifest": rel_to_repo(assets_manifest_file),
            "workdir": "cli",
        },
        "tasks": [t.to_dict() for t in tasks],
    }
    if include_godot and godot_handoff_cli:
        manifest["godot_project"] = rel_to_repo(godot_project.resolve())
        manifest["godot_assemble_file"] = godot_handoff_cli
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("manifest_version") != MANIFEST_VERSION:
        raise ValueError(f"Unsupported manifest version in {path}")
    return data


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = _utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tasks_list(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw = manifest.get("tasks", [])
    if not isinstance(raw, list):
        raise ValueError("manifest.tasks must be a list")
    return raw


def task_by_id(manifest: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in tasks_list(manifest):
        if task.get("id") == task_id:
            return task
    known = ", ".join(t["id"] for t in tasks_list(manifest))
    raise ValueError(f"Unknown task id '{task_id}'. Known: {known}")


def _deps_satisfied(task: dict[str, Any], tasks_by_id: dict[str, dict[str, Any]]) -> bool:
    for dep in task.get("depends_on") or []:
        dep_task = tasks_by_id.get(dep)
        if dep_task is None or dep_task.get("status") != TASK_DONE:
            return False
    return True


def ready_tasks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Tasks whose dependencies are done and status is pending."""
    by_id = {t["id"]: t for t in tasks_list(manifest)}
    ready = [
        t
        for t in tasks_list(manifest)
        if t.get("status") == TASK_PENDING and _deps_satisfied(t, by_id)
    ]
    ready.sort(key=lambda t: (t.get("layer", 0), t.get("id", "")))
    return ready


def status_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for task in tasks_list(manifest):
        status = str(task.get("status", TASK_PENDING))
        counts[status] = counts.get(status, 0) + 1
    ready = ready_tasks(manifest)
    return {
        "brief": manifest.get("brief"),
        "total": len(tasks_list(manifest)),
        "counts": counts,
        "ready_count": len(ready),
        "ready_ids": [t["id"] for t in ready],
        "failed_ids": [t["id"] for t in tasks_list(manifest) if t.get("status") == TASK_FAILED],
        "done": (
            counts.get(TASK_DONE, 0) + counts.get(TASK_SKIPPED, 0)
            == len(tasks_list(manifest))
        ),
    }


def record_task(
    manifest: dict[str, Any],
    task_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    merge_result: bool = True,
) -> dict[str, Any]:
    task = task_by_id(manifest, task_id)
    now = _utc_now()
    if status == TASK_RUNNING:
        task["status"] = TASK_RUNNING
        task["started_at"] = task.get("started_at") or now
    else:
        task["status"] = status
        task["finished_at"] = now
    if result is not None:
        if merge_result and isinstance(task.get("result"), dict):
            merged = dict(task["result"])
            merged.update(result)
            task["result"] = merged
        else:
            task["result"] = result
    return task


def _artifact_exists(repo_root: Path, cli_rel: str) -> bool:
    _ = repo_root
    path = (_CLI_DIR / cli_rel).resolve()
    if path.is_file():
        return True
    if path.is_dir() and any(path.iterdir()):
        return True
    return False


def _primary_artifact_rel(task: dict[str, Any]) -> str | None:
    """Cli-relative path that must exist for a task to stay done.

    Prefer the produced media/output over plan text so deleting an unsatisfactory
    PNG/video marks generate (and dependents) for regeneration.
    """
    arts = task.get("artifacts") or {}
    if not isinstance(arts, dict):
        return None
    step = str(task.get("step") or "")
    if step == "prompt.craft" or step.endswith(".prompt.craft"):
        rel = arts.get("plan")
        return str(rel) if rel else None
    for key in (
        "output",
        "output_dir",
        "nobg_image",
        "video",
        "dev_handoff",
        "assemble_file",
        "plan",
    ):
        rel = arts.get(key)
        if rel:
            return str(rel)
    return None


def _reset_task_to_pending(task: dict[str, Any]) -> None:
    task["status"] = TASK_PENDING
    task["result"] = None
    task["started_at"] = None
    task["finished_at"] = None


def invalidate_missing_artifacts(manifest: dict[str, Any]) -> list[str]:
    """Reset done/skipped tasks whose primary artifact is gone (e.g. user deleted), plus dependents.

    Supports the workflow where producers delete unsatisfactory outputs and expect
    the next status/reconcile/run pass to regenerate them.
    """
    missing_roots: list[str] = []
    for task in tasks_list(manifest):
        if task.get("status") not in (TASK_DONE, TASK_SKIPPED):
            continue
        rel = _primary_artifact_rel(task)
        if not rel:
            continue
        if not _artifact_exists(_REPO_ROOT, rel):
            missing_roots.append(str(task["id"]))

    if not missing_roots:
        return []

    by_id = {t["id"]: t for t in tasks_list(manifest)}
    reset_ids: list[str] = []
    seen: set[str] = set()
    stack = list(missing_roots)
    while stack:
        tid = stack.pop()
        if tid in seen:
            continue
        seen.add(tid)
        task = by_id.get(tid)
        if task is None:
            continue
        _reset_task_to_pending(task)
        reset_ids.append(tid)
        for other in tasks_list(manifest):
            if tid in (other.get("depends_on") or []):
                stack.append(str(other["id"]))

    from assets_manifest import refresh_assets_manifest_from_pipeline

    refresh_assets_manifest_from_pipeline(manifest, invalidated_task_ids=reset_ids)
    return reset_ids


def reconcile_manifest(manifest: dict[str, Any], *, repo_root: Path | None = None) -> dict[str, Any]:
    """Sync task status with disk: missing outputs → pending; existing outputs → done.

    Returns ``{"invalidated": n, "promoted": m, "invalidated_ids": [...], "total": n+m}``.
    """
    _ = repo_root
    invalidated_ids = invalidate_missing_artifacts(manifest)
    promoted = 0
    by_id = {t["id"]: t for t in tasks_list(manifest)}

    for task in tasks_list(manifest):
        if task.get("status") != TASK_PENDING:
            continue
        if not _deps_satisfied(task, by_id):
            continue
        # Must match invalidate: only the primary deliverable counts (not plan alone).
        rel = _primary_artifact_rel(task)
        if not rel or not _artifact_exists(_REPO_ROOT, rel):
            continue
        record_task(
            manifest,
            task["id"],
            status=TASK_DONE,
            result={"source": "reconcile", "reconciled_at": _utc_now()},
        )
        by_id[task["id"]] = task_by_id(manifest, task["id"])
        promoted += 1

    return {
        "invalidated": len(invalidated_ids),
        "promoted": promoted,
        "invalidated_ids": invalidated_ids,
        "total": len(invalidated_ids) + promoted,
    }


def merge_manifest_status(new_manifest: dict[str, Any], old_manifest: dict[str, Any]) -> None:
    """Preserve task status/result from a previous manifest when replanning."""
    old_by_id = {t["id"]: t for t in tasks_list(old_manifest)}
    for task in tasks_list(new_manifest):
        old = old_by_id.get(task["id"])
        if not old:
            continue
        for key in ("status", "result", "started_at", "finished_at"):
            if old.get(key) is not None:
                task[key] = old[key]
