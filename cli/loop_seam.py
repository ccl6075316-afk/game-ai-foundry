"""Loop-aware frame window search for i2v sprite clips.

Avoids fixed lead/trail ratios that overfit one clip. Uses relative frame
differences: drop morph spikes, then pick a phase-aligned window whose
loop seam is comparable to mid-clip motion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_SEAM_OVER_MID_MAX = 1.25
DEFAULT_SPIKE_FACTOR = 1.8
DEFAULT_MIN_KEEP_RATIO = 0.35
DEFAULT_PROBE_FPS = 12.0


def _load_gray(path: Path) -> np.ndarray:
    from PIL import Image

    im = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32)
    alpha = im[:, :, 3:4] / 255.0
    return (im[:, :, :3] * alpha).mean(axis=2)


def _stack_grays(paths: list[Path]) -> list[np.ndarray]:
    arrs = [_load_gray(p) for p in paths]
    h = min(a.shape[0] for a in arrs)
    w = min(a.shape[1] for a in arrs)
    return [a[:h, :w] for a in arrs]


def _diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def _adj_series(stack: list[np.ndarray]) -> list[float]:
    return [_diff(stack[i], stack[i + 1]) for i in range(len(stack) - 1)]


def _sample_indices(n: int, target: int) -> list[int]:
    if target < 1:
        raise ValueError("target_frames must be >= 1")
    if n <= target:
        return list(range(n))
    if target == 1:
        return [n // 2]
    last = n - 1
    return [round(i * last / (target - 1)) for i in range(target)]


def evaluate_loop_sequence(
    paths: list[Path],
    *,
    grays: list[np.ndarray] | None = None,
) -> dict[str, float]:
    """Return seam / mid-adjacent stats for an ordered frame list."""
    if len(paths) < 2 and (grays is None or len(grays) < 2):
        return {
            "n": float(len(paths) if grays is None else len(grays)),
            "seam": 0.0,
            "mid_adj": 0.0,
            "adj_mean": 0.0,
            "adj_max": 0.0,
            "seam_over_mid": 0.0,
        }
    stack = grays if grays is not None else _stack_grays(paths)
    adj = _adj_series(stack)
    if not adj:
        return {
            "n": float(len(stack)),
            "seam": 0.0,
            "mid_adj": 0.0,
            "adj_mean": 0.0,
            "adj_max": 0.0,
            "seam_over_mid": 0.0,
        }
    lo = len(adj) // 4
    hi = max(lo + 1, 3 * len(adj) // 4)
    mid = adj[lo:hi] or adj
    mid_adj = float(np.mean(mid))
    seam = _diff(stack[0], stack[-1])
    return {
        "n": float(len(stack)),
        "seam": round(seam, 4),
        "mid_adj": round(mid_adj, 4),
        "adj_mean": round(float(np.mean(adj)), 4),
        "adj_max": round(float(np.max(adj)), 4),
        "seam_over_mid": round(seam / max(mid_adj, 1e-6), 4),
    }


def find_stable_band(
    adj: list[float],
    *,
    stack: list[np.ndarray] | None = None,
    spike_factor: float = DEFAULT_SPIKE_FACTOR,
) -> tuple[int, int]:
    """Return inclusive frame indices [lo, hi] after dropping i2v morph ends.

    Uses adjacent-diff spikes plus distance from the opening still so gradual
    still→motion→still morphs are excluded even when steps stay smooth.
    """
    n_adj = len(adj)
    if n_adj < 4:
        return 0, n_adj

    mid = adj[n_adj // 4 : 3 * n_adj // 4] or adj
    base = float(np.median(mid))
    calm = base * 1.35
    spike = base * spike_factor

    lead = 0
    limit = max(1, n_adj // 3)
    while lead < limit and adj[lead] > spike:
        lead += 1
    while lead + 1 < limit:
        if adj[lead] <= calm and adj[lead + 1] <= calm:
            break
        lead += 1

    trail = 0
    while trail < limit and adj[n_adj - 1 - trail] > spike:
        trail += 1
    while trail + 1 < limit:
        k = n_adj - 1 - trail
        if adj[k] <= calm and adj[k - 1] <= calm:
            break
        trail += 1

    if stack is not None and len(stack) == n_adj + 1:
        n = len(stack)
        still = np.mean(np.stack(stack[: max(1, n // 20)], axis=0), axis=0)
        mid_stack = stack[n // 4 : 3 * n // 4] or stack
        centroid = np.mean(np.stack(mid_stack, axis=0), axis=0)
        still_gap = float(np.mean(np.abs(still - centroid)))
        if still_gap > 1e-3:
            # Enter motion once we leave the opening still.
            enter = still_gap * 0.45
            dist_limit = max(1, n // 3)
            while lead < dist_limit and float(np.mean(np.abs(stack[lead] - still))) < enter:
                lead += 1
            while trail < dist_limit and float(np.mean(np.abs(stack[n - 1 - trail] - still))) < enter:
                trail += 1

    lo = lead
    hi = n_adj - trail
    if hi - lo < 8:
        lo = max(0, n_adj // 5)
        hi = min(n_adj, n_adj - n_adj // 5)
    return lo, hi


def _window_still_penalty(
    stack: list[np.ndarray],
    start: int,
    end: int,
    still: np.ndarray,
    still_gap: float,
) -> float:
    """Penalize windows that still look like the opening reference still."""
    if still_gap <= 1e-3:
        return 0.0
    ends = 0.5 * (
        float(np.mean(np.abs(stack[start] - still)))
        + float(np.mean(np.abs(stack[end] - still)))
    )
    # Low distance to still ⇒ morph residue remains ⇒ bad loop sprites.
    return max(0.0, 1.0 - ends / still_gap) * 2.0


def optimize_loop_window(
    paths: list[Path],
    *,
    target_frames: int,
    seam_over_mid_max: float = DEFAULT_SEAM_OVER_MID_MAX,
    spike_factor: float = DEFAULT_SPIKE_FACTOR,
    min_keep_ratio: float = DEFAULT_MIN_KEEP_RATIO,
) -> dict[str, Any]:
    """Search a phase-aligned window; ``ok`` when seam is within threshold."""
    if len(paths) < max(4, target_frames // 2):
        stats = evaluate_loop_sequence(paths)
        return {
            "ok": False,
            "reason": "too_few_frames",
            "paths": list(paths),
            "start_index": 0,
            "end_index": max(0, len(paths) - 1),
            "lead_dropped": 0,
            "trail_dropped": 0,
            **stats,
        }

    stack = _stack_grays(paths)
    adj = _adj_series(stack)
    lo, hi = find_stable_band(adj, stack=stack, spike_factor=spike_factor)
    n = len(stack)
    still = np.mean(np.stack(stack[: max(1, n // 20)], axis=0), axis=0)
    mid_stack = stack[n // 4 : 3 * n // 4] or stack
    centroid = np.mean(np.stack(mid_stack, axis=0), axis=0)
    still_gap = float(np.mean(np.abs(still - centroid)))

    min_span = max(target_frames, int(round(n * min_keep_ratio * 0.5)), 8)
    # Prefer at least one motion period worth of frames when possible.
    min_span = min(min_span, max(8, hi - lo + 1))

    candidates: list[dict[str, Any]] = []
    for i in range(lo, hi - min_span + 2):
        for j in range(i + min_span - 1, hi + 1):
            span = j - i + 1
            if span < min_span:
                continue
            idxs = _sample_indices(span, target_frames)
            picked_gray = [stack[i + k] for k in idxs]
            stats = evaluate_loop_sequence([], grays=picked_gray)
            keep_ratio = span / n
            score = stats["seam_over_mid"] - 0.05 * keep_ratio
            score += _window_still_penalty(stack, i, j, still, still_gap)
            if stats["mid_adj"] > 0:
                score += 0.1 * max(0.0, stats["adj_max"] / stats["mid_adj"] - 2.5)
            candidates.append(
                {
                    "start_index": i,
                    "end_index": j,
                    "lead_dropped": i,
                    "trail_dropped": n - 1 - j,
                    "keep_ratio": round(keep_ratio, 4),
                    "score": score,
                    **stats,
                }
            )

    if not candidates:
        stats = evaluate_loop_sequence(paths)
        return {
            "ok": False,
            "reason": "no_candidates",
            "paths": list(paths),
            "start_index": 0,
            "end_index": n - 1,
            "lead_dropped": 0,
            "trail_dropped": 0,
            "stable_lo": lo,
            "stable_hi": hi,
            **stats,
        }

    candidates.sort(key=lambda c: (c["score"], c["seam_over_mid"], -c["keep_ratio"]))
    best = candidates[0]
    ok = best["seam_over_mid"] <= seam_over_mid_max
    # Guard: rejecting the false-positive "full clip with morph ends that match".
    # If best window still includes heavy end morph (tiny trim) but adj_max is wild,
    # try the best candidate that drops meaningful lead+trail.
    if ok and best["lead_dropped"] + best["trail_dropped"] < max(2, n // 20):
        if best["adj_max"] > best["mid_adj"] * 2.5:
            trimmed = [
                c
                for c in candidates
                if c["lead_dropped"] >= max(2, n // 16)
                and c["trail_dropped"] >= max(2, n // 16)
                and c["seam_over_mid"] <= seam_over_mid_max
            ]
            if trimmed:
                best = trimmed[0]
                ok = True
            else:
                # Prefer a trimmed near-pass over morph-inclusive false pass.
                trimmed_any = [
                    c
                    for c in candidates
                    if c["lead_dropped"] >= max(2, n // 16)
                    and c["trail_dropped"] >= max(2, n // 16)
                ]
                if trimmed_any:
                    best = trimmed_any[0]
                    ok = best["seam_over_mid"] <= seam_over_mid_max

    window_paths = paths[best["start_index"] : best["end_index"] + 1]
    idxs = _sample_indices(len(window_paths), target_frames)
    picked = [window_paths[k] for k in idxs]
    return {
        "ok": ok,
        "reason": "pass" if ok else "seam_above_threshold",
        "paths": picked,
        "stable_lo": lo,
        "stable_hi": hi,
        "start_index": best["start_index"],
        "end_index": best["end_index"],
        "lead_dropped": best["lead_dropped"],
        "trail_dropped": best["trail_dropped"],
        "keep_ratio": best["keep_ratio"],
        "score": round(float(best["score"]), 4),
        "seam": best["seam"],
        "mid_adj": best["mid_adj"],
        "adj_mean": best["adj_mean"],
        "adj_max": best["adj_max"],
        "seam_over_mid": best["seam_over_mid"],
        "seam_over_mid_max": seam_over_mid_max,
    }


def select_loop_frame_paths(
    paths: list[Path],
    *,
    target_frames: int,
    fallback_lead_ratio: float = 0.25,
    fallback_trail_ratio: float = 0.05,
    seam_over_mid_max: float = DEFAULT_SEAM_OVER_MID_MAX,
    spike_factor: float = DEFAULT_SPIKE_FACTOR,
    min_keep_ratio: float = DEFAULT_MIN_KEEP_RATIO,
) -> tuple[list[Path], dict[str, Any]]:
    """Optimize loop window; fall back to ratios only when they score better."""
    from frame_sequence import process_frame_sequence

    opt = optimize_loop_window(
        paths,
        target_frames=target_frames,
        seam_over_mid_max=seam_over_mid_max,
        spike_factor=spike_factor,
        min_keep_ratio=min_keep_ratio,
    )

    fb_picked, trim_meta = process_frame_sequence(
        paths,
        skip_lead_ratio=fallback_lead_ratio,
        skip_trail_ratio=fallback_trail_ratio,
        sample_frames=target_frames,
        trim_lead=True,
        trim_trail=True,
    )
    fb_stats = evaluate_loop_sequence(fb_picked)

    use_opt = opt["ok"] or (
        float(opt.get("seam_over_mid") or 1e9) <= float(fb_stats["seam_over_mid"])
    )
    # Soft-pass: keep optimizer window when it beats fallback even above threshold.
    if use_opt and opt.get("paths"):
        meta = {
            "strategy": "optimize_loop" if opt["ok"] else "optimize_loop_best_effort",
            "lead_dropped": int(opt["lead_dropped"]),
            "trail_dropped": int(opt["trail_dropped"]),
            "start_index": int(opt["start_index"]),
            "end_index": int(opt["end_index"]),
            "seam_over_mid": float(opt["seam_over_mid"]),
            "seam_over_mid_max": float(seam_over_mid_max),
            "keep_ratio": float(opt.get("keep_ratio") or 0),
            "optimize_ok": bool(opt["ok"]),
            "fallback_seam_over_mid": float(fb_stats["seam_over_mid"]),
        }
        return list(opt["paths"]), meta

    meta = {
        "strategy": "fallback_ratios",
        "lead_dropped": int(trim_meta["lead_dropped"]),
        "trail_dropped": int(trim_meta["trail_dropped"]),
        "optimize_reason": opt.get("reason"),
        "optimize_seam_over_mid": float(opt.get("seam_over_mid") or 0),
        "optimize_ok": bool(opt.get("ok")),
        "seam_over_mid": float(fb_stats["seam_over_mid"]),
        "seam_over_mid_max": float(seam_over_mid_max),
        "fallback_lead_ratio": float(fallback_lead_ratio),
        "fallback_trail_ratio": float(fallback_trail_ratio),
    }
    return fb_picked, meta
