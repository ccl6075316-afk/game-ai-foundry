"""Tests for image API JSON parse diagnostics / retry classification."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from gamefactory import _is_retryable_image_api_error, _parse_api_json_response


class ApiJsonResponseTests(unittest.TestCase):
    def test_parse_valid_json(self) -> None:
        resp = MagicMock()
        resp.content = b'{"ok": true}'
        resp.text = '{"ok": true}'
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"ok": True}
        self.assertEqual(_parse_api_json_response(resp, kind="API"), {"ok": True})

    def test_parse_invalid_json_includes_preview(self) -> None:
        resp = MagicMock()
        resp.content = b"<html>proxy</html>"
        resp.text = "<html>proxy</html>"
        resp.status_code = 200
        resp.headers = {"Content-Type": "text/html"}
        resp.json.side_effect = __import__("json").JSONDecodeError("Expecting value", "x", 0)
        with self.assertRaises(RuntimeError) as ctx:
            _parse_api_json_response(resp, kind="API")
        msg = str(ctx.exception)
        self.assertIn("Invalid JSON in API response", msg)
        self.assertIn("HTML", msg)
        self.assertIn("<html>", msg)

    def test_retryable_markers(self) -> None:
        self.assertTrue(_is_retryable_image_api_error(RuntimeError("Invalid JSON in API response")))
        self.assertTrue(_is_retryable_image_api_error(RuntimeError("HTTP 503 boom")))
        self.assertTrue(_is_retryable_image_api_error(RuntimeError("HTTP 429 rate limit")))
        self.assertTrue(_is_retryable_image_api_error(RuntimeError("connection reset by peer")))
        self.assertTrue(
            _is_retryable_image_api_error(
                RuntimeError(
                    "Images API request failed: "
                    "[WinError 10054] An existing connection was forcibly closed by the remote host"
                )
            )
        )
        self.assertTrue(
            _is_retryable_image_api_error(
                RuntimeError(
                    "Images API request failed: "
                    "No connection could be made because the target machine actively refused it"
                )
            )
        )
        self.assertTrue(
            _is_retryable_image_api_error(
                RuntimeError(
                    "Images API request failed: "
                    "HTTPSConnectionPool(host='x', port=443): Max retries exceeded with url: /v1 "
                    "(Caused by NewConnectionError("
                    "'Failed to establish a new connection: [WinError 10060]'))"
                )
            )
        )
        self.assertFalse(_is_retryable_image_api_error(RuntimeError("Could not extract image")))
        self.assertFalse(_is_retryable_image_api_error(RuntimeError("bad connection string in prompt")))


if __name__ == "__main__":
    unittest.main()
