# -*- coding: utf-8 -*-
"""Unit tests for sprite frame count resolution (3–4s → 24 default)."""

from __future__ import annotations

import unittest

from video_frames import DEFAULT_SPRITE_FRAMES, resolve_sprite_frame_count


class ResolveSpriteFrameCountTests(unittest.TestCase):
    def test_explicit_wins(self) -> None:
        self.assertEqual(
            resolve_sprite_frame_count(explicit=16, duration_seconds=4),
            16,
        )

    def test_default_for_typical_clip(self) -> None:
        self.assertEqual(DEFAULT_SPRITE_FRAMES, 24)
        self.assertEqual(resolve_sprite_frame_count(duration_seconds=4), 24)
        self.assertEqual(resolve_sprite_frame_count(duration_seconds=3), 24)

    def test_longer_clip_scales_up(self) -> None:
        self.assertEqual(resolve_sprite_frame_count(duration_seconds=8), 48)

    def test_config_floor(self) -> None:
        cfg = {"video": {"split_frames": {"frames": 24}}}
        self.assertEqual(resolve_sprite_frame_count(config=cfg), 24)
        self.assertEqual(
            resolve_sprite_frame_count(duration_seconds=10, config=cfg),
            60,
        )


if __name__ == "__main__":
    unittest.main()
