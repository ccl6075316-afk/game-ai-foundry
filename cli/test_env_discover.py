"""Tests for retained environment discovery."""

from __future__ import annotations

import json
import unittest

from env_discover import (
    discover_capabilities,
    discover_config,
    discover_pipeline,
    discover_tools,
    run_doctor,
)


class EnvDiscoverTest(unittest.TestCase):
    def test_pipeline_always_available(self) -> None:
        info = discover_pipeline()
        self.assertTrue(info["available"])
        self.assertIn("repo_root", info)

    def test_tools_cover_core_toolchain(self) -> None:
        tools = discover_tools({})
        self.assertEqual(
            {"python", "git", "godot", "dotnet", "ffmpeg", "ffprobe"},
            set(tools),
        )

    def test_config_shape_covers_api_keys_and_toolchain(self) -> None:
        config = discover_config(
            {
                "host": {"api_key": "sk-test"},
                "video": {"api_key": "seed-test"},
                "toolchain": {
                    "bin_dir": "/tmp/bin",
                    "dotnet_dir": "/tmp/dotnet",
                },
            }
        )
        self.assertEqual(config["host_key"], "set")
        self.assertEqual(config["seedance_key"], "set")
        self.assertEqual(config["toolchain_bin_dir"], "/tmp/bin")
        self.assertEqual(config["toolchain_dotnet_dir"], "/tmp/dotnet")

    def test_doctor_report_has_no_runtime_sections(self) -> None:
        report = run_doctor({})
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertIn("pipeline", report)
        self.assertIn("tools", report)
        self.assertIn("config", report)
        self.assertIn("capabilities", report)
        self.assertNotIn("executors", serialized)
        self.assertNotIn("agents", serialized)

    def test_capabilities_include_pipeline_and_retained_guards(self) -> None:
        caps = discover_capabilities(
            {},
            discover_tools({}),
            discover_config({}),
        )
        for key in (
            "pipeline_run",
            "image_api",
            "video_api",
            "ffmpeg",
            "godot_assemble",
            "dotnet",
            "media_validate",
            "matting_validate",
            "cjk_guard",
            "pipeline_heal",
        ):
            self.assertIn(key, caps)


if __name__ == "__main__":
    unittest.main()
