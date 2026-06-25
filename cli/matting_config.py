"""Matting / trim settings from ~/.gamefactory/config.json."""

from __future__ import annotations

from typing import Any

DEFAULT_TRIM = {
    "threshold": 240,
    "padding": 2,
}

DEFAULT_COLOR_KEY = {
    "threshold": 240,
    "fuzz": 18.0,
    "key_scope": "exterior",
    "morph_erode": 0,
    "morph_dilate": 0,
    "despeckle": 0,
}

KEY_SCOPE_EXTERIOR = "exterior"
KEY_SCOPE_GLOBAL = "global"
KEY_SCOPES = (KEY_SCOPE_EXTERIOR, KEY_SCOPE_GLOBAL)

DEFAULT_VALIDATE_EDGES = {
    "edge_width": 2,
    "brightness_threshold": 220,
    "max_white_ratio": 0.01,
    "max_semi_transparent": 0,
}


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    matting = config.get("matting", {})
    if not isinstance(matting, dict):
        return {}
    block = matting.get(name, {})
    return block if isinstance(block, dict) else {}


def resolve_trim_settings(
    config: dict[str, Any],
    *,
    threshold: int | None = None,
    padding: int | None = None,
) -> dict[str, int]:
    """CLI override > config.matting.trim > defaults."""
    cfg = _section(config, "trim")
    return {
        "threshold": int(
            threshold if threshold is not None else cfg.get("threshold", DEFAULT_TRIM["threshold"])
        ),
        "padding": int(
            padding if padding is not None else cfg.get("padding", DEFAULT_TRIM["padding"])
        ),
    }


def resolve_color_key_settings(
    config: dict[str, Any],
    *,
    threshold: int | None = None,
    fuzz: float | None = None,
    key_scope: str | None = None,
    morph_erode: int | None = None,
    morph_dilate: int | None = None,
    despeckle: int | None = None,
) -> dict[str, int | float | str]:
    """CLI override > config.matting.color_key > defaults."""
    cfg = _section(config, "color_key")

    def _int(key: str, cli: int | None, default: int) -> int:
        if cli is not None:
            return cli
        val = cfg.get(key, default)
        return int(val)

    def _float(key: str, cli: float | None, default: float) -> float:
        if cli is not None:
            return cli
        val = cfg.get(key, default)
        return float(val)

    resolved_scope = (
        key_scope
        or cfg.get("key_scope")
        or DEFAULT_COLOR_KEY["key_scope"]
    )
    if resolved_scope not in KEY_SCOPES:
        resolved_scope = KEY_SCOPE_EXTERIOR

    return {
        "threshold": _int("threshold", threshold, DEFAULT_COLOR_KEY["threshold"]),
        "fuzz": _float("fuzz", fuzz, DEFAULT_COLOR_KEY["fuzz"]),
        "key_scope": str(resolved_scope),
        "morph_erode": _int("morph_erode", morph_erode, DEFAULT_COLOR_KEY["morph_erode"]),
        "morph_dilate": _int("morph_dilate", morph_dilate, DEFAULT_COLOR_KEY["morph_dilate"]),
        "despeckle": _int("despeckle", despeckle, DEFAULT_COLOR_KEY["despeckle"]),
    }


def resolve_validate_edges_settings(
    config: dict[str, Any],
    *,
    edge_width: int | None = None,
    brightness_threshold: int | None = None,
    max_white_ratio: float | None = None,
    max_semi_transparent: int | None = None,
) -> dict[str, int | float]:
    """CLI override > config.matting.validate_edges > defaults."""
    cfg = _section(config, "validate_edges")

    def _int(key: str, cli: int | None, default: int) -> int:
        if cli is not None:
            return cli
        return int(cfg.get(key, default))

    def _float(key: str, cli: float | None, default: float) -> float:
        if cli is not None:
            return cli
        return float(cfg.get(key, default))

    return {
        "edge_width": _int("edge_width", edge_width, DEFAULT_VALIDATE_EDGES["edge_width"]),
        "brightness_threshold": _int(
            "brightness_threshold",
            brightness_threshold,
            DEFAULT_VALIDATE_EDGES["brightness_threshold"],
        ),
        "max_white_ratio": _float(
            "max_white_ratio",
            max_white_ratio,
            DEFAULT_VALIDATE_EDGES["max_white_ratio"],
        ),
        "max_semi_transparent": _int(
            "max_semi_transparent",
            max_semi_transparent,
            DEFAULT_VALIDATE_EDGES["max_semi_transparent"],
        ),
    }
