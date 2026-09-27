"""Minimal proof: detached job + file status polling works for external agents."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from async_job import (
    job_public_view,
    refresh_job,
    start_detached_job,
    wait_for_job,
)


class AsyncJobPollTests(unittest.TestCase):
    def test_detach_then_poll_until_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_dir = root / "jobs"
            marker = root / "marker.txt"
            argv = [
                sys.executable,
                "-c",
                (
                    "import pathlib,time;"
                    f"p=pathlib.Path(r'{marker}');"
                    "time.sleep(0.4);"
                    "p.write_text('ok',encoding='utf-8')"
                ),
            ]
            job = start_detached_job(argv, cwd=root, jobs_dir=jobs_dir)
            self.assertEqual(job["status"], "running")
            self.assertTrue(job.get("job_id"))
            view = job_public_view(job)
            self.assertEqual(view["next_action"], "poll")
            self.assertEqual(view["status"], "running")

            finished = wait_for_job(
                jobs_dir,
                str(job["job_id"]),
                timeout_sec=30.0,
                poll_sec=0.15,
            )
            refreshed = refresh_job(jobs_dir, str(job["job_id"]))
            self.assertEqual(refreshed["status"], "done")
            self.assertEqual(refreshed.get("exit_code"), 0)
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.read_text(encoding="utf-8"), "ok")
            final_view = job_public_view(finished)
            self.assertEqual(final_view["status"], "done")
            # External agent would stop polling when next_action != poll
            self.assertNotEqual(final_view["next_action"], "poll")

    def test_failed_job_reports_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_dir = root / "jobs"
            argv = [sys.executable, "-c", "raise SystemExit(3)"]
            job = start_detached_job(argv, cwd=root, jobs_dir=jobs_dir)
            finished = wait_for_job(
                jobs_dir,
                str(job["job_id"]),
                timeout_sec=30.0,
                poll_sec=0.15,
            )
            self.assertEqual(finished["status"], "failed")
            self.assertEqual(finished.get("exit_code"), 3)
            view = job_public_view(finished)
            self.assertFalse(view["ok"])
            self.assertEqual(view["status"], "failed")
            job_file = Path(finished["job_file"])
            disk = json.loads(job_file.read_text(encoding="utf-8"))
            self.assertEqual(disk["exit_code"], 3)


if __name__ == "__main__":
    unittest.main()
