"""Pipeline manifest — brief → DAG tasks for concurrent asset production."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from asset_pipeline import _plan_metadata
from asset_sizing import effective_display_dict, resolve_effective_display_size
from brief import (
    ANIMATION_METHOD_IMG2IMG,
    AssetSpec,
    AssetType,
    IconKitItem,
    ProjectContext,
    effective_style_anchor_kind,
    expand_stateful_assets,
    find_asset,
    find_icon_kit_item,
    is_runtime_only_asset,
    load_brief,
    load_brief_full,
    resolve_animation_loop,
    resolve_animation_name,
    resolve_asset_file_key,
    resolve_generate_method,
    resolve_kit_item_slug,
    resolve_style_img2img_path,
    should_use_style_img2img,
    unique_kit_item_slugs,
    validate_brief_for_export,
)
from generation_fingerprint import (
    build_generation_input,
    is_handoff_generation_stale,
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
from production import PLACABLE_CONTENT_CLASSES, build_layout, layout_asset_key, load_production

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
    # generate_method (resolved) is the pipeline truth; animation_method alone on
    # character_pose must not silently fall through to still-only tasks.
    if resolve_generate_method(spec) == "video":
        return AssetKind.VIDEO_ANIMATION
    if spec.type == AssetType.CHARACTER_POSE:
        return AssetKind.CHARACTER_POSE
    if (
        spec.type == AssetType.CHARACTER
        and spec.action.strip()
        and spec.animation_method == ANIMATION_METHOD_IMG2IMG
    ):
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


def _stateful_base_id(spec: AssetSpec) -> str | None:
    file_key = resolve_asset_file_key(spec)
    if "__" not in file_key:
        return None
    return file_key.rsplit("__", 1)[0]


def _stateful_siblings(spec: AssetSpec, assets: list[AssetSpec]) -> list[AssetSpec]:
    base = _stateful_base_id(spec)
    if not base:
        return []
    siblings: list[AssetSpec] = []
    for candidate in assets:
        if (candidate.content_class or "").strip() != "prop_stateful":
            continue
        if not (candidate.state or "").strip():
            continue
        if _stateful_base_id(candidate) == base:
            siblings.append(candidate)
    return siblings


def _stateful_state0_spec(spec: AssetSpec, assets: list[AssetSpec]) -> AssetSpec | None:
    siblings = _stateful_siblings(spec, assets)
    return siblings[0] if siblings else None


def _is_stateful_follow_on(spec: AssetSpec, assets: list[AssetSpec]) -> bool:
    state0 = _stateful_state0_spec(spec, assets)
    if state0 is None:
        return False
    return resolve_asset_file_key(spec) != resolve_asset_file_key(state0)


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
    from brief import should_use_kit_style_img2img, unique_kit_item_slugs
    from image_model_route import effective_generate_tier, resolve_image_model_for_tier

    if not spec.items:
        raise ValueError(f"icon_kit '{spec.name}' requires an 'items' list.")

    name = spec.name
    file_key = resolve_asset_file_key(spec)
    slugs = unique_kit_item_slugs(spec.items)
    tier = effective_generate_tier(
        generate_tier=spec.generate_tier or None,
        for_icon_kit_item=True,
    )
    model = resolve_image_model_for_tier(config, tier)
    model_flag = f" --model {model}" if model else ""
    tier_flag = f" --tier {tier}"
    kit_style = should_use_kit_style_img2img(spec)
    anchor_image_id: str | None = None
    anchor_raw: str | None = None

    for index, (item, slug) in enumerate(zip(spec.items, slugs, strict=True)):
        item_key = f"{file_key}__{slug}"
        paths = _asset_artifacts(output_dir, plans_dir, item_key)
        # Prefer stable id for --item so craft matches id even when label differs.
        item_arg = json.dumps(item.id, ensure_ascii=False)
        item_meta = {
            "kit_item": item.prompt_label,
            "kit_item_id": item.id,
            "kit_item_slug": slug,
            "kit_item_usage": item.usage or spec.usage,
            "kit_item_usage_description": item.usage_description or spec.usage_description,
        }
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
            artifacts={"plan": paths["plan"], **item_meta},
        )
        tasks_by_id[prompt_id] = tasks[-1]

        image_deps = [prompt_id]
        ref_flag = ""
        if kit_style and index > 0 and anchor_image_id and anchor_raw:
            image_deps.append(anchor_image_id)
            ref_flag = f" --reference-image {anchor_raw}"
            item_meta = {
                **item_meta,
                "kit_style_anchor_slug": slugs[0],
                "kit_style_reference": anchor_raw,
            }
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
                f"--validate{ref_flag}{model_flag}{tier_flag}"
            ),
            artifacts={
                "plan": paths["plan"],
                "output": paths["raw_image"],
                **item_meta,
            },
        )
        tasks_by_id[image_id] = tasks[-1]
        if index == 0:
            anchor_image_id = image_id
            anchor_raw = paths["raw_image"]

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
                {"input": paths["raw_image"], "output": paths["trimmed_image"], **item_meta},
            ),
            (
                "image.remove-bg",
                "image.remove-bg",
                (
                    f"python gamefactory.py image remove-bg --mode color "
                    f"--input {paths['trimmed_image']} --output {paths['nobg_image']}"
                ),
                {"input": paths["trimmed_image"], "output": paths["nobg_image"], **item_meta},
            ),
            (
                "image.validate-matting",
                "image.validate-matting",
                (
                    f"python gamefactory.py image validate-matting "
                    f"--input {paths['nobg_image']}"
                ),
                {"input": paths["nobg_image"], **item_meta},
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
    elif _is_stateful_follow_on(spec, assets):
        state0 = _stateful_state0_spec(spec, assets)
        if state0 is None:
            raise ValueError(
                f"Asset '{name}' prop_stateful follow-on state could not resolve state 0 sibling."
            )
        state0_key = resolve_asset_file_key(state0)
        ref_image_task = f"{state0_key}.image.generate"
        if ref_image_task not in tasks_by_id:
            raise ValueError(
                f"Asset '{name}' stateful img2img requires state 0 generate "
                f"'{ref_image_task}' but it is missing."
            )
        image_deps.append(ref_image_task)
        ref_raw = tasks_by_id[ref_image_task].artifacts["output"]
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
    tier_flag = f" --tier {tier}"

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
            f"--validate{ref_flag}{model_flag}{tier_flag}"
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


def _layout_for_godot_plan(
    project: ProjectContext,
    assets: list[AssetSpec],
    *,
    brief_stem: str,
    plans_dir: Path | None,
) -> dict[str, Any]:
    """Prefer hand-edited production.layout when present; else derive from brief."""
    if plans_dir is not None:
        prod_path = Path(plans_dir) / f"production_{brief_stem}.json"
        if prod_path.is_file():
            try:
                data = load_production(prod_path)
                doc = data.get("production_doc") if isinstance(data, dict) else None
                layout = doc.get("layout") if isinstance(doc, dict) else None
                if isinstance(layout, dict) and (
                    isinstance(layout.get("placements"), list)
                    or isinstance(layout.get("regions"), list)
                ):
                    return layout
            except (OSError, ValueError, TypeError, KeyError):
                pass
    return build_layout(project, assets)


def _is_placeholder_asset(spec: AssetSpec) -> bool:
    return str(getattr(spec, "availability", "") or "ready").strip().lower() == "placeholder"


def _validate_placeholder_assets(
    project: ProjectContext,
    assets: list[AssetSpec],
    graphs: list[Any],
) -> None:
    placeholder_names = {spec.name for spec in assets if _is_placeholder_asset(spec)}
    placeholder_ids = {spec.id for spec in assets if _is_placeholder_asset(spec) and spec.id.strip()}
    if not placeholder_names and not placeholder_ids:
        return

    def _is_placeholder_ref(label: str) -> bool:
        key = str(label or "").strip()
        return bool(key) and (key in placeholder_names or key in placeholder_ids)

    errors: list[str] = []
    player_asset = str(project.player_asset or "").strip()
    if _is_placeholder_ref(player_asset):
        errors.append(f"player_asset '{player_asset}' cannot be placeholder")

    for spec in assets:
        if _is_placeholder_asset(spec):
            continue
        if _is_placeholder_ref(spec.reference_asset):
            errors.append(
                f"Asset '{spec.name}' references placeholder asset '{spec.reference_asset.strip()}'"
            )
        if _is_placeholder_ref(spec.style_anchor):
            errors.append(
                f"Asset '{spec.name}' style_anchor points to placeholder asset '{spec.style_anchor.strip()}'"
            )
        if _is_placeholder_ref(spec.identity_anchor):
            errors.append(
                f"Asset '{spec.name}' identity_anchor points to placeholder asset '{spec.identity_anchor.strip()}'"
            )

    for graph in graphs:
        char_asset = str(getattr(graph, "character_asset", "") or "").strip()
        if _is_placeholder_ref(char_asset):
            errors.append(f"animation_graph character_asset '{char_asset}' cannot be placeholder")

    if errors:
        raise ValueError("Placeholder assets are still required:\n- " + "\n- ".join(errors))


def _collect_godot_plan(
    *,
    brief_stem: str,
    project: ProjectContext,
    assets: list[AssetSpec],
    output_dir: Path,
    tasks_by_id: dict[str, PipelineTask],
    godot_project: Path,
    sprite_frames_default: int = 8,
    plans_dir: Path | None = None,
) -> dict[str, Any]:
    assets = [spec for spec in assets if not _is_placeholder_asset(spec)]
    animations: list[dict[str, Any]] = []
    backgrounds: list[dict[str, Any]] = []
    props: list[dict[str, Any]] = []
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
                    "display_size": effective_display_dict(spec, project),
                }
            )
        elif spec.type == AssetType.BACKGROUND:
            raw = rel_to_repo(output_dir / f"{resolve_asset_file_key(spec)}_raw.png")
            backgrounds.append(
                {
                    "asset": spec.name,
                    "image": raw,
                    "display_size": effective_display_dict(spec, project),
                }
            )
        elif (spec.content_class or "").strip() in PLACABLE_CONTENT_CLASSES:
            file_key = resolve_asset_file_key(spec)
            asset_key = layout_asset_key(spec)
            nobg_id = f"{file_key}.image.remove-bg"
            if nobg_id in tasks_by_id:
                out_art = tasks_by_id[nobg_id].artifacts.get("output", "")
                image = _artifact_path_to_repo_rel(out_art) if out_art else rel_to_repo(
                    output_dir / f"{file_key}_nobg.png"
                )
            else:
                image = rel_to_repo(output_dir / f"{file_key}_nobg.png")
            props.append(
                {
                    "asset": asset_key,
                    "image": image,
                    "display_size": effective_display_dict(spec, project),
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

    layout = _layout_for_godot_plan(
        project,
        assets,
        brief_stem=brief_stem,
        plans_dir=plans_dir,
    )
    plan: dict[str, Any] = {
        "project_path": rel_to_repo(godot_project.resolve()),
        "project_name": project.title or brief_stem.replace("_", " ").title(),
        "template": "dotnet",
        "main_scene": "scenes/main.tscn",
        "animations": animations,
        "backgrounds": backgrounds,
        "props": props,
        "layout": layout,
        "viewport": dict(project.viewport) if project.viewport else {"width": 1280, "height": 720},
    }
    if idle_still_path:
        plan["idle_still"] = idle_still_path
    if character_asset:
        plan["character_asset"] = character_asset
        for spec in assets:
            if spec.name == character_asset:
                plan["character_display_size"] = effective_display_dict(spec, project)
                if plan["character_display_size"]:
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
        and not godot_plan.get("props")
        and not (isinstance(godot_plan.get("layout"), dict) and godot_plan["layout"].get("placements"))
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
    max_wave: int | None = None,
) -> dict[str, Any]:
    """Expand brief into a task DAG manifest.

    When ``max_wave`` is set, only assets with ``production_wave <= max_wave``
    enter the generation DAG. The full brief remains the design ledger;
    later waves are planned with a higher ``max_wave`` (or omit the filter).
    """
    brief_path = brief_path.resolve()
    project, assets, graphs = load_brief_full(brief_path)
    validate_brief_for_export(project, assets, animation_graphs=graphs)
    assets = expand_stateful_assets(assets)
    _validate_placeholder_assets(project, assets, graphs)
    assets = [a for a in assets if not _is_placeholder_asset(a)]
    keep_names = {a.name for a in assets}
    graphs = [g for g in graphs if g.character_asset in keep_names]

    if max_wave is not None:
        if max_wave < 1:
            raise ValueError(f"max_wave must be >= 1, got {max_wave}")
        assets = [a for a in assets if int(getattr(a, "production_wave", 1) or 1) <= max_wave]
        keep_names = {a.name for a in assets}
        graphs = [g for g in graphs if g.character_asset in keep_names]

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
    asset_ids: dict[str, str] = {}
    for spec in assets:
        key = resolve_asset_file_key(spec)
        asset_ids[spec.name] = key
        asset_ids[key] = key

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
        file_key = resolve_asset_file_key(spec)
        paths = _asset_artifacts(output_dir, plans_dir, file_key)
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
            plans_dir=plans_dir,
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
    if max_wave is not None:
        manifest["meta"] = {
            **(manifest.get("meta") if isinstance(manifest.get("meta"), dict) else {}),
            "production_max_wave": max_wave,
            "production_wave_asset_count": len(assets),
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
        "skipped_ids": [
            t["id"] for t in tasks_list(manifest) if t.get("status") == TASK_SKIPPED
        ],
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


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _png_header_ok(path: Path) -> bool:
    try:
        if path.stat().st_size < 33:
            return False
        with path.open("rb") as fh:
            return fh.read(8) == _PNG_MAGIC
    except OSError:
        return False


def _expected_split_frame_count(task: dict[str, Any]) -> int | None:
    cmd = str(task.get("command") or "")
    match = re.search(r"--frames\s+(\d+)", cmd)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except ValueError:
        return None
    return value if value > 0 else None


def _frames_dir_ready(task: dict[str, Any], cli_rel: str) -> bool:
    """True when a split-frames output dir has enough intact frame_*.png files."""
    path = (_CLI_DIR / cli_rel).resolve()
    if not path.is_dir():
        return False
    frames = sorted(path.glob("frame_*.png"))
    if not frames:
        return False
    expected = _expected_split_frame_count(task)
    if expected is not None and len(frames) < expected:
        return False
    return all(_png_header_ok(frame) for frame in frames)


def _primary_artifact_ready(task: dict[str, Any], cli_rel: str) -> bool:
    """Stricter than exists — refuse promoting half-written video frame dirs."""
    step = str(task.get("step") or "")
    if step == "video.split-frames" or step.endswith(".video.split-frames"):
        return _frames_dir_ready(task, cli_rel)
    return _artifact_exists(_REPO_ROOT, cli_rel)


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


def _expected_craft_consumer_role(task: dict[str, Any]) -> str | None:
    """Expected handoff consumer_role for a prompt.craft task, or None if unknown."""
    step = str(task.get("step") or "")
    if step != "prompt.craft" and not step.endswith(".prompt.craft"):
        return None
    cmd = str(task.get("command") or "")
    if "--animation" in cmd:
        return VIDEO_GENERATOR_ROLE
    return IMAGE_GENERATOR_ROLE


def _craft_plan_matches_task(task: dict[str, Any], plan_rel: str) -> bool:
    """Reject promoting craft when on-disk plan is for the wrong generator."""
    expected = _expected_craft_consumer_role(task)
    if expected is None:
        return True
    handoff = _load_handoff_json(plan_rel)
    if handoff is None:
        return False
    return str(handoff.get("consumer_role") or "") == expected


def invalidate_mismatched_craft_plans(manifest: dict[str, Any]) -> list[str]:
    """Reset done/skipped prompt.craft (+ cascade) when plan consumer_role mismatches command."""
    roots: list[str] = []
    for task in tasks_list(manifest):
        if task.get("status") not in (TASK_DONE, TASK_SKIPPED):
            continue
        if _expected_craft_consumer_role(task) is None:
            continue
        rel = _primary_artifact_rel(task)
        if not rel or not _artifact_exists(_REPO_ROOT, rel):
            continue
        if not _craft_plan_matches_task(task, rel):
            roots.append(str(task["id"]))

    if not roots:
        return []

    by_id = {t["id"]: t for t in tasks_list(manifest)}
    reset_ids: list[str] = []
    seen: set[str] = set()
    stack = list(roots)
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


def _load_handoff_json(cli_rel: str) -> dict[str, Any] | None:
    path = (_CLI_DIR / cli_rel).resolve()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _brief_path_from_manifest(manifest: dict[str, Any]) -> Path | None:
    brief_rel = str(manifest.get("brief") or "").strip()
    if not brief_rel:
        return None
    brief_path = (_REPO_ROOT / brief_rel).resolve()
    return brief_path if brief_path.is_file() else None


def _load_generation_context(manifest: dict[str, Any]) -> tuple[ProjectContext, list[AssetSpec], dict[str, dict[str, Any]]] | None:
    brief_path = _brief_path_from_manifest(manifest)
    if brief_path is None:
        return None
    from brief_shards import resolve_asset_specs

    project, assets, _ = load_brief_full(brief_path)
    spec_dicts: dict[str, dict[str, Any]] = {}
    for raw in resolve_asset_specs(brief_path):
        if not isinstance(raw, dict):
            continue
        aid = str(raw.get("id") or "").strip()
        if aid:
            spec_dicts[aid] = raw
        try:
            spec = AssetSpec.from_dict(raw)
            fk = resolve_asset_file_key(spec)
            if fk:
                spec_dicts[fk] = raw
        except ValueError:
            continue
    return project, assets, spec_dicts


def _find_prompt_craft_task(manifest: dict[str, Any], asset_id: str) -> dict[str, Any] | None:
    needle = str(asset_id or "").strip()
    if not needle:
        return None
    for task in tasks_list(manifest):
        if str(task.get("step") or "") != "prompt.craft":
            continue
        if str(task.get("asset_id") or "") == needle:
            return task
    return None


def _resolve_spec_for_asset_id(
    asset_id: str,
    assets: list[AssetSpec],
    task: dict[str, Any],
) -> tuple[AssetSpec | None, IconKitItem | None]:
    needle = str(asset_id or "").strip()
    arts = task.get("artifacts") if isinstance(task.get("artifacts"), dict) else {}
    kit_slug = str(arts.get("kit_item_slug") or "").strip()
    kit_id = str(arts.get("kit_item_id") or "").strip()

    for spec in assets:
        fk = resolve_asset_file_key(spec)
        if needle not in (fk, spec.id):
            continue
        kit_item: IconKitItem | None = None
        if kit_slug or kit_id:
            slugs = unique_kit_item_slugs(spec.items)
            for item, slug in zip(spec.items, slugs, strict=False):
                if kit_slug and slug == kit_slug:
                    kit_item = item
                    break
                if kit_id and item.id == kit_id:
                    kit_item = item
                    break
            if kit_item is None and kit_id:
                kit_item = find_icon_kit_item(spec, kit_id)
        return spec, kit_item

    if "__" in needle:
        base, slug = needle.rsplit("__", 1)
        for spec in assets:
            if resolve_asset_file_key(spec) != base:
                continue
            slugs = unique_kit_item_slugs(spec.items)
            for item, item_slug in zip(spec.items, slugs, strict=False):
                if item_slug == slug or item.id == slug:
                    return spec, item
    return None, None


def is_asset_generation_stale(
    manifest: dict[str, Any],
    asset_id: str,
    *,
    project: ProjectContext,
    assets: list[AssetSpec],
    spec_dicts: dict[str, dict[str, Any]],
) -> bool:
    prompt_task = _find_prompt_craft_task(manifest, asset_id)
    if prompt_task is None:
        return False
    arts = prompt_task.get("artifacts") if isinstance(prompt_task.get("artifacts"), dict) else {}
    plan_rel = str(arts.get("plan") or "").strip()
    if not plan_rel:
        return False
    handoff = _load_handoff_json(plan_rel)
    if handoff is None:
        return False
    spec, kit_item = _resolve_spec_for_asset_id(asset_id, assets, prompt_task)
    if spec is None:
        return False
    raw_shard = spec_dicts.get(asset_id) or spec_dicts.get(spec.id) or spec_dicts.get(resolve_asset_file_key(spec))
    current = build_generation_input(
        spec,
        project,
        kit_item=kit_item,
        raw_shard=raw_shard,
    )
    return is_handoff_generation_stale(handoff, current)


def invalidate_stale_generation_inputs(manifest: dict[str, Any]) -> list[str]:
    """Reset done/skipped prompt.craft + dependents when brief/spec inputs changed."""
    ctx = _load_generation_context(manifest)
    if ctx is None:
        return []
    project, assets, spec_dicts = ctx
    stale_roots: list[str] = []
    for task in tasks_list(manifest):
        if task.get("status") not in (TASK_DONE, TASK_SKIPPED):
            continue
        if str(task.get("step") or "") != "prompt.craft":
            continue
        asset_id = str(task.get("asset_id") or "").strip()
        if not asset_id:
            continue
        if is_asset_generation_stale(
            manifest,
            asset_id,
            project=project,
            assets=assets,
            spec_dicts=spec_dicts,
        ):
            stale_roots.append(str(task["id"]))

    if not stale_roots:
        return []

    by_id = {t["id"]: t for t in tasks_list(manifest)}
    reset_ids: list[str] = []
    seen: set[str] = set()
    stack = list(stale_roots)
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

    purged = purge_stale_task_artifacts(manifest, reset_ids)

    from assets_manifest import refresh_assets_manifest_from_pipeline

    refresh_assets_manifest_from_pipeline(manifest, invalidated_task_ids=reset_ids)
    if purged:
        manifest.setdefault("meta", {})["last_stale_purge"] = {
            "at": _utc_now(),
            "paths": purged[:200],
            "count": len(purged),
        }
    return reset_ids


def _reset_task_to_pending(task: dict[str, Any]) -> None:
    task["status"] = TASK_PENDING
    task["result"] = None
    task["started_at"] = None
    task["finished_at"] = None


_ARTIFACT_PURGE_KEYS = frozenset(
    {
        "plan",
        "output",
        "output_dir",
        "nobg_image",
        "video",
        "dev_handoff",
        "assemble_file",
        "input",
        "input_dir",
        "frames_dir",
        "plan_file",
    }
)

# Produced by this task — safe to delete on stale invalidation.
# NOTE: `plan` is only produced by prompt.craft; generate lists it as an input.
# `input` / `input_dir` are always upstream — cascade deletes them via the producer.
_ARTIFACT_PURGE_ARTIFACT_KEYS = frozenset(
    {
        "plan",
        "output",
        "output_dir",
        "nobg_image",
        "video",
        "dev_handoff",
        "frames_dir",
        "plan_file",
    }
)

# Cross-asset / upstream inputs — never delete from this task's artifact map.
_ARTIFACT_PURGE_SKIP_ARTIFACT_KEYS = frozenset(
    {
        "reference_image",
        "kit_style_reference",
        "kit_style_anchor_slug",
        "input",
        "input_dir",
        # Written at pipeline plan time; assemble/dev-context only consume it.
        "assemble_file",
        "project_path",
    }
)

# Keys that look like outputs but are only owned by prompt.craft.
_ARTIFACT_PURGE_CRAFT_ONLY_KEYS = frozenset({"plan", "plan_file"})


def _collect_task_artifact_rels(task: dict[str, Any]) -> list[str]:
    """Cli-relative artifact paths to delete when a task is invalidated."""
    seen: set[str] = set()
    out: list[str] = []
    step = str(task.get("step") or "")
    is_craft = step == "prompt.craft" or step.endswith(".prompt.craft")

    def add(raw: Any) -> None:
        rel = str(raw or "").strip().replace("\\", "/")
        if not rel or rel in seen:
            return
        seen.add(rel)
        out.append(rel)

    arts = task.get("artifacts")
    if isinstance(arts, dict):
        for key, val in arts.items():
            key_s = str(key or "")
            if key_s in _ARTIFACT_PURGE_SKIP_ARTIFACT_KEYS:
                continue
            if key_s in _ARTIFACT_PURGE_CRAFT_ONLY_KEYS and not is_craft:
                continue
            if key_s in _ARTIFACT_PURGE_ARTIFACT_KEYS:
                add(val)

    result = task.get("result")
    if isinstance(result, dict):
        for key in _ARTIFACT_PURGE_KEYS:
            if key in _ARTIFACT_PURGE_SKIP_ARTIFACT_KEYS:
                continue
            if key in _ARTIFACT_PURGE_CRAFT_ONLY_KEYS and not is_craft:
                continue
            add(result.get(key))

    return out


def purge_stale_task_artifacts(
    manifest: dict[str, Any],
    task_ids: list[str],
) -> list[str]:
    """Delete on-disk artifacts for invalidated pipeline tasks.

    Stale brief inputs mean deliverables are obsolete — remove them so UI/disk
    match manifest pending state and the next run starts clean.
    """
    if not task_ids:
        return []
    by_id = {t["id"]: t for t in tasks_list(manifest)}
    removed: list[str] = []
    for tid in task_ids:
        task = by_id.get(tid)
        if task is None:
            continue
        for rel in _collect_task_artifact_rels(task):
            path = (_CLI_DIR / rel).resolve()
            try:
                if path.is_file():
                    path.unlink()
                    removed.append(rel)
                elif path.is_dir():
                    shutil.rmtree(path)
                    removed.append(rel)
            except OSError:
                continue
    return removed


def purge_obsolete_generation_artifacts(manifest: dict[str, Any]) -> list[str]:
    """Delete on-disk deliverables for assets whose handoff no longer matches brief.

    Runs even when tasks are already pending (e.g. after a prior stale reset left files).
    """
    ctx = _load_generation_context(manifest)
    if ctx is None:
        return []
    project, assets, spec_dicts = ctx
    stale_assets: set[str] = set()
    for task in tasks_list(manifest):
        if str(task.get("step") or "") != "prompt.craft":
            continue
        asset_id = str(task.get("asset_id") or "").strip()
        if not asset_id:
            continue
        if is_asset_generation_stale(
            manifest,
            asset_id,
            project=project,
            assets=assets,
            spec_dicts=spec_dicts,
        ):
            stale_assets.add(asset_id)
    if not stale_assets:
        return []
    purge_ids: list[str] = []
    for task in tasks_list(manifest):
        asset_id = str(task.get("asset_id") or "").strip()
        if asset_id in stale_assets:
            purge_ids.append(str(task["id"]))
    return purge_stale_task_artifacts(manifest, purge_ids)


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
        if not _primary_artifact_ready(task, rel):
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
    """Sync task status with disk: stale brief inputs → pending; missing outputs → pending;
    existing valid outputs → done.

    Returns counts including stale invalidation from changed spec/description/sizing.
    """
    _ = repo_root
    stale_ids = invalidate_stale_generation_inputs(manifest)
    purged_obsolete = purge_obsolete_generation_artifacts(manifest)
    mismatched_ids = invalidate_mismatched_craft_plans(manifest)
    invalidated_ids = invalidate_missing_artifacts(manifest)
    # Include role-mismatch resets in the same invalidated list for callers.
    invalidated_ids = list(dict.fromkeys([*mismatched_ids, *invalidated_ids]))
    purged_count = 0
    meta = manifest.get("meta") if isinstance(manifest.get("meta"), dict) else {}
    purge_meta = meta.get("last_stale_purge")
    if isinstance(purge_meta, dict):
        purged_count = int(purge_meta.get("count") or 0)
    if purged_obsolete:
        purged_count += len(purged_obsolete)
        manifest.setdefault("meta", {})["last_stale_purge"] = {
            "at": _utc_now(),
            "paths": purged_obsolete[:200],
            "count": len(purged_obsolete),
        }
    promoted = 0
    by_id = {t["id"]: t for t in tasks_list(manifest)}
    gen_ctx = _load_generation_context(manifest)

    for task in tasks_list(manifest):
        if task.get("status") != TASK_PENDING:
            continue
        if not _deps_satisfied(task, by_id):
            continue
        # Must match invalidate: only the primary deliverable counts (not plan alone).
        rel = _primary_artifact_rel(task)
        if not rel or not _primary_artifact_ready(task, rel):
            continue
        if not _craft_plan_matches_task(task, rel):
            continue
        asset_id = str(task.get("asset_id") or "").strip()
        if gen_ctx and asset_id:
            project, assets, spec_dicts = gen_ctx
            if is_asset_generation_stale(
                manifest,
                asset_id,
                project=project,
                assets=assets,
                spec_dicts=spec_dicts,
            ):
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
        "stale_invalidated": len(stale_ids),
        "stale_invalidated_ids": stale_ids,
        "stale_purged": purged_count,
        "invalidated": len(invalidated_ids),
        "promoted": promoted,
        "invalidated_ids": invalidated_ids,
        "total": len(stale_ids) + len(invalidated_ids) + promoted,
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


def rewrite_godot_assemble_handoff(manifest: dict[str, Any]) -> str | None:
    """Regenerate plans/godot_<brief>.json from the brief + current task artifacts.

    The assemble handoff is written at ``pipeline plan`` time. Cascade resets used to
    delete it (assemble_file listed as an assemble artifact), leaving
    ``godot.assemble`` stuck in a missing-file heal loop. Call this to restore it.
    Returns the cli-relative path written, or None if Godot is not in the manifest.
    """
    from types import SimpleNamespace

    from brief import load_brief_full
    from project_paths import default_paths_for_brief

    brief_rel = str(manifest.get("brief") or "").strip()
    if not brief_rel:
        return None
    brief_path = (_REPO_ROOT / brief_rel).resolve()
    if not brief_path.is_file():
        return None

    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    defaults = default_paths_for_brief(brief_path)
    plans_dir = Path(str(paths.get("plans_dir") or defaults["plans_dir"]))
    output_dir = Path(str(paths.get("output_dir") or defaults["output_dir"]))
    if not plans_dir.is_absolute():
        plans_dir = (_REPO_ROOT / plans_dir).resolve()
    else:
        plans_dir = plans_dir.resolve()
    if not output_dir.is_absolute():
        output_dir = (_REPO_ROOT / output_dir).resolve()
    else:
        output_dir = output_dir.resolve()

    godot_rel = str(manifest.get("godot_project") or "").strip()
    if godot_rel:
        godot_project = (_REPO_ROOT / godot_rel).resolve()
    else:
        godot_project = Path(defaults["godot_project"]).resolve()

    project, assets, _graphs = load_brief_full(brief_path)
    assets = [a for a in assets if not _is_placeholder_asset(a)]
    meta = manifest.get("meta") if isinstance(manifest.get("meta"), dict) else {}
    max_wave = meta.get("production_max_wave")
    if max_wave is not None:
        try:
            mw = int(max_wave)
        except (TypeError, ValueError):
            mw = None
        if mw is not None:
            assets = [
                a for a in assets if int(getattr(a, "production_wave", 1) or 1) <= mw
            ]

    tasks_by_id = {
        str(t.get("id") or ""): SimpleNamespace(artifacts=t.get("artifacts") or {})
        for t in tasks_list(manifest)
        if t.get("id")
    }
    godot_plan = _collect_godot_plan(
        brief_stem=brief_path.stem,
        project=project,
        assets=assets,
        output_dir=output_dir,
        tasks_by_id=tasks_by_id,  # type: ignore[arg-type]
        godot_project=godot_project,
        plans_dir=plans_dir,
    )
    if (
        not godot_plan.get("animations")
        and not godot_plan.get("backgrounds")
        and not godot_plan.get("idle_still")
        and not godot_plan.get("props")
        and not (
            isinstance(godot_plan.get("layout"), dict)
            and godot_plan["layout"].get("placements")
        )
    ):
        return None

    handoff_path = plans_dir / f"godot_{brief_path.stem}.json"
    save_handoff(handoff_path, build_godot_handoff(godot_plan))
    cli_rel = cli_relative(handoff_path)
    manifest["godot_assemble_file"] = cli_rel
    manifest["godot_project"] = rel_to_repo(godot_project.resolve())
    return cli_rel
