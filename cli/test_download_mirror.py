"""Tests for optional GitHub download mirror rewriting."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from download_mirror import DEFAULT_PREFIX, mirror_enabled, rewrite_url


class DownloadMirrorTests(unittest.TestCase):
    def test_default_off_passthrough(self) -> None:
        url = "https://github.com/openai/codex/releases/download/v1/x.exe"
        with patch.dict(os.environ, {"GAMEFACTORY_DOWNLOAD_MIRROR": ""}, clear=False):
            with patch("download_mirror._load_config", return_value={}):
                self.assertEqual(rewrite_url(url), url)

    def test_enabled_prefixes_github(self) -> None:
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/a.zip"
        out = rewrite_url(url, enabled=True)
        self.assertEqual(out, f"{DEFAULT_PREFIX}{url}")

    def test_enabled_prefixes_api(self) -> None:
        url = "https://api.github.com/repos/godotengine/godot/releases/latest"
        out = rewrite_url(url, enabled=True)
        self.assertEqual(out, f"{DEFAULT_PREFIX}{url}")

    def test_non_github_unchanged(self) -> None:
        url = "https://evermeet.cx/ffmpeg/getrelease/zip"
        self.assertEqual(rewrite_url(url, enabled=True), url)

    def test_idempotent(self) -> None:
        url = "https://github.com/openai/codex/releases/download/v1/x.exe"
        once = rewrite_url(url, enabled=True)
        twice = rewrite_url(once, enabled=True)
        self.assertEqual(once, twice)

    def test_config_toggle(self) -> None:
        with patch.dict(os.environ, {"GAMEFACTORY_DOWNLOAD_MIRROR": ""}, clear=False):
            self.assertFalse(mirror_enabled({"toolchain": {"download_mirror": False}}))
            self.assertTrue(mirror_enabled({"toolchain": {"download_mirror": True}}))

    def test_custom_prefix(self) -> None:
        url = "https://github.com/a/b/releases/download/v1/f.zip"
        out = rewrite_url(
            url,
            enabled=True,
            config={"toolchain": {"download_mirror_prefix": "https://gh-proxy.com"}},
        )
        self.assertEqual(out, f"https://gh-proxy.com/{url}")


if __name__ == "__main__":
    unittest.main()
