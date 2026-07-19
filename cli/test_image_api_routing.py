"""Unit tests for image model routing (chat modalities vs Images API)."""

from __future__ import annotations

import base64
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gamefactory import (
    extract_images_api_payload,
    generate_image,
    images_api_endpoint,
    normalize_image_model,
    uses_dedicated_images_api,
)


class ImageApiRoutingTests(unittest.TestCase):
    def test_normalize_aliases(self) -> None:
        self.assertEqual(
            normalize_image_model("gptimage 2", "https://openrouter.ai/api/v1"),
            "openai/gpt-image-2",
        )
        self.assertEqual(
            normalize_image_model("gpt-image-2", "https://openrouter.ai/api/v1"),
            "openai/gpt-image-2",
        )
        self.assertEqual(
            normalize_image_model("gpt-image-2", "https://api.openai.com/v1"),
            "gpt-image-2",
        )
        self.assertEqual(
            normalize_image_model(
                "images/openai/gpt-image-2", "https://openrouter.ai/api/v1"
            ),
            "openai/gpt-image-2",
        )

    def test_dedicated_detection(self) -> None:
        self.assertTrue(uses_dedicated_images_api("openai/gpt-image-2"))
        self.assertTrue(uses_dedicated_images_api("gpt-image-1-mini"))
        self.assertFalse(uses_dedicated_images_api("openai/gpt-5.4-image-2"))
        self.assertFalse(uses_dedicated_images_api("google/gemini-3.1-flash-image"))

    def test_endpoints(self) -> None:
        self.assertTrue(
            images_api_endpoint("https://openrouter.ai/api/v1").endswith("/images")
        )
        self.assertTrue(
            images_api_endpoint("https://api.openai.com/v1").endswith(
                "/images/generations"
            )
        )

    def test_extract_b64(self) -> None:
        url = extract_images_api_payload({"data": [{"b64_json": "YWJj"}]})
        self.assertTrue(url.startswith("data:image/png;base64,"))

    @patch("gamefactory.http_post")
    def test_generate_routes_gpt_image_2_to_images_api(self, post: MagicMock) -> None:
        png = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": [{"b64_json": png}]}
        post.return_value = resp

        out = Path("tmp-gpt-image-2-test.png")
        try:
            generate_image(
                model="gptimage 2",
                prompt="a cat",
                output=out,
                size="1280x720",
                api_key="sk-test",
                api_base="https://openrouter.ai/api/v1",
            )
            self.assertTrue(out.is_file())
            args = post.call_args
            self.assertIn("/images", args.args[1])
            payload = args.kwargs["json"]
            self.assertEqual(payload["model"], "openai/gpt-image-2")
            self.assertEqual(payload["prompt"], "a cat")
            self.assertNotIn("modalities", payload)
        finally:
            if out.exists():
                out.unlink()


if __name__ == "__main__":
    unittest.main()
