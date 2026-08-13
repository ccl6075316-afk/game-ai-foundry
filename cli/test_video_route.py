"""Unit tests for video credential routing."""

from __future__ import annotations

import unittest

from env_discover import discover_capabilities, discover_config
from video_route import (
    infer_video_backend,
    normalize_video_model,
    resolve_video_credentials,
)


class VideoRouteTests(unittest.TestCase):
    def test_normalize_strips_vendor_prefix_off_openrouter(self) -> None:
        self.assertEqual(
            normalize_video_model("google/veo-3.1", "https://api.apilio.ai/v1"),
            "veo3.1",
        )
        self.assertEqual(
            normalize_video_model("veo3.1-fast", "https://api.apilio.ai/v1"),
            "veo3.1-fast",
        )
        self.assertEqual(
            normalize_video_model("x-ai/grok-imagine-video", "https://api.apilio.ai/v1"),
            "grok-imagine-video",
        )
        self.assertEqual(
            normalize_video_model(
                "google/veo-3.1", "https://openrouter.ai/api/v1"
            ),
            "google/veo-3.1",
        )

    def test_backend_seedance_vs_compat(self) -> None:
        self.assertEqual(infer_video_backend("seedance", ""), "seedance")
        self.assertEqual(infer_video_backend("", ""), "seedance")
        self.assertEqual(
            infer_video_backend(
                "custom", "https://ark.cn-beijing.volces.com/api/v3"
            ),
            "seedance",
        )
        self.assertEqual(
            infer_video_backend("apilio", "https://api.apilio.ai/v1"),
            "openai_compat",
        )
        self.assertEqual(
            infer_video_backend("", "https://api.apilio.ai/v1"),
            "openai_compat",
        )

    def test_apilio_provider_account(self) -> None:
        creds = resolve_video_credentials(
            {
                "provider_accounts": {
                    "apilio": {
                        "api_key": "sk-test",
                        "api_base": "https://api.apilio.ai/v1",
                    }
                },
                "video": {"provider": "apilio", "model": "google/veo-3.1"},
            }
        )
        self.assertTrue(creds.usable)
        self.assertEqual(creds.provider, "apilio")
        self.assertEqual(creds.backend, "openai_compat")
        self.assertEqual(creds.model, "veo3.1")
        self.assertEqual(creds.api_base, "https://api.apilio.ai/v1")
        self.assertEqual(creds.api_key, "sk-test")

    def test_legacy_seedance_key_without_provider(self) -> None:
        creds = resolve_video_credentials(
            {"video": {"api_key": "ark-test", "model": "mini"}}
        )
        self.assertTrue(creds.usable)
        self.assertEqual(creds.provider, "seedance")
        self.assertEqual(creds.backend, "seedance")
        self.assertEqual(creds.model, "mini")

    def test_legacy_custom_base_without_provider_is_compat(self) -> None:
        creds = resolve_video_credentials(
            {
                "video": {
                    "api_key": "sk-test",
                    "api_base": "https://api.apilio.ai/v1",
                    "model": "veo3.1",
                }
            }
        )
        self.assertTrue(creds.usable)
        self.assertEqual(creds.backend, "openai_compat")
        self.assertEqual(creds.provider, "")
        self.assertEqual(creds.model, "veo3.1")

    def test_explicit_key_and_apilio_base_without_provider(self) -> None:
        creds = resolve_video_credentials(
            {"video": {}},
            explicit_key="sk-test",
            explicit_base="https://api.apilio.ai/v1",
            explicit_model="google/veo-3.1",
        )
        self.assertTrue(creds.usable)
        self.assertEqual(creds.backend, "openai_compat")
        self.assertEqual(creds.model, "veo3.1")

    def test_unconfigured_is_not_usable(self) -> None:
        creds = resolve_video_credentials({"video": {}})
        self.assertFalse(creds.usable)
        self.assertEqual(creds.provider, "")

    def test_doctor_video_api_accepts_apilio_account(self) -> None:
        config = {
            "provider_accounts": {
                "apilio": {
                    "api_key": "sk-test",
                    "api_base": "https://api.apilio.ai/v1",
                }
            },
            "video": {"provider": "apilio", "model": "veo-3.1"},
        }
        cfg_status = discover_config(config)
        caps = discover_capabilities(config, cfg_status=cfg_status)
        self.assertTrue(caps["video_api"])

    def test_doctor_video_api_false_when_empty(self) -> None:
        config = {"video": {}}
        cfg_status = discover_config(config)
        caps = discover_capabilities(config, cfg_status=cfg_status)
        self.assertFalse(caps["video_api"])
