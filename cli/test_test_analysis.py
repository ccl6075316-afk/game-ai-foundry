"""Tests for tester role — criteria, reports, vision JSON parsing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from test_analysis import (
    _extract_json_object,
    build_validation_report,
    criteria_from_brief,
)

_REPO = Path(__file__).resolve().parent.parent
_EXAMPLE_BRIEF = _REPO / "resources" / "asset-brief.example.json"


class TestAnalysisTests(unittest.TestCase):
    def test_criteria_from_brief(self) -> None:
        criteria = criteria_from_brief(_EXAMPLE_BRIEF)
        self.assertTrue(len(criteria) >= 2)
        sources = {c["source"] for c in criteria}
        self.assertIn("brief.project.gameplay_loop", sources)

    def test_extract_json_object_from_fenced_text(self) -> None:
        text = 'Here is the result:\n```json\n{"status": "passed", "summary": "ok"}\n```'
        obj = _extract_json_object(text)
        self.assertEqual(obj["status"], "passed")

    def test_build_validation_report_build_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "game"
            project.mkdir()
            report = build_validation_report(
                brief_path=_EXAMPLE_BRIEF,
                project_path=project,
                screenshot_path=None,
                build_ok=False,
                build_error="dotnet build failed",
                analysis=None,
                criteria=[{"source": "x", "criterion": "y"}],
            )
            vr = report["validation_report"]
            self.assertEqual(vr["status"], "failed")
            self.assertFalse(vr["layers"]["build"]["ok"])
            self.assertEqual(len(vr["failed_criteria"]), 1)

    @patch("test_analysis.http_post")
    def test_analyze_screenshot_mock(self, mock_post: MagicMock) -> None:
        from PIL import Image

        from test_analysis import analyze_screenshot

        with tempfile.TemporaryDirectory() as tmp:
            img_path = Path(tmp) / "shot.png"
            Image.new("RGB", (64, 64), color=(100, 150, 200)).save(img_path)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "status": "passed",
                                    "summary": "Looks fine",
                                    "failed_criteria": [],
                                }
                            )
                        }
                    }
                ]
            }
            mock_post.return_value = mock_resp

            config = {
                "host": {"api_key": "test-key", "api_base": "https://openrouter.ai/api/v1"},
            }
            result = analyze_screenshot(
                img_path,
                [{"source": "t", "criterion": "visible player"}],
                config=config,
            )
            self.assertEqual(result["status"], "passed")
            mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
