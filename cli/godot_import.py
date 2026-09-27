"""Import PNG frame sequences into Godot projects as SpriteFrames .tres resources."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from frame_sequence import process_frame_sequence, resolve_transition_trim
from display_size import DisplaySize, parse_display_size

# Keep subject length stable across animation frames (avoid Seedance zoom → size flicker).
_STABLE_SUBJECT_FILL = 0.92
_STABLE_ALPHA_THRESHOLD = 16


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
    *,
    bake: bool = False,
) -> None:
    """Write texture to dest.

    By default (``bake=False``) keeps source pixels — ``display_size`` is size *intent*
    for runtime scale, not a bake target. Set ``bake=True`` for legacy downscale.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not bake or display is None or display.is_empty():
        _copy_image_as_png(src, dest)
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


def _copy_image_as_png(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    header = src.read_bytes()[:8]
    if header.startswith(b"\x89PNG\r\n\x1a\n") and dest.suffix.lower() == ".png":
        shutil.copy2(src, dest)
        return
    try:
        from PIL import Image
    except ImportError as exc:
        raise GodotImportError(
            f"Cannot convert {src} to PNG without Pillow"
        ) from exc
    Image.open(src).convert("RGBA").save(dest, format="PNG")


def resolve_bake_display_size(
    config: dict | None = None,
    *,
    bake_display_size: bool | None = None,
) -> bool:
    """Default off: import keeps source clarity; games scale at placement."""
    if bake_display_size is not None:
        return bool(bake_display_size)
    godot = (config or {}).get("godot", {})
    if not isinstance(godot, dict):
        return False
    return bool(godot.get("bake_display_size", False))


def native_subject_display_size(
    sources: list[Path],
    *,
    fill: float = _STABLE_SUBJECT_FILL,
    alpha_threshold: int = _STABLE_ALPHA_THRESHOLD,
) -> DisplaySize:
    """Canvas that fits the largest subject at ~1:1 pixels (fill margin)."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise GodotImportError("Pillow required for native subject sizing") from exc

    fill = max(0.5, min(1.0, float(fill)))
    ref_w = 1
    ref_h = 1
    for src in sources:
        img = Image.open(src).convert("RGBA")
        bbox = img.getchannel("A").point(
            lambda a, t=alpha_threshold: 255 if a > t else 0
        ).getbbox()
        if bbox is None:
            continue
        ref_w = max(ref_w, bbox[2] - bbox[0])
        ref_h = max(ref_h, bbox[3] - bbox[1])
    width = max(1, int(round(ref_w / fill)))
    height = max(1, int(round(ref_h / fill)))
    return DisplaySize(width, height)

def save_animation_frames_at_display_size(
    sources: list[Path],
    dest_dir: Path,
    display: DisplaySize,
    *,
    fill: float = _STABLE_SUBJECT_FILL,
    alpha_threshold: int = _STABLE_ALPHA_THRESHOLD,
    mode: str = "plate",
) -> list[Path]:
    """Fit animation frames onto a fixed display canvas.

    Modes:
    - ``plate`` (default): scale the whole RGBA plate uniformly (no content crop).
      Matches how the matted video frames look when browsed as full images.
    - ``clip_subject``: crop each subject, then apply one scale for the whole clip
      (largest subject width = length reference). Avoids per-frame upscaling.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise GodotImportError("Pillow required to resize assets to display_size") from exc

    if display.is_empty():
        raise GodotImportError("display_size required for stable animation import")
    if not sources:
        raise GodotImportError("No source frames to compose")

    dest_dir.mkdir(parents=True, exist_ok=True)
    mode_key = (mode or "plate").strip().lower()
    if mode_key in ("plate", "full", "canvas"):
        return _compose_frames_plate(sources, dest_dir, display)
    if mode_key in ("clip_subject", "clip", "subject"):
        return _compose_frames_clip_subject(
            sources,
            dest_dir,
            display,
            fill=fill,
            alpha_threshold=alpha_threshold,
        )
    raise GodotImportError(f"Unknown animation compose mode: {mode}")


def _compose_frames_plate(
    sources: list[Path],
    dest_dir: Path,
    display: DisplaySize,
) -> list[Path]:
    """Uniformly scale each full frame onto the display canvas (letterbox if needed)."""
    from PIL import Image

    dests: list[Path] = []
    for idx, src in enumerate(sources, start=1):
        img = Image.open(src).convert("RGBA")
        canvas = Image.new("RGBA", (display.width, display.height), (0, 0, 0, 0))
        dest = dest_dir / f"frame_{idx:04d}.png"
        if img.width < 1 or img.height < 1:
            canvas.save(dest, format="PNG")
            dests.append(dest)
            continue
        scale = min(display.width / img.width, display.height / img.height)
        new_w = max(1, int(round(img.width * scale)))
        new_h = max(1, int(round(img.height * scale)))
        fitted = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        x = (display.width - fitted.width) // 2
        y = (display.height - fitted.height) // 2
        canvas.paste(fitted, (x, y), fitted)
        canvas.save(dest, format="PNG")
        dests.append(dest)
    return dests


def _compose_frames_clip_subject(
    sources: list[Path],
    dest_dir: Path,
    display: DisplaySize,
    *,
    fill: float,
    alpha_threshold: int,
) -> list[Path]:
    """Crop subjects; one scale for the clip from the largest subject width."""
    from PIL import Image

    crops: list[Any] = []
    for src in sources:
        img = Image.open(src).convert("RGBA")
        alpha = img.getchannel("A")
        bbox = alpha.point(lambda a: 255 if a > alpha_threshold else 0).getbbox()
        crops.append(None if bbox is None else img.crop(bbox))

    if not any(c is not None for c in crops):
        raise GodotImportError("No opaque subject found in animation frames")

    fill = max(0.5, min(1.0, float(fill)))
    ref_w = max((c.width for c in crops if c is not None and c.width >= 1), default=1)
    ref_h = max((c.height for c in crops if c is not None and c.height >= 1), default=1)

    scale = (display.width * fill) / max(1.0, float(ref_w))
    if ref_h * scale > display.height:
        scale = display.height / float(ref_h)
    if ref_w * scale > display.width:
        scale = display.width / float(ref_w)

    dests: list[Path] = []
    for idx, crop in enumerate(crops, start=1):
        canvas = Image.new("RGBA", (display.width, display.height), (0, 0, 0, 0))
        dest = dest_dir / f"frame_{idx:04d}.png"
        if crop is None or crop.width < 1 or crop.height < 1:
            canvas.save(dest, format="PNG")
            dests.append(dest)
            continue
        new_w = max(1, int(round(crop.width * scale)))
        new_h = max(1, int(round(crop.height * scale)))
        new_w = min(new_w, display.width)
        new_h = min(new_h, display.height)
        fitted = crop.resize((new_w, new_h), Image.Resampling.LANCZOS)
        x = (display.width - fitted.width) // 2
        y = (display.height - fitted.height) // 2
        canvas.paste(fitted, (x, y), fitted)
        canvas.save(dest, format="PNG")
        dests.append(dest)
    return dests


def resolve_playback_fps(
    frame_count: int,
    *,
    source_duration_seconds: float | None = None,
    lead_ratio: float = 0.0,
    trail_ratio: float = 0.0,
    default_fps: float = 12.0,
) -> float:
    """Match SpriteFrames speed to the temporal span the frames were sampled from."""
    if frame_count < 1:
        return default_fps
    dur = float(source_duration_seconds or 0.0)
    if dur <= 0:
        return default_fps
    lead = max(0.0, min(0.9, float(lead_ratio or 0.0)))
    trail = max(0.0, min(0.9, float(trail_ratio or 0.0)))
    usable = dur * max(0.05, 1.0 - lead - trail)
    return max(1.0, round(frame_count / usable, 2))


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
    source_duration_seconds: float | None = None,
    stable_subject: bool = True,
    bake_display_size: bool | None = None,
) -> dict[str, str]:
    """Trim i2v transition frames (optional), sample, then copy into project.

    By default does **not** bake Brief ``display_size`` into PNG pixels. Multi-frame
    clips use clip_subject onto a native subject canvas (stable size, source clarity).
    Pass ``bake_display_size=True`` for legacy downscale-to-display behavior.
    """
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
    # Replace prior import so stale frames cannot linger.
    if dest_dir.is_dir():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    display = _parse_display_arg(display_size)
    if display is None and isinstance(handoff, dict):
        display = _parse_display_arg(handoff.get("display_size"))

    bake = resolve_bake_display_size(config, bake_display_size=bake_display_size)
    if isinstance(handoff, dict) and handoff.get("bake_display_size") is not None:
        bake = bool(handoff.get("bake_display_size"))

    duration = source_duration_seconds
    if duration is None and isinstance(handoff, dict):
        raw_dur = handoff.get("source_duration_seconds") or handoff.get("duration_seconds")
        try:
            duration = float(raw_dur) if raw_dur is not None else None
        except (TypeError, ValueError):
            duration = None

    # When frames already span the trimmed window, playback fps must match that span
    # (hardcoded 12fps makes ~4s / 24-frame clips play ~1.4–2× too fast).
    playback_fps = float(fps)
    if duration and duration > 0:
        ho = handoff if isinstance(handoff, dict) else {}
        play_lead = float(ho.get("skip_lead_ratio", lead_ratio) or 0.0)
        play_trail = float(ho.get("skip_trail_ratio", trail_ratio) or 0.0)
        if not pre_trimmed:
            if not trim_opts.trim_lead:
                play_lead = 0.0
            if not trim_opts.trim_trail:
                play_trail = 0.0
        playback_fps = resolve_playback_fps(
            len(frames),
            source_duration_seconds=duration,
            lead_ratio=play_lead,
            trail_ratio=play_trail,
            default_fps=playback_fps,
        )

    copied: list[tuple[str, Path]] = []
    if len(frames) > 1 and stable_subject:
        if bake and display is not None and not display.is_empty():
            canvas = display
            mode = "plate"
        else:
            canvas = native_subject_display_size(frames)
            mode = "clip_subject"
        dest_paths = save_animation_frames_at_display_size(
            frames, dest_dir, canvas, mode=mode
        )
        for dest in dest_paths:
            rel = dest.relative_to(project_path).as_posix()
            copied.append((rel, dest))
    else:
        for idx, src in enumerate(frames, start=1):
            dest = dest_dir / f"frame_{idx:04d}{src.suffix}"
            save_texture_at_display_size(src, dest, display, bake=bake)
            rel = dest.relative_to(project_path).as_posix()
            copied.append((rel, dest))

    tres_path = project_path / "assets" / "sprites" / f"{asset}_frames.tres"
    tres_rel = tres_path.relative_to(project_path).as_posix()
    tres_content = _build_sprite_frames_tres(
        copied, animation_name=anim_name, fps=playback_fps, loop=loop
    )
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
        "fps": str(playback_fps),
        "bake_display_size": str(bake).lower(),
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
    save_texture_at_display_size(
        image_path, dest, _parse_display_arg(display_size), bake=False
    )
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
        _copy_image_as_png(image_path, dest)
    else:
        # Backgrounds may still target viewport size when display_size is set.
        save_texture_at_display_size(image_path, dest, display, bake=True)

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
    save_texture_at_display_size(
        image_path, dest, _parse_display_arg(display_size), bake=False
    )
    return dest.relative_to(project_path).as_posix()


def copy_prop_image(
    project_path: Path,
    *,
    asset: str,
    image_path: Path,
    display_size: Any = None,
) -> str:
    """Copy a world prop texture into assets/props/{asset}_nobg.png."""
    from godot_layout import prop_texture_res_path

    project_path = project_path.resolve()
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise GodotImportError(f"Prop image not found: {image_path}")

    rel = prop_texture_res_path(asset)
    dest = project_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    save_texture_at_display_size(
        image_path, dest, _parse_display_arg(display_size), bake=False
    )
    return dest.relative_to(project_path).as_posix()
