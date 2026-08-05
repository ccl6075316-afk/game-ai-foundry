"""Tests for Codex official binary download source resolution."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from codex_sources import _asset_patterns, codex_download_sources, platform_key


class CodexSourcesTests(unittest.TestCase):
    def test_platform_key_known(self) -> None:
        key = platform_key()
        self.assertIn(key, {"win64", "win_arm64", "macos_arm64", "macos_x64", "linux64", "linux_arm64"})

    def test_win64_prefers_bare_exe(self) -> None:
        patterns = _asset_patterns("win64")
        self.assertEqual(patterns[0][1], "exe")
        self.assertIn(r"x86_64-pc-windows-msvc\.exe", patterns[0][0])

    @patch("codex_sources._http_get_json")
    def test_codex_download_sources_picks_matching_asset(self, http: object) -> None:
        http.return_value = {
            "tag_name": "rust-v0.146.1",
            "assets": [
                {
                    "name": "codex-x86_64-pc-windows-msvc.exe",
                    "browser_download_url": "https://example.com/codex.exe",
                },
                {
                    "name": "codex-x86_64-pc-windows-msvc.exe.zip",
                    "browser_download_url": "https://example.com/codex.zip",
                },
            ],
        }
        sources = codex_download_sources("win64")
        self.assertGreaterEqual(len(sources), 1)
        self.assertEqual(sources[0]["kind"], "exe")
        self.assertEqual(sources[0]["url"], "https://example.com/codex.exe")

    @patch("codex_sources._http_get_json", return_value=None)
    def test_codex_download_sources_empty_when_api_fails(self, _http: object) -> None:
        self.assertEqual(codex_download_sources("win64"), [])


if __name__ == "__main__":
    unittest.main()
