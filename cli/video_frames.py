"""Video → sprite frame extraction settings and ffmpeg helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

DEFAULT_SPRITE_FRAMES = 8


class SplitFramesError(RuntimeError):
    """Invalid split-frames options or ffmpeg failure."""


def probe_video_duration(path: Path) -> float:
    """Return video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise SplitFramesError(f"ffprobe failed for {path}: {exc.stderr}") from exc
    except FileNotFoundError as exc:
        raise SplitFramesError("ffprobe not found — install ffmpeg") from exc

    text = result.stdout.strip()
    if not text:
        raise SplitFramesError(f"Could not read duration from {path}")
    try:
        duration = float(text)
    except ValueError as exc:
        raise SplitFramesError(f"Invalid duration from ffprobe: {text!r}") from exc
    if duration <= 0:
        raise SplitFramesError(f"Video duration must be positive, got {duration}")
    return duration


def _split_frames_config(config: dict[str, Any]) -> dict[str, Any]:
    video_cfg = config.get("video", {})
    if not isinstance(video_cfg, dict):
        return {}
    block = video_cfg.get("split_frames", {})
    return block if isinstance(block, dict) else {}


def resolve_split_frames_options(
    config: dict[str, Any],
    *,
    fps: float | None = None,
    frames: int | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Resolve extraction mode: fixed fps or target frame count across clip."""
    if fps is not None and frames is not None:
        raise SplitFramesError("Use either --fps or --frames, not both.")

    cfg = _split_frames_config(config)
    default_frames = int(cfg.get("frames", DEFAULT_SPRITE_FRAMES))
    default_fps = cfg.get("fps")

    if frames is not None:
        if frames < 1:
            raise SplitFramesError("--frames must be at least 1")
        return {
            "mode": "frames",
            "target_frames": int(frames),
            "extract_fps": None,
            "duration_hint": duration_seconds,
        }

    if fps is not None:
        if fps <= 0:
            raise SplitFramesError("--fps must be positive")
        return {
            "mode": "fps",
            "target_frames": None,
            "extract_fps": float(fps),
            "duration_hint": duration_seconds,
        }

    if default_fps is not None:
        parsed_fps = float(default_fps)
        if parsed_fps <= 0:
            raise SplitFramesError("config video.split_frames.fps must be positive")
        return {
            "mode": "fps",
            "target_frames": None,
            "extract_fps": parsed_fps,
            "duration_hint": duration_seconds,
        }

    if default_frames < 1:
        raise SplitFramesError("config video.split_frames.frames must be at least 1")
    return {
        "mode": "frames",
        "target_frames": default_frames,
        "extract_fps": None,
        "duration_hint": duration_seconds,
    }


def resolve_extract_fps(
    input_path: Path,
    options: dict[str, Any],
) -> tuple[float, float, int | None]:
    """Return (extract_fps, duration_seconds, target_frames_or_none)."""
    duration = options.get("duration_hint")
    if duration is None:
        duration = probe_video_duration(input_path)
    duration = float(duration)

    if options["mode"] == "fps":
        return float(options["extract_fps"]), duration, None

    target = int(options["target_frames"])
    extract_fps = target / duration
    return extract_fps, duration, target


def split_video_to_frames(
    input_path: Path,
    output_dir: Path,
    *,
    config: dict[str, Any] | None = None,
    fps: float | None = None,
    frames: int | None = None,
    duration_seconds: float | None = None,
    fmt: str = "png",
) -> dict[str, Any]:
    """Extract frames with ffmpeg; default is evenly spaced sprite frame count."""
    config = config or {}
    options = resolve_split_frames_options(
        config,
        fps=fps,
        frames=frames,
        duration_seconds=duration_seconds,
    )
    extract_fps, duration, target_frames = resolve_extract_fps(input_path, options)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_pattern = str(output_dir / f"frame_%04d.{fmt}")

    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-y",
        "-vf",
        f"fps={extract_fps}",
        out_pattern,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise SplitFramesError(f"ffmpeg failed: {exc.stderr}") from exc
    except FileNotFoundError as exc:
        raise SplitFramesError("ffmpeg not found — install ffmpeg") from exc

    extracted = sorted(output_dir.glob(f"frame_*.{fmt}"))
    if not extracted:
        raise SplitFramesError("No frames extracted")

    # ffmpeg fps filter may yield ±1 frame; trim to exact target when using --frames
    if target_frames is not None and len(extracted) > target_frames:
        for extra in extracted[target_frames:]:
            extra.unlink(missing_ok=True)
        extracted = extracted[:target_frames]
    elif target_frames is not None and len(extracted) < target_frames:
        raise SplitFramesError(
            f"Expected {target_frames} frames, got {len(extracted)} "
            f"(duration={duration:.2f}s, fps={extract_fps:.4f})"
        )

    return {
        "count": len(extracted),
        "mode": options["mode"],
        "duration_seconds": round(duration, 3),
        "extract_fps": round(extract_fps, 4),
        "target_frames": target_frames,
        "output_dir": str(output_dir.resolve()),
        "paths": [str(p.resolve()) for p in extracted],
    }
