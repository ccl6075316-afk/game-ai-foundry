"""Tests for video frame extraction skip logic."""

from __future__ import annotations

import unittest

from video_frames import (
    compute_sample_timestamps,
    resolve_skip_bounds,
)


class TestVideoFramesSkip(unittest.TestCase):
    def test_skip_bounds_default_ratio(self) -> None:
        t_start, t_end = resolve_skip_bounds(4.0, {})
        self.assertAlmostEqual(t_start, 1.0)
        self.assertAlmostEqual(t_end, 3.8)

    def test_sample_timestamps_inside_window(self) -> None:
        stamps = compute_sample_timestamps(1.0, 3.8, 8)
        self.assertEqual(len(stamps), 8)
        self.assertAlmostEqual(stamps[0], 1.0)
        self.assertAlmostEqual(stamps[-1], 3.8)

    def test_skip_bounds_no_trim(self) -> None:
        t_start, t_end = resolve_skip_bounds(4.0, {}, trim_lead=False, trim_trail=False)
        self.assertAlmostEqual(t_start, 0.0)
        self.assertAlmostEqual(t_end, 4.0)

    def test_skip_bounds_override_seconds(self) -> None:
        t_start, t_end = resolve_skip_bounds(
            4.0, {}, skip_lead_seconds=1.0, skip_trail_seconds=0.2
        )
        self.assertAlmostEqual(t_start, 1.0)
        self.assertAlmostEqual(t_end, 3.8)


if __name__ == "__main__":
    unittest.main()
