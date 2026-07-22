"""Resolve which image model to use (default vs bulk stills)."""

from __future__ import annotations

import logging
from typing import Any, Literal

GenerateTier = Literal["default", "bulk"]

_LOG = logging.getLogger("gamefactory.image_model_route")


def normalize_generate_tier(raw: str | None) -> GenerateTier | None:
    text = str(raw or "").strip().lower()
    if not text:
        return None
    if text in ("default", "bulk"):
        return text  # type: ignore[return-value]
    raise ValueError(f"generate_tier must be 'default' or 'bulk', got {raw!r}")


def effective_generate_tier(
    *,
    generate_tier: str | None,
    for_icon_kit_item: bool = False,
) -> GenerateTier:
    """Kit expanded items default to bulk; otherwise honor explicit tier or default."""
    normalized = None
    try:
        normalized = normalize_generate_tier(generate_tier)
    except ValueError:
        normalized = None
    if normalized:
        return normalized
    if for_icon_kit_item:
        return "bulk"
    return "default"


def resolve_image_model_for_tier(
    config: dict[str, Any] | None,
    tier: GenerateTier,
    *,
    explicit_model: str | None = None,
) -> str:
    """Pick model id for generate. ``explicit_model`` (CLI --model) wins."""
    if explicit_model and str(explicit_model).strip():
        return str(explicit_model).strip()
    image_cfg = config.get("image") if isinstance(config, dict) else None
    if not isinstance(image_cfg, dict):
        image_cfg = {}
    default = str(image_cfg.get("model") or "").strip()
    if tier == "bulk":
        bulk = str(image_cfg.get("bulk_model") or "").strip()
        if bulk:
            return bulk
        if default:
            _LOG.info(
                "image.bulk_model unset; falling back to image.model=%s",
                default,
            )
            return default
        return ""
    return default
