"""Video → sprite frame extraction settings and ffmpeg helpers."""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Any

from toolchain_paths import resolve_ffmpeg, resolve_ffprobe

from frame_sequence import (
    DEFAULT_SKIP_LEAD_RATIO,
    DEFAULT_SKIP_TRAIL_RATIO,
    process_frame_sequence,
    resolve_transition_trim,
    sample_frame_paths_evenly,
)

DEFAULT_SPRITE_FRAMES = 8


class SplitFramesError(RuntimeError):
    """Invalid split-frames options or ffmpeg failure."""


def _require_ffmpeg(config: dict[str, Any] | None = None) -> str:
    path = resolve_ffmpeg(config)
    if not path:
        raise SplitFramesError("ffmpeg not found — run: python gamefactory.py setup install ffmpeg")
    return path


def _require_ffprobe(config: dict[str, Any] | None = None) -> str:
    path = resolve_ffprobe(config)
    if not path:
        raise SplitFramesError("ffprobe not found — run: python gamefactory.py setup install ffmpeg")
    return path


def probe_video_duration(path: Path, config: dict[str, Any] | None = None) -> float:
    """Return video duration in seconds via ffprobe."""
    ffprobe = _require_ffprobe(config)
    cmd = [
        ffprobe,
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


def resolve_skip_bounds(
    duration: float,
    config: dict[str, Any],
    *,
    trim_lead: bool | None = None,
    trim_trail: bool | None = None,
    skip_lead_seconds: float | None = None,
    skip_lead_ratio: float | None = None,
    skip_trail_seconds: float | None = None,
    skip_trail_ratio: float | None = None,
) -> tuple[float, float]:
    """Return (t_start, t_end); respects config trim_lead / trim_trail toggles."""
    opts = resolve_transition_trim(
        config,
        scope="split",
        trim_lead=trim_lead,
        trim_trail=trim_trail,
        skip_lead_ratio=skip_lead_ratio,
        skip_trail_ratio=skip_trail_ratio,
        skip_lead_seconds=skip_lead_seconds,
        skip_trail_seconds=skip_trail_seconds,
    )

    lead = 0.0
    if opts.trim_lead:
        if opts.skip_lead_seconds is not None:
            lead = float(opts.skip_lead_seconds)
        elif opts.skip_lead_ratio > 0:
            lead = duration * opts.skip_lead_ratio

    trail = 0.0
    if opts.trim_trail:
        if opts.skip_trail_seconds is not None:
            trail = float(opts.skip_trail_seconds)
        elif opts.skip_trail_ratio > 0:
            trail = duration * opts.skip_trail_ratio

    if lead + trail >= duration:
        raise SplitFramesError(
            f"skip lead ({lead:.3f}s) + trail ({trail:.3f}s) "
            f"must be less than clip duration ({duration:.3f}s)"
        )

    return lead, duration - trail


def compute_sample_timestamps(
    t_start: float,
    t_end: float,
    target_frames: int,
) -> list[float]:
    """Evenly sample target_frames timestamps inside [t_start, t_end]."""
    if target_frames < 1:
        raise SplitFramesError("--frames must be at least 1")
    if t_end <= t_start:
        raise SplitFramesError("Invalid sample window")

    if target_frames == 1:
        return [(t_start + t_end) / 2.0]

    span = t_end - t_start
    return [t_start + (i / (target_frames - 1)) * span for i in range(target_frames)]


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
    *,
    config: dict[str, Any] | None = None,
    skip_lead_seconds: float | None = None,
    skip_lead_ratio: float | None = None,
    skip_trail_seconds: float | None = None,
    skip_trail_ratio: float | None = None,
    trim_lead: bool | None = None,
    trim_trail: bool | None = None,
) -> tuple[float, float, int | None, float, float]:
    """Return (extract_fps, duration, target_frames, t_start, t_end)."""
    config = config or {}
    duration = options.get("duration_hint")
    if duration is None:
        duration = probe_video_duration(input_path, config)
    duration = float(duration)

    t_start, t_end = resolve_skip_bounds(
        duration,
        config,
        trim_lead=trim_lead,
        trim_trail=trim_trail,
        skip_lead_seconds=skip_lead_seconds,
        skip_lead_ratio=skip_lead_ratio,
        skip_trail_seconds=skip_trail_seconds,
        skip_trail_ratio=skip_trail_ratio,
    )
    usable = t_end - t_start

    if options["mode"] == "fps":
        return float(options["extract_fps"]), duration, None, t_start, t_end

    target = int(options["target_frames"])
    extract_fps = target / usable
    return extract_fps, duration, target, t_start, t_end


def _extract_frame_at(
    input_path: Path,
    timestamp: float,
    output_path: Path,
    config: dict[str, Any] | None = None,
) -> None:
    ffmpeg = _require_ffmpeg(config)
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        str(timestamp),
        "-i",
        str(input_path),
        "-frames:v",
        "1",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise SplitFramesError(f"ffmpeg failed at t={timestamp:.3f}s: {exc.stderr}") from exc
    except FileNotFoundError as exc:
        raise SplitFramesError("ffmpeg not found — install ffmpeg") from exc


def split_video_to_frames(
    input_path: Path,
    output_dir: Path,
    *,
    config: dict[str, Any] | None = None,
    fps: float | None = None,
    frames: int | None = None,
    duration_seconds: float | None = None,
    fmt: str = "png",
    skip_lead_seconds: float | None = None,
    skip_lead_ratio: float | None = None,
    skip_trail_seconds: float | None = None,
    skip_trail_ratio: float | None = None,
    trim_lead: bool | None = None,
    trim_trail: bool | None = None,
) -> dict[str, Any]:
    """Extract sprite frames; optional head/tail trim then sample (see config trim_lead/trim_trail)."""
    config = config or {}
    trim_opts = resolve_transition_trim(
        config,
        scope="split",
        trim_lead=trim_lead,
        trim_trail=trim_trail,
        skip_lead_ratio=skip_lead_ratio,
        skip_trail_ratio=skip_trail_ratio,
        skip_lead_seconds=skip_lead_seconds,
        skip_trail_seconds=skip_trail_seconds,
    )
    options = resolve_split_frames_options(
        config,
        fps=fps,
        frames=frames,
        duration_seconds=duration_seconds,
    )
    extract_fps, duration, target_frames, t_start, t_end = resolve_extract_fps(
        input_path,
        options,
        config=config,
        skip_lead_seconds=skip_lead_seconds,
        skip_lead_ratio=skip_lead_ratio,
        skip_trail_seconds=skip_trail_seconds,
        skip_trail_ratio=skip_trail_ratio,
        trim_lead=trim_opts.trim_lead,
        trim_trail=trim_opts.trim_trail,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    dense_fps = extract_fps
    ffmpeg = _require_ffmpeg(config)

    if options["mode"] == "frames" and target_frames is not None:
        # Phase 1: dense extract inside trimmed window (time-trim only).
        usable = t_end - t_start
        dense_fps = max(extract_fps, target_frames / usable * 3.0, 12.0)
        out_pattern = str(output_dir / f"_dense_%04d.{fmt}")
        cmd = [
            ffmpeg,
            "-ss",
            str(t_start),
            "-i",
            str(input_path),
            "-t",
            str(usable),
            "-y",
            "-vf",
            f"fps={dense_fps}",
            out_pattern,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise SplitFramesError(f"ffmpeg failed: {exc.stderr}") from exc
        except FileNotFoundError as exc:
            raise SplitFramesError("ffmpeg not found — install ffmpeg") from exc

        dense = sorted(output_dir.glob(f"_dense_*.{fmt}"))
        if not dense:
            raise SplitFramesError("No frames extracted in trimmed window")

        try:
            picked, _pick_meta = process_frame_sequence(
                dense,
                pre_trimmed=True,
                pre_sampled=False,
                sample_frames=target_frames,
            )
        except ValueError as exc:
            raise SplitFramesError(str(exc)) from exc

        for idx, src in enumerate(picked, start=1):
            out_path = output_dir / f"frame_{idx:04d}.{fmt}"
            shutil.copy2(src, out_path)
            extracted.append(out_path)
        for tmp in dense:
            tmp.unlink(missing_ok=True)
    else:
        usable = t_end - t_start
        out_pattern = str(output_dir / f"frame_%04d.{fmt}")
        cmd = [
            ffmpeg,
            "-ss",
            str(t_start),
            "-i",
            str(input_path),
            "-t",
            str(usable),
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
        if target_frames is not None and len(extracted) > target_frames:
            picked = sample_frame_paths_evenly(extracted, target_frames)
            keep = {p.resolve() for p in picked}
            for path in extracted:
                if path.resolve() not in keep:
                    path.unlink(missing_ok=True)
            extracted = picked
            for idx, src in enumerate(extracted, start=1):
                dest = output_dir / f"frame_{idx:04d}.{fmt}"
                if src != dest:
                    src.rename(dest)
            extracted = sorted(output_dir.glob(f"frame_*.{fmt}"))
        elif target_frames is not None and len(extracted) < target_frames:
            raise SplitFramesError(
                f"Expected {target_frames} frames, got {len(extracted)} "
                f"(duration={duration:.2f}s, fps={extract_fps:.4f})"
            )

    if not extracted:
        raise SplitFramesError("No frames extracted")

    skip_lead = t_start
    skip_trail = duration - t_end
    return {
        "count": len(extracted),
        "mode": options["mode"],
        "duration_seconds": round(duration, 3),
        "extract_fps": round(extract_fps, 4),
        "target_frames": target_frames,
        "trim_lead": trim_opts.trim_lead,
        "trim_trail": trim_opts.trim_trail,
        "skip_lead_seconds": round(skip_lead, 3),
        "skip_trail_seconds": round(skip_trail, 3),
        "sample_start_seconds": round(t_start, 3),
        "sample_end_seconds": round(t_end, 3),
        "output_dir": str(output_dir.resolve()),
        "paths": [str(p.resolve()) for p in extracted],
    }
