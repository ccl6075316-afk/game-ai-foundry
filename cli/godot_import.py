"""Import PNG frame sequences into Godot projects as SpriteFrames .tres resources."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from frame_sequence import process_frame_sequence, resolve_transition_trim


class GodotImportError(RuntimeError):
    pass


def _sanitize_id(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return safe or "frame"


def import_sprite_frames(
    project_path: Path,
    *,
    asset: str,
    input_dir: Path,
    pattern: str = "frame_*.png",
    fps: float = 12.0,
    animation_name: str | None = None,
    loop: bool = True,
    skip_lead_frames: int = 0,
    skip_trail_frames: int = 0,
    skip_lead_ratio: float | None = None,
    skip_trail_ratio: float | None = None,
    sample_frames: int | None = None,
    pre_trimmed: bool = False,
    pre_sampled: bool = False,
    trim_lead: bool | None = None,
    trim_trail: bool | None = None,
    config: dict | None = None,
    handoff: dict | None = None,
) -> dict[str, str]:
    """Trim i2v transition frames (optional), sample, then copy into project."""
    project_path = project_path.resolve()
    input_dir = input_dir.resolve()

    if not project_path.is_dir():
        raise GodotImportError(f"Project not found: {project_path}")
    if not input_dir.is_dir():
        raise GodotImportError(f"Input dir not found: {input_dir}")

    all_frames = sorted(input_dir.glob(pattern))
    if not all_frames:
        raise GodotImportError(f"No files matching {pattern} in {input_dir}")

    trim_opts = resolve_transition_trim(
        config or {},
        scope="import",
        handoff=handoff,
        trim_lead=trim_lead,
        trim_trail=trim_trail,
        skip_lead_ratio=skip_lead_ratio,
        skip_trail_ratio=skip_trail_ratio,
    )
    lead_ratio, trail_ratio = trim_opts.as_skip_ratios()

    try:
        frames, meta = process_frame_sequence(
            all_frames,
            skip_lead_ratio=lead_ratio,
            skip_trail_ratio=trail_ratio,
            skip_lead_frames=skip_lead_frames,
            skip_trail_frames=skip_trail_frames,
            sample_frames=sample_frames,
            pre_trimmed=pre_trimmed,
            pre_sampled=pre_sampled,
            trim_lead=trim_opts.trim_lead,
            trim_trail=trim_opts.trim_trail,
        )
    except ValueError as exc:
        raise GodotImportError(str(exc)) from exc

    anim_name = animation_name or asset
    dest_dir = project_path / "assets" / "sprites" / asset
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied: list[tuple[str, Path]] = []
    for idx, src in enumerate(frames, start=1):
        dest = dest_dir / f"frame_{idx:04d}{src.suffix}"
        shutil.copy2(src, dest)
        rel = dest.relative_to(project_path).as_posix()
        copied.append((rel, dest))

    tres_path = project_path / "assets" / "sprites" / f"{asset}_frames.tres"
    tres_rel = tres_path.relative_to(project_path).as_posix()
    tres_content = _build_sprite_frames_tres(copied, animation_name=anim_name, fps=fps, loop=loop)
    tres_path.write_text(tres_content, encoding="utf-8")

    return {
        "asset": asset,
        "animation_name": anim_name,
        "frame_count": str(len(copied)),
        "input_frame_count": str(meta["input_count"]),
        "lead_dropped": str(meta["lead_dropped"]),
        "trail_dropped": str(meta["trail_dropped"]),
        "sampled_to": str(meta["sampled_to"]) if meta["sampled_to"] else "",
        "trim_lead": str(trim_opts.trim_lead).lower(),
        "trim_trail": str(trim_opts.trim_trail).lower(),
        "frames_dir": dest_dir.relative_to(project_path).as_posix(),
        "sprite_frames": tres_rel,
    }


def _build_sprite_frames_tres(
    frames: list[tuple[str, Path]],
    *,
    animation_name: str,
    fps: float,
    loop: bool,
) -> str:
    """Write Godot 4 text SpriteFrames resource."""
    load_steps = len(frames) + 1
    lines: list[str] = [
        f'[gd_resource type="SpriteFrames" load_steps={load_steps} format=3]',
        "",
    ]

    ext_ids: list[str] = []
    for idx, (rel_path, _) in enumerate(frames, start=1):
        ext_id = f"{idx}_{_sanitize_id(Path(rel_path).stem)}"
        ext_ids.append(ext_id)
        lines.append(f'[ext_resource type="Texture2D" path="res://{rel_path}" id="{ext_id}"]')
        lines.append("")

    frame_entries: list[str] = []
    for ext_id in ext_ids:
        frame_entries.append(
            "{" + f'"duration": 1.0, "texture": ExtResource("{ext_id}")' + "}"
        )

    loop_str = "true" if loop else "false"
    lines.extend(
        [
            "[resource]",
            "animations = [{",
            '"frames": [',
            ", ".join(frame_entries),
            "],",
            f'"loop": {loop_str},',
            f'"name": &"{animation_name}",',
            f'"speed": {float(fps)}',
            "}]",
        ]
    )
    return "\n".join(lines) + "\n"


def copy_background_image(
    project_path: Path,
    *,
    asset: str,
    image_path: Path,
) -> str:
    """Copy a background PNG into assets/backgrounds/."""
    project_path = project_path.resolve()
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise GodotImportError(f"Background image not found: {image_path}")

    dest_dir = project_path / "assets" / "backgrounds"
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = image_path.suffix or ".png"
    dest = dest_dir / f"{asset}{ext}"
    shutil.copy2(image_path, dest)
    return dest.relative_to(project_path).as_posix()


def copy_idle_still(
    project_path: Path,
    *,
    image_path: Path,
    asset: str = "idle_still",
) -> str:
    """Copy a separate character still for idle display (NOT the i2v reference or anim frame 0)."""
    project_path = project_path.resolve()
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise GodotImportError(f"Idle still not found: {image_path}")

    dest_dir = project_path / "assets" / "sprites"
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = image_path.suffix or ".png"
    dest = dest_dir / f"{asset}{ext}"
    shutil.copy2(image_path, dest)
    return dest.relative_to(project_path).as_posix()
