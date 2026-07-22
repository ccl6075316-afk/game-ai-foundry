"""Unit tests for style img2img strength config helper."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr
from unittest.mock import MagicMock, patch

from gamefactory import (
    DEFAULT_STYLE_IMG2IMG_STRENGTH,
    apply_style_img2img_strength,
    generate_image,
    resolve_style_img2img_strength,
)


class StyleImg2ImgStrengthTests(unittest.TestCase):
    def test_resolve_default_when_key_missing(self) -> None:
        self.assertEqual(resolve_style_img2img_strength({}), DEFAULT_STYLE_IMG2IMG_STRENGTH)
        self.assertEqual(
            resolve_style_img2img_strength({"image": {}}),
            DEFAULT_STYLE_IMG2IMG_STRENGTH,
        )

    def test_resolve_explicit_value(self) -> None:
        self.assertEqual(
            resolve_style_img2img_strength({"image": {"style_img2img_strength": 0.5}}),
            0.5,
        )

    def test_resolve_null_skips(self) -> None:
        self.assertIsNone(
            resolve_style_img2img_strength({"image": {"style_img2img_strength": None}})
        )

    def test_resolve_clamps_out_of_range(self) -> None:
        self.assertEqual(
            resolve_style_img2img_strength({"image": {"style_img2img_strength": 1.5}}),
            1.0,
        )
        self.assertEqual(
            resolve_style_img2img_strength({"image": {"style_img2img_strength": -0.2}}),
            0.0,
        )

    def test_resolve_invalid_value_skips(self) -> None:
        self.assertIsNone(
            resolve_style_img2img_strength({"image": {"style_img2img_strength": "bad"}})
        )

    def test_apply_skips_without_reference(self) -> None:
        payload: dict = {}
        self.assertIsNone(apply_style_img2img_strength(payload, {}, has_reference=False))
        self.assertNotIn("image_config", payload)

    def test_apply_merges_image_config(self) -> None:
        payload = {"image_config": {"foo": "bar"}}
        buf = io.StringIO()
        with redirect_stderr(buf):
            strength = apply_style_img2img_strength(
                payload,
                {"image": {"style_img2img_strength": 0.4}},
                has_reference=True,
            )
        self.assertEqual(strength, 0.4)
        self.assertEqual(payload["image_config"], {"foo": "bar", "strength": 0.4})
        self.assertIn("strength=0.4", buf.getvalue())

    @patch("gamefactory.http_post")
    def test_generate_image_chat_path_applies_strength(self, post: MagicMock) -> None:
        import base64
        from pathlib import Path

        png = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"images": [{"image_url": {"url": f"data:image/png;base64,{png}"}}]}}]
        }
        post.return_value = resp

        ref = Path("tmp-ref.png")
        out = Path("tmp-out.png")
        try:
            ref.write_bytes(b"\x89PNG\r\n\x1a\nref")
            generate_image(
                model="google/gemini-3.1-flash-image",
                prompt="a cat",
                output=out,
                size="1024x1024",
                api_key="sk-test",
                api_base="https://openrouter.ai/api/v1",
                reference_image=ref,
                config={"image": {"style_img2img_strength": 0.3}},
            )
            payload = post.call_args.kwargs["json"]
            self.assertEqual(payload["image_config"]["strength"], 0.3)
        finally:
            ref.unlink(missing_ok=True)
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
