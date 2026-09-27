"""Tests for stable subject compositing, playback fps, and native (non-baked) import."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from display_size import DisplaySize
from godot_import import (
    import_sprite_frames,
    native_subject_display_size,
    resolve_bake_display_size,
    resolve_playback_fps,
    save_animation_frames_at_display_size,
    save_texture_at_display_size,
)


class GodotImportStableDisplayTest(unittest.TestCase):
    def test_playback_fps_uses_usable_window(self) -> None:
        fps = resolve_playback_fps(
            24,
            source_duration_seconds=4.0,
            lead_ratio=0.25,
            trail_ratio=0.05,
        )
        self.assertAlmostEqual(fps, 24 / 2.8, places=2)

    def test_bake_display_size_defaults_off(self) -> None:
        self.assertFalse(resolve_bake_display_size({}))
        self.assertFalse(resolve_bake_display_size({"godot": {"bake_display_size": False}}))
        self.assertTrue(resolve_bake_display_size({"godot": {"bake_display_size": True}}))
        self.assertTrue(resolve_bake_display_size({}, bake_display_size=True))

    def test_plate_mode_keeps_relative_layout(self) -> None:
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            dest_dir = Path(tmp) / "dest"
            src_dir.mkdir()
            for i, body_w in enumerate((100, 200), start=1):
                img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                x0 = (400 - body_w) // 2
                draw.ellipse((x0, 80, x0 + body_w, 120), fill=(20, 120, 200, 255))
                img.save(src_dir / f"frame_{i:04d}.png")

            sources = sorted(src_dir.glob("frame_*.png"))
            display = DisplaySize(160, 80)
            dests = save_animation_frames_at_display_size(
                sources, dest_dir, display, mode="plate"
            )
            self.assertEqual(len(dests), 2)

            widths = []
            for path in dests:
                im = Image.open(path).convert("RGBA")
                self.assertEqual(im.size, (160, 80))
                bbox = im.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
                assert bbox is not None
                widths.append(bbox[2] - bbox[0])

            self.assertAlmostEqual(widths[1] / widths[0], 2.0, delta=0.12)

    def test_clip_subject_preserves_relative_size(self) -> None:
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            dest_dir = Path(tmp) / "dest"
            src_dir.mkdir()
            for i, body_w in enumerate((100, 200), start=1):
                img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                x0 = (400 - body_w) // 2
                draw.ellipse((x0, 80, x0 + body_w, 120), fill=(20, 120, 200, 255))
                img.save(src_dir / f"frame_{i:04d}.png")

            sources = sorted(src_dir.glob("frame_*.png"))
            display = DisplaySize(160, 90)
            dests = save_animation_frames_at_display_size(
                sources, dest_dir, display, mode="clip_subject"
            )
            widths = []
            for path in dests:
                im = Image.open(path).convert("RGBA")
                bbox = im.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
                assert bbox is not None
                widths.append(bbox[2] - bbox[0])
            self.assertAlmostEqual(widths[1] / widths[0], 2.0, delta=0.15)
            self.assertGreaterEqual(widths[1], int(160 * 0.92) - 2)

    def test_native_subject_display_keeps_largest_subject_pixels(self) -> None:
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            src_dir.mkdir()
            for i, body_w in enumerate((100, 200), start=1):
                img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                x0 = (400 - body_w) // 2
                draw.ellipse((x0, 60, x0 + body_w, 140), fill=(20, 120, 200, 255))
                img.save(src_dir / f"frame_{i:04d}.png")
            sources = sorted(src_dir.glob("frame_*.png"))
            display = native_subject_display_size(sources, fill=0.92)
            self.assertGreaterEqual(display.width, int(200 / 0.92) - 1)
            self.assertGreaterEqual(display.height, 80)

    def test_import_default_does_not_bake_tiny_display_size(self) -> None:
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "game"
            (project / "assets" / "sprites").mkdir(parents=True)
            src = root / "nobg"
            src.mkdir()
            for i in range(1, 4):
                img = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.ellipse((80, 60, 240, 120), fill=(10, 80, 160, 255))
                img.save(src / f"frame_{i:04d}.png")

            info = import_sprite_frames(
                project,
                asset="fish_swim",
                input_dir=src,
                fps=12,
                pre_trimmed=True,
                pre_sampled=True,
                display_size={"width": 64, "height": 36},
                stable_subject=True,
                bake_display_size=False,
            )
            out = sorted((project / "assets/sprites/fish_swim").glob("frame_*.png"))
            self.assertEqual(len(out), 3)
            w, h = Image.open(out[0]).size
            self.assertGreater(w, 64)
            self.assertGreater(h, 36)
            self.assertEqual(info["bake_display_size"], "false")

    def test_still_copy_keeps_source_pixels_by_default(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "still.png"
            Image.new("RGBA", (256, 128), (1, 2, 3, 255)).save(src)
            dest = root / "out.png"
            save_texture_at_display_size(src, dest, DisplaySize(32, 16), bake=False)
            self.assertEqual(Image.open(dest).size, (256, 128))
            save_texture_at_display_size(src, dest, DisplaySize(32, 16), bake=True)
            self.assertEqual(Image.open(dest).size, (32, 16))


if __name__ == "__main__":
    unittest.main()
