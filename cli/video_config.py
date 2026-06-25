"""Seedance video generation settings — brief / config / CLI resolution."""

from __future__ import annotations

from typing import Any

VALID_RESOLUTIONS = ("480p", "720p", "1080p")

DEFAULT_VIDEO_GENERATE = {
    "model": "mini",
    "duration": 5,
    "resolution": "480p",
    "ratio": "1:1",
    "generate_audio": False,
    "watermark": False,
}


def _video_section(config: dict[str, Any]) -> dict[str, Any]:
    block = config.get("video", {})
    return block if isinstance(block, dict) else {}


def resolve_video_generate_settings(
    config: dict[str, Any],
    *,
    model: str | None = None,
    duration: int | float | None = None,
    resolution: str | None = None,
    ratio: str | None = None,
    generate_audio: bool | None = None,
    watermark: bool | None = None,
) -> dict[str, Any]:
    """Merge settings: CLI/plan overrides > config.video > defaults."""
    cfg = _video_section(config)

    resolved_model = str(model or cfg.get("model") or DEFAULT_VIDEO_GENERATE["model"])
    resolved_duration = int(
        duration if duration is not None else cfg.get("duration", DEFAULT_VIDEO_GENERATE["duration"])
    )
    resolved_resolution = str(
        resolution or cfg.get("resolution") or DEFAULT_VIDEO_GENERATE["resolution"]
    )
    if resolved_resolution not in VALID_RESOLUTIONS:
        resolved_resolution = str(DEFAULT_VIDEO_GENERATE["resolution"])

    resolved_ratio = str(ratio or cfg.get("ratio") or DEFAULT_VIDEO_GENERATE["ratio"])

    if generate_audio is not None:
        resolved_audio = bool(generate_audio)
    elif "generate_audio" in cfg:
        resolved_audio = bool(cfg["generate_audio"])
    else:
        resolved_audio = bool(DEFAULT_VIDEO_GENERATE["generate_audio"])

    if watermark is not None:
        resolved_watermark = bool(watermark)
    elif "watermark" in cfg:
        resolved_watermark = bool(cfg["watermark"])
    else:
        resolved_watermark = bool(DEFAULT_VIDEO_GENERATE["watermark"])

    if resolved_duration < 4 or resolved_duration > 15:
        raise ValueError(f"video duration must be 4–15 seconds, got {resolved_duration}")

    return {
        "model": resolved_model,
        "duration": resolved_duration,
        "resolution": resolved_resolution,
        "ratio": resolved_ratio,
        "generate_audio": resolved_audio,
        "watermark": resolved_watermark,
    }


def video_settings_from_asset_spec(
    config: dict[str, Any],
    spec: Any,
) -> dict[str, Any]:
    """Build Seedance params from AssetSpec + global config."""
    overrides: dict[str, Any] = {}
    if getattr(spec, "duration_seconds", None):
        overrides["duration"] = int(spec.duration_seconds)
    if getattr(spec, "video_model", ""):
        overrides["model"] = spec.video_model
    if getattr(spec, "video_resolution", ""):
        overrides["resolution"] = spec.video_resolution
    if getattr(spec, "video_ratio", ""):
        overrides["ratio"] = spec.video_ratio
    if getattr(spec, "generate_audio", None) is not None:
        overrides["generate_audio"] = spec.generate_audio
    if getattr(spec, "watermark", None) is not None:
        overrides["watermark"] = spec.watermark
    return resolve_video_generate_settings(config, **overrides)
