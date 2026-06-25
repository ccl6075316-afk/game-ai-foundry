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

ENGINE_AI = "ai"
ENGINE_SOFT_KEY = "soft-key"
VIDEO_FRAME_ENGINES = (ENGINE_AI, ENGINE_SOFT_KEY)

DEFAULT_VIDEO_FRAME = {
    "engine": ENGINE_AI,
    "model": "birefnet-general",
    "trim": {
        "threshold": 200,
        "padding": 2,
    },
    "soft_key": {
        "threshold": 200,
        "fuzz": 36.0,
        "key_scope": "global",
        "morph_erode": 1,
        "morph_dilate": 1,
        "despeckle": 1,
    },
}

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


def resolve_video_frame_settings(
    config: dict[str, Any],
    *,
    engine: str | None = None,
    model: str | None = None,
    threshold: int | None = None,
    fuzz: float | None = None,
    key_scope: str | None = None,
    morph_erode: int | None = None,
    morph_dilate: int | None = None,
    despeckle: int | None = None,
    trim_threshold: int | None = None,
    trim_padding: int | None = None,
) -> dict[str, Any]:
    """Settings for video frame matting (matting.video_frames)."""
    cfg = _section(config, "video_frames")
    resolved_engine = engine or cfg.get("engine") or DEFAULT_VIDEO_FRAME["engine"]
    if resolved_engine not in VIDEO_FRAME_ENGINES:
        resolved_engine = ENGINE_AI

    trim_cfg = cfg.get("trim", {}) if isinstance(cfg.get("trim"), dict) else {}
    soft_cfg = cfg.get("soft_key", {}) if isinstance(cfg.get("soft_key"), dict) else {}

    resolved_scope = key_scope or soft_cfg.get("key_scope") or DEFAULT_VIDEO_FRAME["soft_key"]["key_scope"]
    if resolved_scope not in KEY_SCOPES:
        resolved_scope = KEY_SCOPE_GLOBAL

    return {
        "engine": resolved_engine,
        "model": str(model or cfg.get("model") or DEFAULT_VIDEO_FRAME["model"]),
        "trim": {
            "threshold": int(
                trim_threshold
                if trim_threshold is not None
                else trim_cfg.get("threshold", DEFAULT_VIDEO_FRAME["trim"]["threshold"])
            ),
            "padding": int(
                trim_padding
                if trim_padding is not None
                else trim_cfg.get("padding", DEFAULT_VIDEO_FRAME["trim"]["padding"])
            ),
        },
        "soft_key": {
            "threshold": int(
                threshold
                if threshold is not None
                else soft_cfg.get("threshold", DEFAULT_VIDEO_FRAME["soft_key"]["threshold"])
            ),
            "fuzz": float(
                fuzz if fuzz is not None else soft_cfg.get("fuzz", DEFAULT_VIDEO_FRAME["soft_key"]["fuzz"])
            ),
            "key_scope": str(resolved_scope),
            "morph_erode": int(
                morph_erode
                if morph_erode is not None
                else soft_cfg.get("morph_erode", DEFAULT_VIDEO_FRAME["soft_key"]["morph_erode"])
            ),
            "morph_dilate": int(
                morph_dilate
                if morph_dilate is not None
                else soft_cfg.get("morph_dilate", DEFAULT_VIDEO_FRAME["soft_key"]["morph_dilate"])
            ),
            "despeckle": int(
                despeckle
                if despeckle is not None
                else soft_cfg.get("despeckle", DEFAULT_VIDEO_FRAME["soft_key"]["despeckle"])
            ),
        },
    }
