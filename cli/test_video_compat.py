"""Unit tests for OpenAI-compatible video adapter (mocked HTTP)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from video_cmds import generate_cmd
from video_compat import (
    CompatVideoError,
    _resized_png_bytes,
    build_compat_submit_attempts,
    build_vendor_submit_attempts,
    extract_task_id,
    extract_video_url,
    generate_compat_video,
    video_vendor_family,
)
from video_config import resolve_video_generate_settings


class _FakeResp:
    def __init__(
        self,
        status: int,
        json_data: object | None = None,
        text: str = "",
        content: bytes = b"",
    ) -> None:
        self.status_code = status
        self._json = json_data
        self.text = text or (json.dumps(json_data) if json_data is not None else "")
        self.content = content

    def json(self) -> object:
        if self._json is None:
            raise ValueError("no json")
        return self._json


class VideoCompatTests(unittest.TestCase):
    def test_attempts_order_and_first_frame_fields(self) -> None:
        attempts = build_compat_submit_attempts(
            model="veo3.1",
            prompt="swim",
            duration=6,
            resolution="720p",
            ratio="1:1",
            generate_audio=False,
            reference_data_url="data:image/png;base64,abc",
        )
        paths = [rel for rel, _ in attempts]
        self.assertEqual(paths[0], "videos")
        self.assertIn("videos/generations", paths)
        first_payload = attempts[0][1]
        self.assertEqual(first_payload["model"], "veo3.1")
        self.assertEqual(first_payload["ratio"], "1:1")
        self.assertNotIn("aspect_ratio", first_payload)
        self.assertEqual(first_payload["input_reference"], "data:image/png;base64,abc")
        self.assertIsInstance(first_payload["input_reference"], str)
        gen_payload = next(p for rel, p in attempts if rel == "videos/generations")
        self.assertEqual(gen_payload["image"], "data:image/png;base64,abc")
        self.assertEqual(gen_payload["image_urls"], ["data:image/png;base64,abc"])

    def test_reference_resize_caps_long_edge(self) -> None:
        import cv2
        import numpy as np

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "big.png"
            cv2.imwrite(str(src), np.zeros((900, 1200, 3), dtype=np.uint8))
            out = _resized_png_bytes(src, max_edge=512)
            decoded = cv2.imdecode(
                np.frombuffer(out, dtype=np.uint8), cv2.IMREAD_UNCHANGED
            )
            self.assertIsNotNone(decoded)
            height, width = decoded.shape[:2]
            self.assertLessEqual(max(width, height), 512)

    def test_vendor_attempts_wan_and_hailuo(self) -> None:
        self.assertEqual(video_vendor_family("wan2.2-i2v-flash"), "wan")
        self.assertEqual(video_vendor_family("MiniMax-Hailuo-2.3"), "hailuo")
        wan = build_vendor_submit_attempts(
            api_base="https://api.apilio.ai/v1",
            model="wan2.2-i2v-flash",
            prompt="swim",
            duration=6,
            resolution="720p",
            reference_data_url="data:image/jpeg;base64,abc",
        )
        self.assertEqual(wan[0][0], "https://api.apilio.ai/v2/videos/generations")
        self.assertEqual(wan[0][1]["duration"], 5)
        self.assertEqual(wan[0][1]["resolution"], "720P")
        self.assertEqual(wan[0][1]["images"], ["data:image/jpeg;base64,abc"])
        hailuo = build_vendor_submit_attempts(
            api_base="https://api.apilio.ai/v1",
            model="MiniMax-Hailuo-02",
            prompt="swim",
            duration=6,
            resolution="720p",
            reference_data_url="data:image/jpeg;base64,abc",
        )
        self.assertEqual(hailuo[0][0], "https://api.apilio.ai/minimax/v1/video_generation")
        self.assertEqual(hailuo[0][1]["resolution"], "768P")
        self.assertEqual(hailuo[0][1]["first_frame_image"], "data:image/jpeg;base64,abc")

    def test_extract_task_and_url_shapes(self) -> None:
        self.assertEqual(extract_task_id({"id": "t1"}), "t1")
        self.assertEqual(extract_task_id({"data": {"task_id": "t2"}}), "t2")
        self.assertEqual(
            extract_video_url({"content": {"video_url": "https://cdn.example/a.mp4"}}),
            "https://cdn.example/a.mp4",
        )
        self.assertEqual(
            extract_video_url({"output": ["https://cdn.example/b.mp4"]}),
            "https://cdn.example/b.mp4",
        )
        self.assertEqual(
            extract_video_url({"data": "https://cdn.example/wan.mp4"}),
            "https://cdn.example/wan.mp4",
        )
        self.assertEqual(
            extract_video_url(
                {"file": {"download_url": "https://cdn.example/hailuo.mp4"}}
            ),
            "https://cdn.example/hailuo.mp4",
        )

    def test_probe_falls_through_then_downloads(self) -> None:
        mp4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 32
        calls: list[tuple[str, str]] = []

        def fake_post(_proxy, url, **_kwargs):
            calls.append(("POST", url))
            if url.endswith("/videos") and not url.rstrip("/").endswith("/generations"):
                return _FakeResp(404, text="not found")
            if url.endswith("/videos/generations"):
                return _FakeResp(200, {"id": "task-9", "status": "queued"})
            return _FakeResp(500, text="unexpected post")

        def fake_get(_proxy, url, **_kwargs):
            calls.append(("GET", url))
            if url.endswith("/videos/generations/task-9"):
                return _FakeResp(
                    200,
                    {
                        "id": "task-9",
                        "status": "succeeded",
                        "video_url": "https://cdn.example/out.mp4",
                    },
                )
            if url == "https://cdn.example/out.mp4":
                return _FakeResp(200, content=mp4)
            return _FakeResp(404, text="missing")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "clip.mp4"
            ref = Path(tmp) / "still.png"
            ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
            with patch("video_compat.http_post", side_effect=fake_post), patch(
                "video_compat.http_get", side_effect=fake_get
            ):
                result = generate_compat_video(
                    model="google/veo-3.1",
                    prompt="goldfish swimming",
                    output_path=out,
                    api_key="sk-test",
                    api_base="https://api.apilio.ai/v1",
                    reference_image=ref,
                    duration=6,
                    poll_interval=0.01,
                    timeout=2.0,
                )
            self.assertTrue(out.is_file())
            self.assertEqual(out.read_bytes(), mp4)
            self.assertEqual(result["endpoint"], "videos/generations")
            self.assertEqual(result["model"], "veo3.1")
            self.assertTrue(any(u.endswith("/videos") for _, u in calls if _ == "POST"))
            self.assertTrue(
                any(u.endswith("/videos/generations") for _, u in calls if _ == "POST")
            )

    def test_apilio_videos_completed_downloads_url(self) -> None:
        mp4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 32
        posted: list[dict] = []

        def fake_post(_proxy, url, **kwargs):
            posted.append(kwargs.get("json") or {})
            self.assertTrue(url.endswith("/videos"))
            return _FakeResp(200, {"id": "veo-1", "status": "queued"})

        def fake_get(_proxy, url, **_kwargs):
            if url.endswith("/videos/veo-1"):
                return _FakeResp(
                    200,
                    {
                        "id": "veo-1",
                        "status": "completed",
                        "video_url": "https://cdn.example/out.mp4",
                    },
                )
            if url == "https://cdn.example/out.mp4":
                return _FakeResp(200, content=mp4)
            return _FakeResp(404, text="missing")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "clip.mp4"
            ref = Path(tmp) / "still.png"
            ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
            with patch("video_compat.http_post", side_effect=fake_post), patch(
                "video_compat.http_get", side_effect=fake_get
            ):
                result = generate_compat_video(
                    model="google/veo-3.1",
                    prompt="goldfish swimming",
                    output_path=out,
                    api_key="sk-test",
                    api_base="https://api.apilio.ai/v1",
                    reference_image=ref,
                    duration=6,
                    poll_interval=0.01,
                    timeout=2.0,
                )
            self.assertEqual(result["endpoint"], "videos")
            self.assertEqual(result["model"], "veo3.1")
            self.assertTrue(out.is_file())
            self.assertEqual(posted[0]["ratio"], "1:1")
            self.assertIsInstance(posted[0]["input_reference"], str)
            self.assertTrue(posted[0]["input_reference"].startswith("data:image/"))

    def test_wan_vendor_path_submit_and_download(self) -> None:
        mp4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 32
        posted: list[str] = []

        def fake_post(_proxy, url, **_kwargs):
            posted.append(url)
            self.assertIn("/v2/videos/generations", url)
            return _FakeResp(200, {"task_id": "wan-1", "status": "PENDING"})

        def fake_get(_proxy, url, **_kwargs):
            if url.endswith("/v2/videos/generations/wan-1"):
                return _FakeResp(
                    200,
                    {
                        "task_id": "wan-1",
                        "status": "SUCCESS",
                        "data": "https://cdn.example/wan.mp4",
                    },
                )
            if url == "https://cdn.example/wan.mp4":
                return _FakeResp(200, content=mp4)
            return _FakeResp(404, text="missing")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "clip.mp4"
            ref = Path(tmp) / "still.png"
            ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
            with patch("video_compat.http_post", side_effect=fake_post), patch(
                "video_compat.http_get", side_effect=fake_get
            ):
                result = generate_compat_video(
                    model="wan2.2-i2v-flash",
                    prompt="swim",
                    output_path=out,
                    api_key="sk-test",
                    api_base="https://api.apilio.ai/v1",
                    reference_image=ref,
                    duration=6,
                    poll_interval=0.01,
                    timeout=2.0,
                )
            self.assertTrue(out.is_file())
            self.assertEqual(result["endpoint"], "https://api.apilio.ai/v2/videos/generations")
            self.assertTrue(posted[0].endswith("/v2/videos/generations"))

    def test_failed_task_does_not_leave_output(self) -> None:
        def fake_post(_proxy, url, **_kwargs):
            if url.endswith("/videos"):
                return _FakeResp(200, {"id": "bad-1", "status": "queued"})
            return _FakeResp(404, text="nope")

        def fake_get(_proxy, url, **_kwargs):
            return _FakeResp(200, {"id": "bad-1", "status": "failed", "error": "boom"})

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "clip.mp4"
            out.write_bytes(b"partial")
            with patch("video_compat.http_post", side_effect=fake_post), patch(
                "video_compat.http_get", side_effect=fake_get
            ):
                with self.assertRaises(CompatVideoError):
                    generate_compat_video(
                        model="hailuo",
                        prompt="swim",
                        output_path=out,
                        api_key="sk-test",
                        api_base="https://api.apilio.ai/v1",
                        poll_interval=0.01,
                        timeout=2.0,
                    )
            self.assertFalse(out.exists())

    def test_duration_seedance_vs_compat(self) -> None:
        with self.assertRaises(ValueError):
            resolve_video_generate_settings({"video": {"duration": 6}}, duration=3)
        six = resolve_video_generate_settings(
            {"video": {"duration": 6}}, backend="openai_compat", duration=6
        )
        self.assertEqual(six["duration"], 6)
        three = resolve_video_generate_settings(
            {"video": {}}, backend="openai_compat", duration=3
        )
        self.assertEqual(three["duration"], 3)
        with self.assertRaises(ValueError):
            resolve_video_generate_settings({"video": {}}, backend="openai_compat", duration=40)

    def test_generate_cmd_missing_key_mentions_provider(self) -> None:
        runner = CliRunner()
        with patch("video_cmds._load_config", return_value={"video": {}}):
            result = runner.invoke(
                generate_cmd,
                ["--prompt", "swim", "--output", "out.mp4", "--duration", "6"],
            )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Provider", result.output)


if __name__ == "__main__":
    unittest.main()
