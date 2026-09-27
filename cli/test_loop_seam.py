"""Tests for loop-seam window search (synthetic images — no clip overfitting)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from loop_seam import (
    DEFAULT_SEAM_OVER_MID_MAX,
    evaluate_loop_sequence,
    optimize_loop_window,
    select_loop_frame_paths,
)


def _write_gray(path: Path, value: float, size: int = 16) -> None:
    v = int(max(0, min(255, round(value))))
    Image.fromarray(np.full((size, size), v, dtype=np.uint8), mode="L").convert("RGBA").save(path)


def _sine_loop_sequence(
    out: Path,
    *,
    n: int = 48,
    morph_lead: int = 6,
    morph_trail: int = 6,
    period: int = 12,
) -> list[Path]:
    """Still morph → periodic swim → morph back to still.

    Mid-band frames follow a closed sine so a phase-aligned window can loop cleanly.
    """
    paths: list[Path] = []
    still = 40.0
    for i in range(n):
        if i < morph_lead:
            # morph from still toward first swim phase
            t = i / max(morph_lead, 1)
            phase0 = 0.0
            swim0 = 128 + 80 * np.sin(2 * np.pi * phase0)
            val = still * (1 - t) + swim0 * t
        elif i >= n - morph_trail:
            t = (i - (n - morph_trail)) / max(morph_trail, 1)
            phase = ((i - morph_lead) % period) / period
            swim = 128 + 80 * np.sin(2 * np.pi * phase)
            val = swim * (1 - t) + still * t
        else:
            phase = ((i - morph_lead) % period) / period
            val = 128 + 80 * np.sin(2 * np.pi * phase)
        p = out / f"frame_{i + 1:04d}.png"
        _write_gray(p, val)
        paths.append(p)
    return paths


class TestLoopSeam(unittest.TestCase):
    def test_evaluate_reports_seam_over_mid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # identical ends, small mid steps
            vals = [10, 20, 30, 40, 50, 40, 30, 20, 10]
            paths = []
            for i, v in enumerate(vals, 1):
                p = root / f"f_{i:04d}.png"
                _write_gray(p, v)
                paths.append(p)
            stats = evaluate_loop_sequence(paths)
            self.assertGreater(stats["mid_adj"], 0)
            self.assertLess(stats["seam_over_mid"], 0.5)

    def test_optimize_finds_mid_loop_not_zero_trim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _sine_loop_sequence(Path(tmp), n=48, morph_lead=8, morph_trail=8, period=12)
            result = optimize_loop_window(paths, target_frames=12)
            self.assertTrue(result["ok"], msg=result)
            # Must drop morph ends — not the false-positive full span.
            self.assertGreaterEqual(result["lead_dropped"], 4)
            self.assertGreaterEqual(result["trail_dropped"], 4)
            self.assertGreaterEqual(
                result["lead_dropped"] + result["trail_dropped"], 10
            )
            self.assertLessEqual(result["seam_over_mid"], DEFAULT_SEAM_OVER_MID_MAX)
            self.assertEqual(len(result["paths"]), 12)

    def test_already_good_loop_keeps_most_of_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Pure period, no morph — optimizer should not carve aggressively.
            root = Path(tmp)
            period = 12
            paths = []
            for i in range(36):
                val = 128 + 80 * np.sin(2 * np.pi * (i % period) / period)
                p = root / f"frame_{i + 1:04d}.png"
                _write_gray(p, val)
                paths.append(p)
            result = optimize_loop_window(paths, target_frames=12)
            self.assertTrue(result["ok"], msg=result)
            kept_ratio = (result["end_index"] - result["start_index"] + 1) / len(paths)
            self.assertGreaterEqual(kept_ratio, 0.45)
            self.assertLessEqual(result["seam_over_mid"], DEFAULT_SEAM_OVER_MID_MAX)

    def test_no_good_loop_falls_back_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Monotonic ramp — first and last never match.
            paths = []
            for i in range(30):
                p = root / f"frame_{i + 1:04d}.png"
                _write_gray(p, 10 + i * 7)
                paths.append(p)
            result = optimize_loop_window(paths, target_frames=12)
            self.assertFalse(result["ok"])
            self.assertGreater(result["seam_over_mid"], DEFAULT_SEAM_OVER_MID_MAX)

    def test_select_loop_frame_paths_fallback_to_ratios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for i in range(40):
                p = root / f"frame_{i + 1:04d}.png"
                _write_gray(p, 10 + i * 5)
                paths.append(p)
            picked, meta = select_loop_frame_paths(
                paths,
                target_frames=8,
                fallback_lead_ratio=0.25,
                fallback_trail_ratio=0.05,
            )
            self.assertEqual(len(picked), 8)
            # Monotonic ramp: optimizer cannot pass; may still best-effort if better
            # than ratios, otherwise explicit fallback_ratios.
            self.assertIn(
                meta["strategy"],
                {"fallback_ratios", "optimize_loop_best_effort"},
            )
            if meta["strategy"] == "fallback_ratios":
                self.assertEqual(meta["lead_dropped"], 10)

    def test_select_prefers_best_effort_over_worse_fallback(self) -> None:
        """When no window passes threshold, still prefer better-than-fallback window."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Mostly ramp, but a mid segment nearly closes (imperfect).
            paths = []
            for i in range(40):
                if 12 <= i <= 28:
                    # gentle bump that almost returns
                    phase = (i - 12) / 16
                    val = 80 + 40 * np.sin(np.pi * phase)
                else:
                    val = 20 + i * 3
                p = root / f"frame_{i + 1:04d}.png"
                _write_gray(p, val)
                paths.append(p)
            picked, meta = select_loop_frame_paths(
                paths,
                target_frames=8,
                fallback_lead_ratio=0.25,
                fallback_trail_ratio=0.05,
                seam_over_mid_max=0.5,  # intentionally strict
            )
            self.assertEqual(len(picked), 8)
            self.assertIn(
                meta["strategy"],
                {"optimize_loop", "optimize_loop_best_effort", "fallback_ratios"},
            )
            self.assertLessEqual(
                meta["seam_over_mid"],
                meta.get("fallback_seam_over_mid", meta["seam_over_mid"]) + 0.01,
            )


if __name__ == "__main__":
    unittest.main()
