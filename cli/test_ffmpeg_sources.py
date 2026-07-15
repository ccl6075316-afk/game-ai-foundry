"""Tests for FFmpeg download source resolution."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ffmpeg_sources import ffmpeg_download_sources, platform_key


class FfmpegSourcesTests(unittest.TestCase):
    def test_platform_key_macos_arm64(self) -> None:
        with patch("ffmpeg_sources.sys.platform", "darwin"):
            with patch("ffmpeg_sources.platform.machine", return_value="arm64"):
                self.assertEqual(platform_key(), "macos_arm64")

    @patch("ffmpeg_sources._btbn_asset_url", return_value="https://example.com/ffmpeg.zip")
    def test_includes_btbn_when_available(self, _mock: object) -> None:
        sources = ffmpeg_download_sources("macos_arm64")
        self.assertTrue(any(s["label"] == "BtbN-GitHub" for s in sources))

    @patch("ffmpeg_sources._btbn_asset_url", return_value=None)
    def test_macos_includes_evermeet_fallback(self, _mock: object) -> None:
        sources = ffmpeg_download_sources("macos_arm64")
        self.assertTrue(any("evermeet" in s["label"] for s in sources))


if __name__ == "__main__":
    unittest.main()
