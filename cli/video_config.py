"""Seedance video generation settings — brief / config / CLI resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

VALID_RESOLUTIONS = ("480p", "720p", "1080p")
RATIO_AUTO = "auto"
RATIO_ADAPTIVE = "adaptive"

# Nearest standard Seedance ratio for a reference still's pixel dimensions.
SEEDANCE_ASPECT_RATIOS: dict[str, float] = {
    "1:1": 1.0,
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "4:3": 4 / 3,
    "3:4": 3 / 4,
}

DEFAULT_VIDEO_GENERATE = {
    "model": "mini",
    "duration": 5,
    "resolution": "480p",
    "ratio": "1:1",
    "generate_audio": False,
    "watermark": False,
}


def read_image_dimensions(path: Path) -> tuple[int, int]:
    """Return (width, height) for a local image."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Cannot read reference image: {path}")
    h, w = img.shape[:2]
    return w, h


def resolve_video_ratio_from_reference(
    config: dict[str, Any],
    reference_image: Path,
) -> dict[str, Any]:
    """Pick Seedance ratio for image-to-video from reference still.

    Default ``adaptive`` — match input framing (no snap-crop to 16:9/1:1).
    Config ``video.ratio_from_reference``: ``adaptive`` | ``nearest``.
    """
    meta = infer_seedance_ratio_from_image(reference_image)
    cfg = _video_section(config)
    mode = str(cfg.get("ratio_from_reference", RATIO_ADAPTIVE)).strip().lower()
    if mode == "nearest":
        meta["ratio"] = meta["nearest_ratio"]
        meta["ratio_mode"] = "nearest"
    else:
        meta["ratio"] = RATIO_ADAPTIVE
        meta["ratio_mode"] = RATIO_ADAPTIVE
    return meta


def infer_seedance_ratio_from_image(path: Path) -> dict[str, Any]:
    """Measure reference still; include nearest standard ratio for logging."""
    w, h = read_image_dimensions(path)
    aspect = w / h if h else 1.0
    nearest_ratio, target = min(
        SEEDANCE_ASPECT_RATIOS.items(),
        key=lambda item: abs(item[1] - aspect),
    )
    return {
        "ratio": nearest_ratio,
        "nearest_ratio": nearest_ratio,
        "width": w,
        "height": h,
        "aspect": round(aspect, 4),
        "target_aspect": round(target, 4),
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
    reference_image: Path | None = None,
    cli_ratio: bool = False,
) -> dict[str, Any]:
    """Merge settings: CLI/plan overrides > config.video > defaults.

    Image-to-video ratio priority:
      1. CLI ``--ratio`` (explicit; ``auto`` infers from reference)
      2. Reference still dimensions → nearest Seedance ratio
      3. Plan/brief ratio (text-to-video only path)
      4. config.video.ratio → default 1:1

    When ``reference_image`` is set, plan/config ``1:1`` is **not** applied unless
    the user passes ``--ratio`` on the CLI — avoids cropping landscape stills.
    """
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

    ratio_meta: dict[str, Any] | None = None
    ratio_source = "default"

    if cli_ratio and ratio is not None:
        if str(ratio).strip().lower() == RATIO_AUTO:
            if reference_image is None:
                raise ValueError("--ratio auto requires --reference-image")
            ratio_meta = resolve_video_ratio_from_reference(config, reference_image)
            resolved_ratio = str(ratio_meta["ratio"])
            ratio_source = "reference_image"
        else:
            resolved_ratio = str(ratio).strip()
            ratio_source = "cli"
    elif reference_image is not None:
        ratio_meta = resolve_video_ratio_from_reference(config, reference_image)
        resolved_ratio = str(ratio_meta["ratio"])
        ratio_source = "reference_image"
    elif ratio is not None and str(ratio).strip().lower() not in ("", RATIO_AUTO):
        resolved_ratio = str(ratio).strip()
        ratio_source = "plan"
    elif cfg.get("ratio") and str(cfg.get("ratio")).lower() not in ("", RATIO_AUTO):
        resolved_ratio = str(cfg["ratio"])
        ratio_source = "config"
    else:
        resolved_ratio = str(DEFAULT_VIDEO_GENERATE["ratio"])
        ratio_source = "default"

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

    result = {
        "model": resolved_model,
        "duration": resolved_duration,
        "resolution": resolved_resolution,
        "ratio": resolved_ratio,
        "ratio_source": ratio_source,
        "generate_audio": resolved_audio,
        "watermark": resolved_watermark,
    }
    if ratio_meta:
        result["reference_dimensions"] = [ratio_meta["width"], ratio_meta["height"]]
        result["reference_aspect"] = ratio_meta["aspect"]
        if ratio_meta.get("nearest_ratio"):
            result["nearest_standard_ratio"] = ratio_meta["nearest_ratio"]
        if ratio_meta.get("ratio_mode"):
            result["ratio_mode"] = ratio_meta["ratio_mode"]
    return result


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
        vr = str(spec.video_ratio).strip()
        if vr and vr.lower() != RATIO_AUTO:
            overrides["ratio"] = vr
    elif getattr(spec, "reference_asset", ""):
        overrides["ratio"] = RATIO_AUTO
    if getattr(spec, "generate_audio", None) is not None:
        overrides["generate_audio"] = spec.generate_audio
    if getattr(spec, "watermark", None) is not None:
        overrides["watermark"] = spec.watermark
    return resolve_video_generate_settings(config, **overrides)
