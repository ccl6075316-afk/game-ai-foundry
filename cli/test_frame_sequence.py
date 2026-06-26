"""Tests for trim-then-sample frame sequence helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from frame_sequence import (
    process_frame_sequence,
    sample_frame_paths_evenly,
    trim_frame_paths,
)


class TestFrameSequence(unittest.TestCase):
    def _paths(self, n: int) -> list[Path]:
        return [Path(f"frame_{i:04d}.png") for i in range(1, n + 1)]

    def test_trim_then_sample_full_pipeline(self) -> None:
        frames = self._paths(61)
        picked, meta = process_frame_sequence(
            frames,
            skip_lead_ratio=0.25,
            skip_trail_ratio=0.05,
            sample_frames=8,
        )
        self.assertEqual(len(picked), 8)
        self.assertEqual(meta["lead_dropped"], 15)
        self.assertEqual(meta["trail_dropped"], 3)
        self.assertEqual(meta["sampled_to"], 8)
        self.assertEqual(picked[0].name, "frame_0016.png")

    def test_pre_trimmed_pre_sampled_skips_both(self) -> None:
        frames = self._paths(8)
        picked, meta = process_frame_sequence(
            frames,
            sample_frames=8,
            pre_trimmed=True,
            pre_sampled=True,
        )
        self.assertEqual(len(picked), 8)
        self.assertEqual(meta["lead_dropped"], 0)
        self.assertEqual(meta["sampled_to"], 0)

    def test_sample_evenly(self) -> None:
        picked = sample_frame_paths_evenly(self._paths(43), 8)
        self.assertEqual(len(picked), 8)
        self.assertEqual(picked[0].name, "frame_0001.png")
        self.assertEqual(picked[-1].name, "frame_0043.png")

    def test_trim_disabled_keeps_all_frames(self) -> None:
        frames = self._paths(61)
        picked, meta = process_frame_sequence(
            frames,
            trim_lead=False,
            trim_trail=False,
            sample_frames=8,
        )
        self.assertEqual(meta["lead_dropped"], 0)
        self.assertEqual(meta["trail_dropped"], 0)
        self.assertEqual(len(picked), 8)

    def test_resolve_transition_trim_defaults(self) -> None:
        from frame_sequence import resolve_transition_trim

        opts = resolve_transition_trim({})
        self.assertTrue(opts.trim_lead)
        self.assertTrue(opts.trim_trail)

        off = resolve_transition_trim({}, trim_lead=False, trim_trail=False)
        self.assertFalse(off.trim_lead)
        self.assertEqual(off.as_skip_ratios(), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
