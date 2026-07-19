"""Deterministic pipeline runner — subprocess DAG execution without Hermes."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roles import PROMPT_CRAFTER_ROLE, GODOT_DEVELOPER_ROLE

from assets_manifest import refresh_assets_manifest_from_pipeline
from pipeline_manifest import (
    TASK_DONE,
    TASK_FAILED,
    TASK_PENDING,
    TASK_RUNNING,
    TASK_SKIPPED,
    _CLI_DIR,
    _artifact_exists,
    load_manifest,
    ready_tasks,
    reconcile_manifest,
    record_task,
    save_manifest,
    status_summary,
    task_by_id,
    tasks_list,
)

EXIT_VALIDATE_FAIL = 2
EXIT_TIMEOUT = 124

DEFAULT_NETWORK_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SEC = 2.0

# Substrings matched against stdout+stderr (case-insensitive) for retryable network errors.
_NETWORK_ERROR_MARKERS = (
    "connection error",
    "connection refused",
    "connection reset",
    "connection aborted",
    "connectionerror",
    "connecttimeout",
    "read timeout",
    "read timed out",
    "timed out",
    "timeout",
    "proxyerror",
    "proxy error",
    "tunnel connection failed",
    "max retries exceeded",
    "failed to establish a new connection",
    "name or service not known",
    "name resolution",
    "getaddrinfo",
    "nodename nor servname",
    "network is unreachable",
    "temporary failure in name resolution",
    "sslerror",
    "ssl:",
    "broken pipe",
    "remote end closed",
    "remote disconnected",
    "server disconnected",
    "chunkedencodingerror",
    "http 429",
    "http 502",
    "http 503",
    "http 504",
    "status code 429",
    "status code 502",
    "status code 503",
    "status code 504",
    "rate limit",
    "ratelimit",
    "too many requests",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "temporarily unavailable",
    "try again later",
)


@dataclass
class TaskRunOutcome:
    task_id: str
    exit_code: int
    status: str
    result: dict[str, Any]
    should_pause: bool = False
    pause_reason: str | None = None


@dataclass
class PipelineRunResult:
    complete: bool = False
    paused: bool = False
    blocked: bool = False
    message: str = ""
    last_outcome: TaskRunOutcome | None = None
    summary: dict[str, Any] = field(default_factory=dict)


def cli_workdir() -> Path:
    return _CLI_DIR


def extract_json_from_stdout(stdout: str) -> dict[str, Any] | None:
    """Parse first JSON object from command stdout (pretty-printed or one-line)."""
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(text[start:])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def is_retryable_network_failure(
    exit_code: int,
    stdout: str = "",
    stderr: str = "",
) -> bool:
    """True for transient network/API failures — not validation (exit 2) or logic errors."""
    if exit_code == 0:
        return False
    if exit_code == EXIT_VALIDATE_FAIL:
        return False
    if exit_code == EXIT_TIMEOUT:
        return True
    blob = f"{stdout}\n{stderr}".lower()
    return any(marker in blob for marker in _NETWORK_ERROR_MARKERS)


def outcome_from_process(
    task_id: str,
    *,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> TaskRunOutcome:
    parsed = extract_json_from_stdout(stdout)
    tail_line = ""
    for line in reversed(stdout.strip().splitlines()):
        if line.strip():
            tail_line = line.strip()
            break

    result: dict[str, Any] = {
        "exit_code": exit_code,
        "stdout_tail": tail_line,
    }
    if parsed is not None:
        result["parsed"] = parsed
    if stderr.strip():
        result["stderr"] = stderr.strip()[-2000:]
    if exit_code != 0 and stdout.strip():
        result["stdout"] = stdout.strip()[-2000:]

    if exit_code == 0:
        return TaskRunOutcome(
            task_id=task_id,
            exit_code=0,
            status=TASK_DONE,
            result=result,
        )

    if exit_code == EXIT_VALIDATE_FAIL:
        next_action = (parsed or {}).get("next_action")
        return TaskRunOutcome(
            task_id=task_id,
            exit_code=exit_code,
            status=TASK_FAILED,
            result=result,
            should_pause=True,
            pause_reason=(
                f"Validation failed for {task_id}"
                + (f" (next_action={next_action})" if next_action else "")
                + " — rerun prompt.craft or fix plan, then reset task to pending."
            ),
        )

    return TaskRunOutcome(
        task_id=task_id,
        exit_code=exit_code,
        status=TASK_FAILED,
        result=result,
        should_pause=True,
        pause_reason=f"Command failed for {task_id} (exit {exit_code})",
    )


def _run_task_once(
    task: dict[str, Any],
    *,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> TaskRunOutcome:
    task_id = str(task["id"])
    command = str(task.get("command") or "")
    workdir = cwd or cli_workdir()
    try:
        proc = subprocess.run(
            command,
            cwd=str(workdir),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return TaskRunOutcome(
            task_id=task_id,
            exit_code=EXIT_TIMEOUT,
            status=TASK_FAILED,
            result={
                "exit_code": EXIT_TIMEOUT,
                "error": "timeout",
                "stdout": stdout[-2000:],
                "stderr": stderr[-2000:],
            },
            should_pause=True,
            pause_reason=f"Timeout running {task_id}",
        )

    return outcome_from_process(
        task_id,
        exit_code=int(proc.returncode),
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def run_task_subprocess(
    task: dict[str, Any],
    *,
    cwd: Path | None = None,
    timeout: float | None = None,
    dry_run: bool = False,
    retries: int = DEFAULT_NETWORK_RETRIES,
    retry_backoff: float = DEFAULT_RETRY_BACKOFF_SEC,
    on_retry: Any | None = None,
) -> TaskRunOutcome:
    """Run one task; retry on network/timeout failures (not validation exit 2).

    ``retries`` = extra attempts after the first failure (default 3 → up to 4 tries).
    """
    task_id = str(task["id"])
    command = str(task.get("command") or "")
    if not command:
        return TaskRunOutcome(
            task_id=task_id,
            exit_code=1,
            status=TASK_FAILED,
            result={"error": "empty command"},
            should_pause=True,
            pause_reason=f"Task {task_id} has no command",
        )

    if dry_run:
        return TaskRunOutcome(
            task_id=task_id,
            exit_code=0,
            status=TASK_DONE,
            result={"dry_run": True, "command": command},
        )

    attempts_log: list[dict[str, Any]] = []
    total_attempts = max(1, int(retries) + 1)
    last: TaskRunOutcome | None = None

    for attempt in range(1, total_attempts + 1):
        last = _run_task_once(task, cwd=cwd, timeout=timeout)
        if last.status == TASK_DONE:
            if attempts_log:
                last.result["network_retries"] = attempts_log
                last.result["attempts"] = attempt
            return last

        stderr = str((last.result or {}).get("stderr") or "")
        stdout = str(
            (last.result or {}).get("stdout")
            or (last.result or {}).get("stdout_tail")
            or ""
        )
        retryable = is_retryable_network_failure(last.exit_code, stdout, stderr)
        if not retryable or attempt >= total_attempts:
            if attempts_log:
                last.result["network_retries"] = attempts_log
                last.result["attempts"] = attempt
            return last

        wait_s = float(retry_backoff) * (2 ** (attempt - 1))
        attempts_log.append(
            {
                "attempt": attempt,
                "exit_code": last.exit_code,
                "wait_seconds": wait_s,
                "stderr_tail": stderr[-400:] if stderr else "",
            }
        )
        if on_retry:
            on_retry(task_id, attempt, int(retries), wait_s, last)
        time.sleep(wait_s)

    assert last is not None
    return last


def _auto_skip_role_tasks(manifest: dict[str, Any], skip_roles: set[str]) -> list[str]:
    """Mark skipped-role tasks done/skipped when artifacts exist or role is AI-only."""
    skipped: list[str] = []
    for task in tasks_list(manifest):
        if task.get("status") != TASK_PENDING:
            continue
        role = task.get("role")
        if role not in skip_roles:
            continue

        artifacts = task.get("artifacts") or {}
        plan_rel = artifacts.get("plan") or artifacts.get("dev_handoff")
        if plan_rel and _artifact_exists(_CLI_DIR, plan_rel):
            record_task(
                manifest,
                task["id"],
                status=TASK_DONE,
                result={"source": "auto_skip", "reason": "handoff artifact exists"},
            )
            skipped.append(task["id"])
            continue

        if role == GODOT_DEVELOPER_ROLE:
            record_task(
                manifest,
                task["id"],
                status=TASK_SKIPPED,
                result={
                    "source": "skip_role",
                    "reason": "Pass 4 — delegate to codex/cursor (use --run-game-dev for dev-context only)",
                },
            )
            skipped.append(task["id"])
    return skipped


def _missing_handoffs_for_skipped_roles(manifest: dict[str, Any], skip_roles: set[str]) -> list[str]:
    missing: list[str] = []
    for task in tasks_list(manifest):
        if task.get("status") != TASK_PENDING:
            continue
        role = task.get("role")
        if role not in skip_roles:
            continue
        if role == GODOT_DEVELOPER_ROLE:
            continue
        plan_rel = (task.get("artifacts") or {}).get("plan")
        if plan_rel and not _artifact_exists(_CLI_DIR, plan_rel):
            missing.append(task["id"])
    return missing


def _auto_skip_prompt_tasks(manifest: dict[str, Any], skip_roles: set[str]) -> list[str]:
    """Backward-compatible alias."""
    return _auto_skip_role_tasks(manifest, skip_roles)


def _missing_plans_for_skipped_roles(manifest: dict[str, Any], skip_roles: set[str]) -> list[str]:
    return _missing_handoffs_for_skipped_roles(manifest, skip_roles)


def run_pipeline(
    manifest_path: Path,
    *,
    jobs: int = 4,
    skip_roles: set[str] | None = None,
    run_prompts: bool = False,
    run_game_dev: bool = False,
    stop_on_fail: bool = True,
    task_timeout: float | None = 1800.0,
    dry_run: bool = False,
    network_retries: int = DEFAULT_NETWORK_RETRIES,
    retry_backoff: float = DEFAULT_RETRY_BACKOFF_SEC,
    on_task_start: Any | None = None,
    on_task_finish: Any | None = None,
    on_task_retry: Any | None = None,
) -> PipelineRunResult:
    """Execute ready manifest tasks in parallel waves until done, paused, or blocked."""
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if network_retries < 0:
        raise ValueError("network_retries must be >= 0")
    if retry_backoff < 0:
        raise ValueError("retry_backoff must be >= 0")

    skip = set(skip_roles or [])
    if not run_prompts and PROMPT_CRAFTER_ROLE not in skip:
        skip.add(PROMPT_CRAFTER_ROLE)
    if not run_game_dev and GODOT_DEVELOPER_ROLE not in skip:
        skip.add(GODOT_DEVELOPER_ROLE)

    manifest_path = manifest_path.resolve()
    lock = threading.Lock()

    def persist(*, sync_assets: bool = True) -> None:
        save_manifest(manifest_path, manifest)
        if sync_assets:
            refresh_assets_manifest_from_pipeline(manifest)

    manifest = load_manifest(manifest_path)

    # User may have deleted unsatisfactory outputs — re-queue those tasks first.
    synced = reconcile_manifest(manifest)
    if synced["total"] and not dry_run:
        persist()

    if skip:
        _auto_skip_role_tasks(manifest, skip)
        missing = _missing_handoffs_for_skipped_roles(manifest, skip)
        if missing:
            return PipelineRunResult(
                blocked=True,
                message=(
                    "Missing plan files for skipped prompt tasks: "
                    + ", ".join(missing)
                    + ". Run prompt craft first or use --run-prompts."
                ),
                summary=status_summary(manifest),
            )
        if not dry_run:
            persist()

    while True:
        with lock:
            manifest = load_manifest(manifest_path)
            summary = status_summary(manifest)
            if summary["done"]:
                return PipelineRunResult(
                    complete=True,
                    message="All tasks done.",
                    summary=summary,
                )
            if summary["failed_ids"] and stop_on_fail:
                return PipelineRunResult(
                    paused=True,
                    message=f"Pipeline has failed tasks: {', '.join(summary['failed_ids'])}",
                    summary=summary,
                )

            ready = ready_tasks(manifest)
            ready = [t for t in ready if t.get("role") not in skip]

        if not ready:
            with lock:
                manifest = load_manifest(manifest_path)
                summary = status_summary(manifest)
            pending = summary["counts"].get(TASK_PENDING, 0)
            if pending:
                return PipelineRunResult(
                    blocked=True,
                    message="No ready tasks but pipeline incomplete (check failed/blocked deps).",
                    summary=summary,
                )
            return PipelineRunResult(complete=True, message="Nothing left to run.", summary=summary)

        if dry_run:
            for task in ready:
                if on_task_start:
                    on_task_start(task)
                outcome = run_task_subprocess(task, dry_run=True)
                if on_task_finish:
                    on_task_finish(outcome)
            return PipelineRunResult(
                complete=False,
                message=f"Dry run: would execute {len(ready)} task(s).",
                summary=status_summary(load_manifest(manifest_path)),
            )

        pause_outcome: TaskRunOutcome | None = None

        def execute_one(task: dict[str, Any]) -> TaskRunOutcome:
            nonlocal manifest
            tid = task["id"]
            with lock:
                manifest = load_manifest(manifest_path)
                record_task(manifest, tid, status=TASK_RUNNING)
                persist()
            if on_task_start:
                on_task_start(task)
            outcome = run_task_subprocess(
                task,
                timeout=task_timeout,
                retries=network_retries,
                retry_backoff=retry_backoff,
                on_retry=on_task_retry,
            )
            with lock:
                manifest = load_manifest(manifest_path)
                record_task(manifest, tid, status=outcome.status, result=outcome.result)
                persist()
            if on_task_finish:
                on_task_finish(outcome)
            return outcome

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(execute_one, task): task for task in ready}
            for future in as_completed(futures):
                outcome = future.result()
                if stop_on_fail and outcome.should_pause:
                    pause_outcome = outcome
                    for f in futures:
                        f.cancel()
                    break

        if pause_outcome is not None:
            with lock:
                summary = status_summary(load_manifest(manifest_path))
            return PipelineRunResult(
                paused=True,
                message=pause_outcome.pause_reason or "Pipeline paused on failure.",
                last_outcome=pause_outcome,
                summary=summary,
            )


def reset_task(manifest: dict[str, Any], task_id: str) -> None:
    """Set a task back to pending (e.g. after prompt fix)."""
    task = task_by_id(manifest, task_id)
    task["status"] = TASK_PENDING
    task["result"] = None
    task["started_at"] = None
    task["finished_at"] = None


def reset_task_cascade(manifest: dict[str, Any], task_id: str) -> list[str]:
    """Reset task and any downstream tasks that depend on it (transitively)."""
    reset: list[str] = []
    by_id = {t["id"]: t for t in tasks_list(manifest)}

    def dependents_of(tid: str) -> list[str]:
        return [t["id"] for t in tasks_list(manifest) if tid in (t.get("depends_on") or [])]

    stack = [task_id]
    seen: set[str] = set()
    while stack:
        tid = stack.pop()
        if tid in seen:
            continue
        seen.add(tid)
        if tid in by_id:
            reset_task(manifest, tid)
            reset.append(tid)
        for dep in dependents_of(tid):
            stack.append(dep)
    refresh_assets_manifest_from_pipeline(manifest, invalidated_task_ids=reset)
    return reset
