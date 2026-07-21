"""Smoke: loopback permission bridge + mutating FOUNDRY_TOOL gate.

Starts a tiny HTTP server (same contract as Electron), runs two mutate
attempts (deny then approve), asserts subprocess behavior.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from pi_foundry_tools import run_allowed_gamefactory
from tool_permission import ENV_TOKEN, ENV_URL


def main() -> None:
    decisions = ["deny", "once"]
    seen: list[dict] = []
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw or "{}")
            with lock:
                seen.append(payload)
                decision = decisions.pop(0) if decisions else "deny"
            body = json.dumps({"decision": decision}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    token = "smoke-token"
    env = {
        ENV_URL: f"http://127.0.0.1:{port}/tool-permission",
        ENV_TOKEN: token,
    }

    class FakeProc:
        returncode = 0
        stdout = '{"ok": true}'
        stderr = ""

    try:
        with patch.dict("os.environ", env, clear=False):
            # Auth header is checked by Electron; Python client sends it —
            # this smoke server ignores auth (contract shape only).
            denied = run_allowed_gamefactory(
                ["setup", "install", "ffmpeg", "--json", "--i-confirm"],
                permission_session_id="smoke-sess",
            )
            assert denied.get("ok") is False, denied
            assert "denied" in str(denied.get("error") or "").lower(), denied

            with patch("pi_foundry_tools.subprocess.run", return_value=FakeProc()):
                with patch("pi_foundry_tools.Path.is_file", return_value=True):
                    allowed = run_allowed_gamefactory(
                        ["setup", "install", "ffmpeg", "--json"],
                        permission_session_id="smoke-sess",
                    )
            assert allowed.get("ok") is True, allowed

        assert len(seen) == 2, seen
        assert "ffmpeg" in seen[0].get("argv_summary", "")
        print("ok: tool-permission bridge smoke (deny then approve)")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
