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

    def test_criteria_prefers_scenes_systems_over_long_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.json"
            brief.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "Fish",
                            "description": "X" * 500,
                            "art_direction": "pixel",
                            "dimension": "2d",
                            "genre": "sim",
                            "gameplay_loop": "cast",
                            "session_goal": "endless",
                            "player_asset": "rod",
                            "controls": {"cast": ["Space"]},
                            "viewport": {"width": 1280, "height": 720},
                            "scenes": [
                                {"id": "dock", "title": "钓场", "summary": "Cast and fight."}
                            ],
                            "systems": [
                                {"id": "economy", "title": "经济", "summary": "Tickets."}
                            ],
                        },
                        "assets": [
                            {
                                "name": "rod",
                                "id": "rod",
                                "type": "character",
                                "usage": "player_idle",
                                "usage_description": "rod",
                                "display_size": {"width": 64, "height": 64},
                                "description": "rod",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            criteria = criteria_from_brief(brief)
            sources = {c["source"] for c in criteria}
            self.assertIn("brief.project.scenes[dock]", sources)
            self.assertIn("brief.project.systems[economy]", sources)
            desc = next(c for c in criteria if c["source"] == "brief.project.description")
            self.assertTrue(desc["criterion"].startswith("Product overview:"))
            self.assertLessEqual(len(desc["criterion"]), 320)

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
