"""File-backed detached jobs for external-agent polling.

Protocol (agent-agnostic):
1. Start returns immediately with ``job_id`` and ``next_action=poll``.
2. Poll ``job status --job-id`` until ``status`` is ``done`` or ``failed``.
3. Truth lives in ``<jobs_dir>/<job_id>.json`` (not in chat memory).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JOB_SCHEMA_VERSION = 1
TERMINAL = frozenset({"done", "failed"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def jobs_dir_for_manifest(manifest_path: Path) -> Path:
    """Default job store next to the pipeline manifest."""
    return Path(manifest_path).resolve().parent / "jobs"


def job_path(jobs_dir: Path, job_id: str) -> Path:
    return Path(jobs_dir) / f"{job_id}.json"


def log_path(jobs_dir: Path, job_id: str) -> Path:
    return Path(jobs_dir) / f"{job_id}.log"


def load_job(jobs_dir: Path, job_id: str) -> dict[str, Any]:
    path = job_path(jobs_dir, job_id)
    if not path.is_file():
        raise FileNotFoundError(f"job not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"job file is not an object: {path}")
    return data


def save_job(jobs_dir: Path, job: dict[str, Any]) -> Path:
    jobs_dir = Path(jobs_dir)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(job["job_id"])
    path = job_path(jobs_dir, job_id)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
                PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid)
            )
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                ok = ctypes.windll.kernel32.GetExitCodeProcess(  # type: ignore[attr-defined]
                    handle, ctypes.byref(exit_code)
                )
                if not ok:
                    return False
                return int(exit_code.value) == STILL_ACTIVE
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        else:
            os.kill(int(pid), 0)
            return True
    except OSError:
        return False


def refresh_job(jobs_dir: Path, job_id: str) -> dict[str, Any]:
    """Recompute running/done from pid + exit_code fields; persist if changed."""
    job = load_job(jobs_dir, job_id)
    status = str(job.get("status") or "")
    if status in TERMINAL:
        return job

    pid = job.get("pid")
    alive = _pid_alive(int(pid) if pid is not None else None)
    exit_code = job.get("exit_code")

    changed = False
    if exit_code is not None:
        new_status = "done" if int(exit_code) == 0 else "failed"
        if status != new_status:
            job["status"] = new_status
            job["finished_at"] = job.get("finished_at") or _utc_now()
            changed = True
    elif not alive and status == "running":
        # Worker crashed without writing exit_code.
        job["status"] = "failed"
        job["exit_code"] = job.get("exit_code")
        if job.get("exit_code") is None:
            job["exit_code"] = 1
        job["finished_at"] = _utc_now()
        job["error"] = job.get("error") or "process ended without exit_code"
        changed = True

    if changed:
        save_job(jobs_dir, job)
    return job


def job_public_view(job: dict[str, Any]) -> dict[str, Any]:
    status = str(job.get("status") or "pending")
    if status == "running":
        next_action = "poll"
    elif status == "failed":
        next_action = "resume"
    elif status == "done":
        next_action = "human_review"
    else:
        next_action = "poll"
    return {
        "schema_version": JOB_SCHEMA_VERSION,
        "ok": status != "failed",
        "command": "job status",
        "stage": "assets",
        "status": status,
        "next_action": next_action,
        "inputs": {"job_id": job.get("job_id"), "jobs_dir": job.get("jobs_dir")},
        "outputs": [p for p in [job.get("job_file"), job.get("log_file")] if p],
        "summary": {
            "job_id": job.get("job_id"),
            "pid": job.get("pid"),
            "exit_code": job.get("exit_code"),
            "argv": job.get("argv"),
            "cwd": job.get("cwd"),
            "error": job.get("error"),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
        },
        "failures": (
            [
                {
                    "code": "job_failed",
                    "kind": "unknown",
                    "message": str(job.get("error") or f"job exit_code={job.get('exit_code')}"),
                    "task_id": job.get("job_id"),
                }
            ]
            if status == "failed"
            else []
        ),
    }


def start_detached_job(
    argv: list[str],
    *,
    cwd: Path,
    jobs_dir: Path,
    env: dict[str, str] | None = None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    """Spawn a worker that runs ``argv`` and updates the job file when finished."""
    if not argv:
        raise ValueError("argv must be non-empty")
    jobs_dir = Path(jobs_dir)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex[:12]
    py = python_executable or sys.executable
    job: dict[str, Any] = {
        "schema_version": JOB_SCHEMA_VERSION,
        "job_id": job_id,
        "status": "pending",
        "argv": list(argv),
        "cwd": str(Path(cwd).resolve()),
        "jobs_dir": str(jobs_dir.resolve()),
        "job_file": str(job_path(jobs_dir, job_id)),
        "log_file": str(log_path(jobs_dir, job_id)),
        "pid": None,
        "exit_code": None,
        "started_at": None,
        "finished_at": None,
        "error": None,
    }
    save_job(jobs_dir, job)

    worker_argv = [
        py,
        str(Path(__file__).resolve()),
        "--worker",
        "--job-file",
        str(job_path(jobs_dir, job_id)),
    ]
    popen_env = {**os.environ, **(env or {})}
    popen_env["PYTHONIOENCODING"] = "utf-8"
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    log_handle = open(log_path(jobs_dir, job_id), "a", encoding="utf-8")  # noqa: SIM115
    try:
        proc = subprocess.Popen(
            worker_argv,
            cwd=str(Path(cwd).resolve()),
            env=popen_env,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            close_fds=(os.name != "nt"),
        )
    finally:
        # Child inherits the handle; parent can close its copy.
        log_handle.close()

    job["status"] = "running"
    job["pid"] = proc.pid
    job["worker_pid"] = proc.pid
    job["started_at"] = _utc_now()
    save_job(jobs_dir, job)
    return job


def run_worker(job_file: Path) -> int:
    """Child process entry: execute argv and persist exit_code."""
    job_file = Path(job_file)
    job = json.loads(job_file.read_text(encoding="utf-8"))
    jobs_dir = Path(job["jobs_dir"])
    argv = list(job.get("argv") or [])
    cwd = Path(job.get("cwd") or ".")
    job["status"] = "running"
    job["pid"] = os.getpid()
    job["started_at"] = job.get("started_at") or _utc_now()
    save_job(jobs_dir, job)

    log_file = Path(job.get("log_file") or log_path(jobs_dir, str(job["job_id"])))
    exit_code = 1
    try:
        with log_file.open("a", encoding="utf-8") as log:
            log.write(f"\n--- worker start { _utc_now() } pid={os.getpid()} ---\n")
            log.write("argv: " + json.dumps(argv, ensure_ascii=False) + "\n")
            log.flush()
            completed = subprocess.run(
                argv,
                cwd=str(cwd),
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
            exit_code = int(completed.returncode)
            log.write(f"\n--- worker end exit={exit_code} ---\n")
    except (OSError, ValueError) as exc:
        job["error"] = str(exc)
        exit_code = 1
    job["exit_code"] = exit_code
    job["status"] = "done" if exit_code == 0 else "failed"
    job["finished_at"] = _utc_now()
    job["pid"] = os.getpid()
    save_job(jobs_dir, job)
    return exit_code


def wait_for_job(
    jobs_dir: Path,
    job_id: str,
    *,
    timeout_sec: float = 60.0,
    poll_sec: float = 0.2,
) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        job = refresh_job(jobs_dir, job_id)
        if str(job.get("status")) in TERMINAL:
            return job
        time.sleep(poll_sec)
    job = refresh_job(jobs_dir, job_id)
    if str(job.get("status")) not in TERMINAL:
        job["error"] = job.get("error") or f"wait timed out after {timeout_sec}s"
    return job


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--worker"]:
        # --worker --job-file PATH
        if len(args) >= 3 and args[1] == "--job-file":
            return run_worker(Path(args[2]))
        print("usage: async_job.py --worker --job-file PATH", file=sys.stderr)
        return 2
    print("async_job is a library; use pipeline job CLI", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
