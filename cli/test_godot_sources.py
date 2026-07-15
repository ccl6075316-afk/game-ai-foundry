"""Tests for Godot download source resolution."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from godot_sources import godot_download_source, godot_mono_asset_name


MOCK_RELEASE = {
    "tag_name": "4.6.3-stable",
    "assets": [
        {
            "name": "Godot_v4.6.3-stable_mono_macos.universal.zip",
            "browser_download_url": "https://example.com/godot-macos.zip",
        },
        {
            "name": "Godot_v4.6.3-stable_mono_win64.zip",
            "browser_download_url": "https://example.com/godot-win.zip",
        },
    ],
}


class GodotSourcesTests(unittest.TestCase):
    @patch("godot_sources._http_get_json", return_value=MOCK_RELEASE)
    def test_macos_mono_asset(self, _api: object) -> None:
        name = godot_mono_asset_name("macos_arm64")
        self.assertEqual(name, "Godot_v4.6.3-stable_mono_macos.universal.zip")

    @patch("godot_sources._http_get_json", return_value=MOCK_RELEASE)
    def test_win64_download_source(self, _api: object) -> None:
        src = godot_download_source("win64")
        self.assertIsNotNone(src)
        assert src is not None
        self.assertIn("godot-win.zip", src["url"])
        self.assertEqual(src["kind"], "zip")


if __name__ == "__main__":
    unittest.main()
