"""Edge QA for matted (transparent) sprites — detect white halos on silhouette."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from asset_pipeline import ValidationResult


def _near_white_mask(bgr: np.ndarray, threshold: int) -> np.ndarray:
    """True where all BGR channels are bright (actual white/near-white, not saturated colors)."""
    floor = max(0, threshold - 20)
    return np.min(bgr, axis=2) >= floor


def validate_matting_edges(
    image_path: Path,
    *,
    edge_width: int = 2,
    brightness_threshold: int = 220,
    max_white_ratio: float = 0.01,
    max_semi_transparent: int = 0,
) -> ValidationResult:
    """Check 1–2px edge band for white fringes after trim + remove-bg.

    Samples the outermost ``edge_width`` pixels of the opaque region and any
    bright semi-transparent pixels on the silhouette boundary.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return ValidationResult(
            ok=False,
            asset_type="matting",
            checks=[{"check": "readable", "passed": False}],
            message=f"Cannot read image: {image_path}",
        )

    if img.ndim < 3 or img.shape[2] < 4:
        return ValidationResult(
            ok=False,
            asset_type="matting",
            checks=[{"check": "has_alpha", "passed": False}],
            message="Matting validation requires RGBA PNG with alpha channel.",
        )

    bgr = img[:, :, :3]
    alpha = img[:, :, 3]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    near_white = _near_white_mask(bgr, brightness_threshold)

    fg = (alpha >= 128).astype(np.uint8)
    if fg.sum() == 0:
        return ValidationResult(
            ok=False,
            asset_type="matting",
            checks=[{"check": "foreground_pixels", "value": 0, "passed": False}],
            message="No opaque foreground pixels found.",
        )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    eroded = fg.copy()
    for _ in range(max(1, edge_width)):
        eroded = cv2.erode(eroded, kernel, iterations=1)

    edge_band = (fg > 0) & (eroded == 0)
    edge_count = int(edge_band.sum())

    bright_on_edge = edge_band & near_white
    bright_count = int(bright_on_edge.sum())
    white_ratio = bright_count / edge_count if edge_count else 0.0

    semi = (alpha > 0) & (alpha < 128) & near_white
    semi_count = int(semi.sum())

    dilated = cv2.dilate(fg, kernel, iterations=1)
    outer_ring = (dilated > 0) & (fg == 0)
    halo = outer_ring & (alpha > 0) & near_white
    halo_count = int(halo.sum())

    checks: list[dict[str, Any]] = [
        {"check": "has_alpha", "passed": True},
        {"check": "edge_width_px", "value": edge_width},
        {"check": "edge_pixels_sampled", "value": edge_count},
        {
            "check": "bright_edge_pixels",
            "value": bright_count,
            "ratio": round(white_ratio, 6),
            "max_ratio": max_white_ratio,
            "threshold": brightness_threshold,
            "passed": white_ratio <= max_white_ratio,
        },
        {
            "check": "semi_transparent_bright",
            "value": semi_count,
            "max": max_semi_transparent,
            "passed": semi_count <= max_semi_transparent,
        },
        {
            "check": "outer_halo_pixels",
            "value": halo_count,
            "passed": halo_count == 0,
        },
    ]

    ok = all(c.get("passed", True) for c in checks if "passed" in c)
    if ok:
        message = (
            f"Matting edge validation passed "
            f"(bright edge ratio {white_ratio:.4f} ≤ {max_white_ratio})."
        )
    else:
        message = (
            "Matting edge validation failed: white fringe on silhouette. "
            "Retry remove-bg with higher morph_erode / fuzz, or lower threshold."
        )

    return ValidationResult(
        ok=ok,
        asset_type="matting",
        checks=checks,
        message=message,
    )
