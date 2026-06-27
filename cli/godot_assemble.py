"""Assemble Godot .NET projects from godot-assembler handoff plans."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from godot_import import GodotImportError, copy_background_image, copy_idle_still, import_sprite_frames, import_still_as_animation

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_DOTNET = _REPO_ROOT / "resources" / "godot-templates" / "dotnet"
_TEMPLATE_DEFAULT = _REPO_ROOT / "resources" / "godot-templates" / "default"
_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"


class GodotAssembleError(RuntimeError):
    pass


def resolve_template_dir(template: str) -> Path:
    if template == "dotnet":
        return _TEMPLATE_DOTNET
    if template in ("default", "empty"):
        return _TEMPLATE_DEFAULT
    raise GodotAssembleError(f"Unknown template '{template}'. Use: dotnet, default")


def _load_config() -> dict[str, Any]:
    if not _CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def init_project_from_template(
    project_path: Path,
    *,
    project_name: str,
    template: str = "dotnet",
) -> None:
    """Copy template tree into project_path if it does not exist."""
    project_path = project_path.resolve()
    if project_path.exists() and any(project_path.iterdir()):
        return

    template_dir = resolve_template_dir(template)
    if not template_dir.is_dir():
        raise GodotAssembleError(f"Template missing: {template_dir}")

    project_path.mkdir(parents=True, exist_ok=True)
    for item in template_dir.iterdir():
        dest = project_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    godot_file = project_path / "project.godot"
    if godot_file.is_file():
        content = godot_file.read_text(encoding="utf-8")
        content = content.replace('config/name="Game"', f'config/name="{project_name}"')
        godot_file.write_text(content, encoding="utf-8")


def _resolve_repo_path(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p.resolve()
    return (_REPO_ROOT / path_str).resolve()


def wire_main_scene(
    project_path: Path,
    *,
    sprite_frames_res: str | None = None,
    background_res: str | None = None,
    idle_still_res: str | None = None,
    main_scene: str = "scenes/main.tscn",
) -> None:
    """Write main.tscn with Player + AnimatedSprite2D + optional idle still + background."""
    scene_path = project_path / main_scene
    scene_path.parent.mkdir(parents=True, exist_ok=True)

    load_steps = 2
    if sprite_frames_res:
        load_steps += 1
    if background_res:
        load_steps += 1
    if idle_still_res:
        load_steps += 1

    lines = [
        f'[gd_scene load_steps={load_steps} format=3 uid="uid://gamefactory_main"]',
        "",
        '[ext_resource type="Script" path="res://scripts/Main.cs" id="1_main"]',
        '[ext_resource type="Script" path="res://scripts/Player.cs" id="2_player"]',
    ]
    next_id = 3
    frames_ext = ""
    if sprite_frames_res:
        lines.append(f'[ext_resource type="SpriteFrames" path="res://{sprite_frames_res}" id="3_frames"]')
        frames_ext = 'sprite_frames = ExtResource("3_frames")'
        next_id = 4
    bg_ext = ""
    if background_res:
        lines.append(f'[ext_resource type="Texture2D" path="res://{background_res}" id="{next_id}_bg"]')
        bg_ext = f'\ntexture = ExtResource("{next_id}_bg")'
        next_id += 1

    idle_ext = ""
    if idle_still_res:
        lines.append(f'[ext_resource type="Texture2D" path="res://{idle_still_res}" id="{next_id}_idle"]')
        idle_ext = f'\ntexture = ExtResource("{next_id}_idle")'

    lines.extend(
        [
            "",
            '[node name="Main" type="Node2D"]',
            'script = ExtResource("1_main")',
            "",
            '[node name="Background" type="Sprite2D" parent="."]',
            "position = Vector2(640, 360)" + bg_ext,
            "",
            '[node name="Player" type="CharacterBody2D" parent="."]',
            "position = Vector2(640, 400)",
            'script = ExtResource("2_player")',
            "",
            '[node name="IdleStill" type="Sprite2D" parent="Player"]' + idle_ext,
            "",
            '[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="Player"]',
            "visible = false",
            frames_ext,
            "",
            '[node name="Camera2D" type="Camera2D" parent="Player"]',
            "",
        ]
    )
    scene_path.write_text("\n".join(lines), encoding="utf-8")


def assemble_from_plan(plan: dict[str, Any], *, repo_root: Path | None = None) -> dict[str, Any]:
    """Execute godot-assembler plan dict."""
    root = repo_root or _REPO_ROOT
    config = _load_config()
    video_cfg = config.get("video", {}) if isinstance(config.get("video"), dict) else {}
    split_cfg = video_cfg.get("split_frames", {}) if isinstance(video_cfg.get("split_frames"), dict) else {}
    default_sample_frames = split_cfg.get("frames")

    project_rel = str(plan.get("project_path", "games/demo"))
    project_path = (root / project_rel).resolve()
    project_name = str(plan.get("project_name", "Game Factory Demo"))
    template = str(plan.get("template", "dotnet"))
    main_scene = str(plan.get("main_scene", "scenes/main.tscn"))

    init_project_from_template(project_path, project_name=project_name, template=template)

    results: dict[str, Any] = {
        "project_path": str(project_path),
        "animations": [],
        "backgrounds": [],
    }

    primary_sf: str | None = None
    animations = plan.get("animations") or []
    if not isinstance(animations, list):
        raise GodotAssembleError("plan.animations must be a list")

    for item in animations:
        if not isinstance(item, dict):
            continue
        asset = str(item.get("asset", "anim"))
        frames_dir = _resolve_repo_path(str(item["frames_dir"]))
        fps = float(item.get("fps", 12))
        anim_name = str(item.get("animation_name", asset))
        skip_frames = int(item.get("skip_lead_frames", 0))
        trail_frames = int(item.get("skip_trail_frames", 0))
        sample = item.get("sprite_frames", item.get("sample_frames", default_sample_frames))
        sample_frames = int(sample) if sample is not None else None
        pre_trimmed = bool(item.get("pre_trimmed", False))
        pre_sampled = bool(item.get("pre_sampled", False))
        trim_lead = item.get("trim_lead")
        trim_trail = item.get("trim_trail")
        try:
            imp = import_sprite_frames(
                project_path,
                asset=asset,
                input_dir=frames_dir,
                fps=fps,
                animation_name=anim_name,
                skip_lead_frames=skip_frames,
                skip_trail_frames=trail_frames,
                sample_frames=sample_frames,
                pre_trimmed=pre_trimmed,
                pre_sampled=pre_sampled,
                trim_lead=trim_lead if trim_lead is not None else None,
                trim_trail=trim_trail if trim_trail is not None else None,
                config=config,
                handoff=item,
            )
        except GodotImportError as exc:
            raise GodotAssembleError(str(exc)) from exc
        results["animations"].append(imp)
        if primary_sf is None:
            primary_sf = imp["sprite_frames"]

    backgrounds = plan.get("backgrounds") or []
    primary_bg: str | None = None
    if isinstance(backgrounds, list):
        for item in backgrounds:
            if not isinstance(item, dict):
                continue
            asset = str(item.get("asset", "bg"))
            img = _resolve_repo_path(str(item["image"]))
            try:
                rel = copy_background_image(project_path, asset=asset, image_path=img)
            except GodotImportError as exc:
                raise GodotAssembleError(str(exc)) from exc
            results["backgrounds"].append({"asset": asset, "path": rel})
            if primary_bg is None:
                primary_bg = rel

    idle_still_res: str | None = None
    idle_still_src: Path | None = None
    idle_still = plan.get("idle_still")
    if isinstance(idle_still, str) and idle_still.strip():
        idle_still_src = _resolve_repo_path(idle_still)
        try:
            idle_still_res = copy_idle_still(
                project_path,
                image_path=idle_still_src,
            )
        except GodotImportError as exc:
            raise GodotAssembleError(str(exc)) from exc
        results["idle_still"] = idle_still_res

    if primary_sf is None and idle_still_src is not None and idle_still_src.is_file():
        static_asset = "hero"
        animations_list = plan.get("animations") or []
        if isinstance(animations_list, list) and animations_list:
            first = animations_list[0]
            if isinstance(first, dict) and first.get("asset"):
                static_asset = str(first["asset"])
        elif isinstance(idle_still, str):
            stem = Path(idle_still).stem.replace("_nobg", "")
            if stem:
                static_asset = stem
        try:
            imp = import_still_as_animation(
                project_path,
                asset=static_asset,
                image_path=idle_still_src,
                animation_name="walk",
            )
        except GodotImportError as exc:
            raise GodotAssembleError(str(exc)) from exc
        results["animations"].append(imp)
        primary_sf = imp["sprite_frames"]

    if primary_sf or idle_still_res:
        wire_main_scene(
            project_path,
            sprite_frames_res=primary_sf,
            background_res=primary_bg,
            idle_still_res=idle_still_res,
            main_scene=main_scene,
        )

    results["main_scene"] = main_scene
    results["sprite_frames"] = primary_sf
    return results
