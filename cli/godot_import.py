"""Import PNG frame sequences into Godot projects as SpriteFrames .tres resources."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from frame_sequence import process_frame_sequence, resolve_transition_trim
from display_size import DisplaySize, parse_display_size


def _parse_display_arg(raw: Any) -> DisplaySize | None:
    if isinstance(raw, dict):
        return parse_display_size(raw)
    if isinstance(raw, DisplaySize):
        return raw if not raw.is_empty() else None
    return parse_display_size(raw)


def save_texture_at_display_size(
    src: Path,
    dest: Path,
    display: DisplaySize | None,
) -> None:
    """Resize to in-game display pixels (godogen Size column); Godot scale stays 1."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if display is None or display.is_empty():
        shutil.copy2(src, dest)
        return
    try:
        from PIL import Image
    except ImportError as exc:
        raise GodotImportError("Pillow required to resize assets to display_size") from exc
    img = Image.open(src)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    resized = img.resize((display.width, display.height), Image.Resampling.LANCZOS)
    resized.save(dest, format="PNG")


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
    display_size: Any = None,
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

    display = _parse_display_arg(display_size)
    if display is None and isinstance(handoff, dict):
        display = _parse_display_arg(handoff.get("display_size"))

    copied: list[tuple[str, Path]] = []
    for idx, src in enumerate(frames, start=1):
        dest = dest_dir / f"frame_{idx:04d}{src.suffix}"
        save_texture_at_display_size(src, dest, display)
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


def _extract_animation_blocks(text: str) -> list[str]:
    """Pull each animation dict from a SpriteFrames .tres file."""
    marker = "animations = [{"
    start = text.find(marker)
    if start < 0:
        return []

    pos = start + len("animations = [")
    blocks: list[str] = []
    depth = 0
    block_start: int | None = None
    for i in range(pos, len(text)):
        ch = text[i]
        if ch == "{":
            if depth == 0:
                block_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and block_start is not None:
                blocks.append(text[block_start : i + 1])
                block_start = None
    return blocks


def merge_sprite_frames_tres(
    project_path: Path,
    imports: list[dict[str, str]],
    *,
    output_asset: str,
) -> dict[str, str]:
    """Merge multiple single-animation SpriteFrames .tres into one resource."""
    if not imports:
        raise GodotImportError("merge_sprite_frames_tres requires at least one import")
    if len(imports) == 1:
        return imports[0]

    project_path = project_path.resolve()
    all_ext: list[str] = []
    all_anims: list[str] = []
    next_idx = 1

    for imp in imports:
        tres_rel = imp.get("sprite_frames", "")
        if not tres_rel:
            continue
        tres_path = project_path / tres_rel
        if not tres_path.is_file():
            raise GodotImportError(f"SpriteFrames not found: {tres_path}")
        text = tres_path.read_text(encoding="utf-8")

        local_id_map: dict[str, str] = {}
        for line in text.splitlines():
            if not line.startswith("[ext_resource"):
                continue
            old_id_match = re.search(r'id="([^"]+)"', line)
            if not old_id_match:
                continue
            old_id = old_id_match.group(1)
            new_id = f"{next_idx}_{_sanitize_id(old_id)}"
            local_id_map[old_id] = new_id
            new_line = re.sub(r'id="[^"]+"', f'id="{new_id}"', line)
            all_ext.append(new_line)
            next_idx += 1

        for anim_block in _extract_animation_blocks(text):
            remapped = anim_block
            for old_id, new_id in local_id_map.items():
                remapped = remapped.replace(f'ExtResource("{old_id}")', f'ExtResource("{new_id}")')
            all_anims.append(remapped)

    if not all_anims:
        raise GodotImportError("No animations found to merge")

    load_steps = len(all_ext) + 1
    lines: list[str] = [
        f'[gd_resource type="SpriteFrames" load_steps={load_steps} format=3]',
        "",
    ]
    for ext_line in all_ext:
        lines.append(ext_line)
        lines.append("")

    lines.extend(
        [
            "[resource]",
            "animations = [" + ", ".join(all_anims) + "]",
        ]
    )

    tres_path = project_path / "assets" / "sprites" / f"{output_asset}_frames.tres"
    tres_path.parent.mkdir(parents=True, exist_ok=True)
    tres_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tres_rel = tres_path.relative_to(project_path).as_posix()

    anim_names = [imp.get("animation_name", imp.get("asset", "")) for imp in imports]
    return {
        "asset": output_asset,
        "animation_name": ",".join(anim_names),
        "frame_count": str(sum(int(imp.get("frame_count", "0") or 0) for imp in imports)),
        "sprite_frames": tres_rel,
        "merged_from": ",".join(imp.get("asset", "") for imp in imports),
    }


def import_still_as_animation(
    project_path: Path,
    *,
    asset: str,
    image_path: Path,
    animation_name: str = "walk",
    fps: float = 12.0,
    display_size: Any = None,
) -> dict[str, str]:
    """Build a one-frame SpriteFrames resource from a static character still."""
    project_path = project_path.resolve()
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise GodotImportError(f"Still image not found: {image_path}")

    dest_dir = project_path / "assets" / "sprites" / asset
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"frame_0001{image_path.suffix or '.png'}"
    save_texture_at_display_size(image_path, dest, _parse_display_arg(display_size))
    rel = dest.relative_to(project_path).as_posix()

    tres_path = project_path / "assets" / "sprites" / f"{asset}_frames.tres"
    tres_rel = tres_path.relative_to(project_path).as_posix()
    tres_path.write_text(
        _build_sprite_frames_tres([(rel, dest)], animation_name=animation_name, fps=fps, loop=True),
        encoding="utf-8",
    )
    return {
        "asset": asset,
        "animation_name": animation_name,
        "frame_count": "1",
        "sprite_frames": tres_rel,
        "frames_dir": dest_dir.relative_to(project_path).as_posix(),
    }


def copy_background_image(
    project_path: Path,
    *,
    asset: str,
    image_path: Path,
    display_size: Any = None,
) -> str:
    """Copy a background image into assets/backgrounds/ (always as PNG for Godot)."""
    project_path = project_path.resolve()
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise GodotImportError(f"Background image not found: {image_path}")

    dest_dir = project_path / "assets" / "backgrounds"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{asset}.png"
    display = _parse_display_arg(display_size)
    if display is None:
        header = image_path.read_bytes()[:8]
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            shutil.copy2(image_path, dest)
        else:
            try:
                from PIL import Image
            except ImportError as exc:
                raise GodotImportError(
                    f"Background is not PNG ({image_path}); install Pillow to convert."
                ) from exc
            Image.open(image_path).save(dest, format="PNG")
    else:
        save_texture_at_display_size(image_path, dest, display)

    return dest.relative_to(project_path).as_posix()


def copy_idle_still(
    project_path: Path,
    *,
    image_path: Path,
    asset: str = "idle_still",
    display_size: Any = None,
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
    save_texture_at_display_size(image_path, dest, _parse_display_arg(display_size))
    return dest.relative_to(project_path).as_posix()
