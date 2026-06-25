"""Video frame matting — separate from studio white color-key (image remove-bg).

Static sprites: `image remove-bg --mode color` (pure white #FFFFFF).
Video frames:   `video matte-frames --engine ai` (rembg / BiRefNet) or `--engine soft-key`.

Industry practice for game sprite extraction from video without green screen:
- rembg + BiRefNet / ISNet (danielgatis/rembg, MIT) — per-frame AI matting
- Optional soft color-key when AI unavailable (gray/off-white Seedance backgrounds)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np

from image_cmds import remove_bg_color_key, trim_content_bbox
from matting_config import (
    ENGINE_AI,
    ENGINE_SOFT_KEY,
    VIDEO_FRAME_ENGINES,
    resolve_video_frame_settings,
)

VideoFrameEngine = Literal["ai", "soft-key"]


class VideoMattingError(RuntimeError):
    """Raised when video frame matting fails."""


@lru_cache(maxsize=4)
def _rembg_session(model_name: str):
    try:
        from rembg import new_session
    except ImportError as exc:
        raise VideoMattingError(
            'AI engine requires rembg. Install: pip install "rembg[cpu]"'
        ) from exc
    return new_session(model_name)


def matte_frame_ai(image_bytes: bytes, *, model: str) -> bytes:
    """Remove background via rembg (U2Net / BiRefNet / ISNet family)."""
    try:
        from rembg import remove
    except ImportError as exc:
        raise VideoMattingError(
            'AI engine requires rembg. Install: pip install "rembg[cpu]"'
        ) from exc

    session = _rembg_session(model)
    return remove(image_bytes, session=session)


def matte_frame_soft_key(
    img_bgr: np.ndarray,
    *,
    threshold: int,
    fuzz: float,
    key_scope: str,
    morph_erode: int,
    morph_dilate: int,
    despeckle: int,
) -> np.ndarray:
    """Softer color-key for gray/off-white video frames (not studio white)."""
    return remove_bg_color_key(
        img_bgr,
        threshold=threshold,
        fuzz=fuzz,
        key_scope=key_scope,
        morph_erode=morph_erode,
        morph_dilate=morph_dilate,
        despeckle=despeckle,
    )


def validate_video_frame_rgba(path: Path) -> dict[str, Any]:
    """Relaxed QA for animation frames — alpha present, not strict white-edge ratio."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return {"ok": False, "message": f"Cannot read {path}"}
    if img.ndim < 3 or img.shape[2] != 4:
        return {"ok": False, "message": "Expected RGBA PNG"}
    alpha = img[:, :, 3]
    opaque_ratio = float(np.mean(alpha > 128))
    if opaque_ratio < 0.05:
        return {"ok": False, "message": "Subject too small or fully transparent"}
    if opaque_ratio > 0.98:
        return {"ok": False, "message": "Almost fully opaque — background likely not removed"}
    return {
        "ok": True,
        "message": "Video frame matting passed (relaxed QA).",
        "opaque_ratio": opaque_ratio,
    }


def matte_single_frame(
    input_path: Path,
    output_path: Path,
    *,
    engine: VideoFrameEngine,
    config: dict[str, Any],
    trim: bool = True,
    validate: bool = True,
    **overrides: Any,
) -> dict[str, Any]:
    """Matte one frame; optional trim before matting."""
    settings = resolve_video_frame_settings(config, engine=engine, **overrides)

    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise VideoMattingError(f"Cannot read {input_path}")

    work = img
    if trim:
        if work.shape[2] == 4:
            work, _ = trim_content_bbox(work, use_alpha=True, **settings["trim"])
        else:
            work, _ = trim_content_bbox(work, **settings["trim"])

    if engine == ENGINE_AI:
        ext = ".png"
        ok, buf = cv2.imencode(ext, work if work.shape[2] == 3 else cv2.cvtColor(work, cv2.COLOR_BGRA2BGR))
        if not ok:
            raise VideoMattingError(f"Failed to encode {input_path}")
        result_bytes = matte_frame_ai(buf.tobytes(), model=str(settings["model"]))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result_bytes)
    elif engine == ENGINE_SOFT_KEY:
        bgr = work if work.shape[2] == 3 else cv2.cvtColor(work, cv2.COLOR_BGRA2BGR)
        rgba = matte_frame_soft_key(bgr, **settings["soft_key"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_path), rgba):
            raise VideoMattingError(f"Failed to write {output_path}")
    else:
        raise VideoMattingError(f"Unknown engine: {engine}")

    qa = validate_video_frame_rgba(output_path) if validate else {"ok": True, "skipped": True}
    if not qa.get("ok"):
        raise VideoMattingError(qa.get("message", "validation failed"))

    return {"output": str(output_path.resolve()), "engine": engine, "validation": qa}


def matte_frames_batch(
    input_dir: Path,
    output_dir: Path,
    *,
    engine: VideoFrameEngine,
    config: dict[str, Any],
    pattern: str = "frame_*.png",
    trim: bool = True,
    validate: bool = True,
    **overrides: Any,
) -> list[dict[str, Any]]:
    """Batch-matte all frames matching pattern."""
    frames = sorted(input_dir.glob(pattern))
    if not frames:
        raise VideoMattingError(f"No frames matching {pattern} in {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    for frame in frames:
        out_path = output_dir / frame.name
        try:
            result = matte_single_frame(
                frame,
                out_path,
                engine=engine,
                config=config,
                trim=trim,
                validate=validate,
                **overrides,
            )
            results.append(result)
        except (VideoMattingError, OSError, ValueError) as exc:
            failures.append(f"{frame.name}: {exc}")

    if failures:
        raise VideoMattingError(
            "Batch matting had failures:\n" + "\n".join(failures[:8])
            + (f"\n... and {len(failures) - 8} more" if len(failures) > 8 else "")
        )

    return results


def batch_summary(results: list[dict[str, Any]]) -> str:
    return json.dumps({"count": len(results), "engine": results[0]["engine"] if results else None})
