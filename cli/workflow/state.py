"""Read-only manifest classification and consistency checks."""

from __future__ import annotations

from typing import Any

from pipeline_manifest import ready_tasks, status_summary, tasks_list
from workflow.contract import make_failure

VALID_TASK_STATUSES = {
    "pending",
    "running",
    "done",
    "failed",
    "skipped",
    "paused",
    "blocked",
}


def summarize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = status_summary(manifest)
    summary["ready_ids"] = [task["id"] for task in ready_tasks(manifest)]
    summary["ready_count"] = len(summary["ready_ids"])
    return summary


def classify_manifest_state(summary: dict[str, Any]) -> tuple[str, str]:
    counts = summary.get("counts") or {}
    if summary.get("failed_ids"):
        return "failed", "resume"
    if counts.get("blocked"):
        return "blocked", "fix_input"
    if counts.get("paused"):
        return "paused", "resume"
    if summary.get("done"):
        return "done", "human_review"
    if counts.get("running"):
        return "running", "run"
    if summary.get("ready_count"):
        return "pending", "run"
    return "paused", "resume"


def classify_runner_state(
    summary: dict[str, Any],
    result: dict[str, Any],
) -> tuple[str, str]:
    if result.get("blocked"):
        return "blocked", "fix_input"
    if result.get("paused"):
        return "paused", "resume"
    status, next_action = classify_manifest_state(summary)
    if not result.get("ok") and status in {"pending", "running"}:
        return "blocked", "fix_input"
    return status, next_action


def manifest_failures(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        make_failure(
            "task_failed",
            f"task failed: {task_id}",
            task_id=task_id,
        )
        for task_id in summary.get("failed_ids") or []
    ]


def manifest_validation_errors(manifest: dict[str, Any]) -> list[str]:
    try:
        tasks = tasks_list(manifest)
    except (TypeError, ValueError) as exc:
        return [str(exc)]

    errors: list[str] = []
    task_ids: set[str] = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"tasks[{index}] must be an object")
            continue
        task_id = str(task.get("id") or "").strip()
        if not task_id:
            errors.append(f"tasks[{index}] missing id")
        elif task_id in task_ids:
            errors.append(f"duplicate task id: {task_id}")
        else:
            task_ids.add(task_id)
        task_status = str(task.get("status") or "pending")
        if task_status not in VALID_TASK_STATUSES:
            errors.append(f"task {task_id or index}: invalid status {task_status}")

    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id") or "")
        dependencies = task.get("depends_on") or []
        if not isinstance(dependencies, list):
            errors.append(f"task {task_id}: depends_on must be a list")
            continue
        for dependency in dependencies:
            dependency_id = str(dependency)
            if dependency_id == task_id:
                errors.append(f"task {task_id}: self dependency")
            elif dependency_id not in task_ids:
                errors.append(f"task {task_id}: unknown dependency {dependency_id}")
    return errors
