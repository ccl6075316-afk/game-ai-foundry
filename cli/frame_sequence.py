"""Shared trim-then-sample logic for i2v sprite frame sequences."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

DEFAULT_SKIP_LEAD_RATIO = 0.25
DEFAULT_SKIP_TRAIL_RATIO = 0.05


@dataclass(frozen=True)
class TransitionTrimOptions:
    """User-configurable head/tail trim before sprite sampling."""

    trim_lead: bool
    trim_trail: bool
    skip_lead_ratio: float
    skip_trail_ratio: float
    skip_lead_seconds: float | None = None
    skip_trail_seconds: float | None = None

    def as_skip_ratios(self) -> tuple[float, float]:
        return (
            self.skip_lead_ratio if self.trim_lead else 0.0,
            self.skip_trail_ratio if self.trim_trail else 0.0,
        )


def _split_frames_config(config: dict[str, Any]) -> dict[str, Any]:
    video_cfg = config.get("video", {})
    if not isinstance(video_cfg, dict):
        return {}
    block = video_cfg.get("split_frames", {})
    return block if isinstance(block, dict) else {}


def _godot_config(config: dict[str, Any]) -> dict[str, Any]:
    block = config.get("godot", {})
    return block if isinstance(block, dict) else {}


def resolve_transition_trim(
    config: dict[str, Any] | None = None,
    *,
    scope: Literal["split", "import"] = "split",
    trim_lead: bool | None = None,
    trim_trail: bool | None = None,
    skip_lead_ratio: float | None = None,
    skip_trail_ratio: float | None = None,
    skip_lead_seconds: float | None = None,
    skip_trail_seconds: float | None = None,
    handoff: dict[str, Any] | None = None,
) -> TransitionTrimOptions:
    """Merge handoff > CLI > config. User can disable head/tail trim independently."""
    config = config or {}
    split_cfg = _split_frames_config(config)
    godot_cfg = _godot_config(config)
    ho = handoff or {}

    if scope == "import":
        lead_flag = ho.get("trim_lead", godot_cfg.get("import_trim_lead", split_cfg.get("trim_lead", True)))
        trail_flag = ho.get("trim_trail", godot_cfg.get("import_trim_trail", split_cfg.get("trim_trail", True)))
        lead_ratio = ho.get(
            "skip_lead_ratio",
            godot_cfg.get("import_skip_lead_ratio", split_cfg.get("skip_lead_ratio", DEFAULT_SKIP_LEAD_RATIO)),
        )
        trail_ratio = ho.get(
            "skip_trail_ratio",
            godot_cfg.get("import_skip_trail_ratio", split_cfg.get("skip_trail_ratio", DEFAULT_SKIP_TRAIL_RATIO)),
        )
    else:
        lead_flag = ho.get("trim_lead", split_cfg.get("trim_lead", True))
        trail_flag = ho.get("trim_trail", split_cfg.get("trim_trail", True))
        lead_ratio = ho.get("skip_lead_ratio", split_cfg.get("skip_lead_ratio", DEFAULT_SKIP_LEAD_RATIO))
        trail_ratio = ho.get("skip_trail_ratio", split_cfg.get("skip_trail_ratio", DEFAULT_SKIP_TRAIL_RATIO))

    if trim_lead is not None:
        lead_flag = trim_lead
    if trim_trail is not None:
        trail_flag = trim_trail
    if skip_lead_ratio is not None:
        lead_ratio = skip_lead_ratio
    if skip_trail_ratio is not None:
        trail_ratio = skip_trail_ratio

    lead_sec = skip_lead_seconds if skip_lead_seconds is not None else ho.get("skip_lead_seconds")
    trail_sec = skip_trail_seconds if skip_trail_seconds is not None else ho.get("skip_trail_seconds")
    if lead_sec is None:
        lead_sec = split_cfg.get("skip_lead_seconds")
    if trail_sec is None:
        trail_sec = split_cfg.get("skip_trail_seconds")

    return TransitionTrimOptions(
        trim_lead=bool(lead_flag),
        trim_trail=bool(trail_flag),
        skip_lead_ratio=float(lead_ratio or 0),
        skip_trail_ratio=float(trail_ratio or 0),
        skip_lead_seconds=float(lead_sec) if lead_sec is not None else None,
        skip_trail_seconds=float(trail_sec) if trail_sec is not None else None,
    )


def trim_frame_paths(
    frames: list[Path],
    *,
    skip_lead_ratio: float = DEFAULT_SKIP_LEAD_RATIO,
    skip_trail_ratio: float = DEFAULT_SKIP_TRAIL_RATIO,
    skip_lead_frames: int = 0,
    skip_trail_frames: int = 0,
    min_lead_frames: int = 1,
    trim_lead: bool = True,
    trim_trail: bool = True,
) -> tuple[list[Path], int, int]:
    """Drop leading/trailing i2v transition frames. Returns (trimmed, lead_dropped, trail_dropped)."""
    if not frames or (not trim_lead and not trim_trail):
        return list(frames), 0, 0

    n = len(frames)
    lead = 0 if not trim_lead else skip_lead_frames
    if trim_lead and lead <= 0 and skip_lead_ratio > 0:
        lead = int(n * float(skip_lead_ratio))
        if lead < min_lead_frames:
            lead = min(min_lead_frames, max(0, n - 1))

    trail = 0 if not trim_trail else skip_trail_frames
    if trim_trail and trail <= 0 and skip_trail_ratio > 0:
        trail = int(n * float(skip_trail_ratio))

    lead = max(0, min(lead, n - 1))
    trail = max(0, min(trail, n - lead - 1))
    end = n - trail if trail else n
    return frames[lead:end], lead, trail


def sample_frame_paths_evenly(frames: list[Path], target_frames: int) -> list[Path]:
    """Evenly pick target_frames from an already-trimmed sequence."""
    if target_frames < 1:
        raise ValueError("target_frames must be at least 1")
    if len(frames) <= target_frames:
        return list(frames)
    if target_frames == 1:
        return [frames[len(frames) // 2]]

    last = len(frames) - 1
    indices = [round(i * last / (target_frames - 1)) for i in range(target_frames)]
    return [frames[i] for i in indices]


def process_frame_sequence(
    frames: list[Path],
    *,
    skip_lead_ratio: float | None = DEFAULT_SKIP_LEAD_RATIO,
    skip_trail_ratio: float | None = DEFAULT_SKIP_TRAIL_RATIO,
    skip_lead_frames: int = 0,
    skip_trail_frames: int = 0,
    sample_frames: int | None = None,
    pre_trimmed: bool = False,
    pre_sampled: bool = False,
    trim_lead: bool = True,
    trim_trail: bool = True,
) -> tuple[list[Path], dict[str, int]]:
    """Phase 1: trim i2v transition (optional). Phase 2: sample to sprite frame count."""
    meta: dict[str, int] = {
        "input_count": len(frames),
        "lead_dropped": 0,
        "trail_dropped": 0,
        "sampled_to": 0,
    }
    if not frames:
        return [], meta

    working = list(frames)
    if not pre_trimmed:
        working, lead, trail = trim_frame_paths(
            working,
            skip_lead_ratio=float(skip_lead_ratio or 0),
            skip_trail_ratio=float(skip_trail_ratio or 0),
            skip_lead_frames=skip_lead_frames,
            skip_trail_frames=skip_trail_frames,
            trim_lead=trim_lead,
            trim_trail=trim_trail,
        )
        meta["lead_dropped"] = lead
        meta["trail_dropped"] = trail

    if (
        not pre_sampled
        and sample_frames is not None
        and sample_frames > 0
        and len(working) > sample_frames
    ):
        working = sample_frame_paths_evenly(working, sample_frames)
        meta["sampled_to"] = sample_frames

    if not working:
        raise ValueError(
            f"trim/sample removed all {meta['input_count']} frames "
            f"(lead={meta['lead_dropped']}, trail={meta['trail_dropped']}, "
            f"sample={sample_frames})"
        )

    return working, meta
