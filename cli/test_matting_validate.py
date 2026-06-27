"""Tests for matting edge validation and color-key defaults."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from image_cmds import remove_bg_color_key
from matting_config import DEFAULT_COLOR_KEY, DEFAULT_VALIDATE_EDGES
from matting_validate import validate_matting_edges


class MattingValidateTests(unittest.TestCase):
    def test_defaults_include_morph_cleanup(self) -> None:
        self.assertGreaterEqual(DEFAULT_COLOR_KEY["morph_erode"], 1)
        self.assertGreaterEqual(DEFAULT_COLOR_KEY["despeckle"], 1)

    def test_colored_sprite_passes_after_color_key(self) -> None:
        img = np.full((128, 128, 3), 255, dtype=np.uint8)
        cv2.circle(img, (64, 64), 36, (200, 100, 50), -1)
        rgba = remove_bg_color_key(img, **DEFAULT_COLOR_KEY)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nobg.png"
            cv2.imwrite(str(path), rgba)
            result = validate_matting_edges(path, **DEFAULT_VALIDATE_EDGES)
        self.assertTrue(result.ok, result.message)


if __name__ == "__main__":
    unittest.main()
