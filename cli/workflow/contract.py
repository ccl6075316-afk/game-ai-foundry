"""Stable enums and JSON response helpers for workflow commands."""

from __future__ import annotations

import json
from typing import Any

import click

SCHEMA_VERSION = 1

STATUSES = frozenset(
    {"pending", "running", "done", "paused", "blocked", "failed"}
)
STAGES = frozenset(
    {"design", "production", "assets", "assemble", "implement", "validate"}
)
NEXT_ACTIONS = frozenset(
    {
        "none",
        "freeze_brief",
        "derive_production",
        "run",
        "resume",
        "recraft_prompt",
        "fix_input",
        "human_review",
    }
)
FAILURE_KINDS = frozenset({"validation", "network", "dependency", "config", "unknown"})

RESPONSE_FIELDS = (
    "schema_version",
    "ok",
    "command",
    "stage",
    "status",
    "next_action",
    "inputs",
    "outputs",
    "summary",
    "failures",
)

FAILURE_KIND_BY_CODE = {
    "brief_missing": "validation",
    "brief_invalid": "validation",
    "production_missing": "validation",
    "production_invalid": "validation",
    "manifest_missing": "validation",
    "manifest_invalid": "validation",
    "progress_invalid": "validation",
    "unsupported_stage": "config",
    "config_read": "config",
    "network_error": "network",
    "dependency_missing": "dependency",
    "task_failed": "unknown",
    "run_failed": "unknown",
    "resume_failed": "unknown",
    "init_failed": "unknown",
    "rollback_failed": "dependency",
    "workflow_error": "unknown",
}


def make_failure(
    code: str,
    message: str,
    *,
    kind: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    expected_kind = FAILURE_KIND_BY_CODE.get(code, "unknown")
    if kind is not None and kind != expected_kind:
        raise ValueError(
            f"failure {code} kind must be {expected_kind}, got {kind}"
        )
    resolved_kind = expected_kind
    return {
        "code": code,
        "kind": resolved_kind,
        "message": message,
        **details,
    }


def build_response(
    *,
    command: str,
    ok: bool,
    stage: str,
    status: str,
    next_action: str,
    inputs: dict[str, Any] | None = None,
    outputs: list[str] | None = None,
    summary: dict[str, Any] | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"invalid workflow stage: {stage}")
    if status not in STATUSES:
        raise ValueError(f"invalid workflow status: {status}")
    if next_action not in NEXT_ACTIONS:
        raise ValueError(f"invalid workflow next_action: {next_action}")

    checked_failures: list[dict[str, Any]] = []
    for failure in failures or []:
        if not isinstance(failure, dict):
            raise ValueError("failure must be an object")
        if "kind" not in failure:
            raise ValueError("failure missing kind")
        if failure["kind"] not in FAILURE_KINDS:
            raise ValueError(f"invalid failure kind: {failure['kind']}")
        code = str(failure.get("code") or "")
        if not code:
            raise ValueError("failure missing code")
        expected_kind = FAILURE_KIND_BY_CODE.get(code, "unknown")
        if failure["kind"] != expected_kind:
            raise ValueError(
                f"failure {code} kind must be {expected_kind}, got {failure['kind']}"
            )
        checked_failures.append(dict(failure))

    return {
        "schema_version": SCHEMA_VERSION,
        "ok": bool(ok),
        "command": command,
        "stage": stage,
        "status": status,
        "next_action": next_action,
        "inputs": inputs or {},
        "outputs": outputs or [],
        "summary": summary or {},
        "failures": checked_failures,
    }


def emit_response(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    click.echo(
        f"{payload['command']}: {payload['status']} -> {payload['next_action']}"
    )
    for output in payload.get("outputs") or []:
        click.echo(f"output: {output}")
    for failure in payload.get("failures") or []:
        click.echo(
            f"failure[{failure['kind']}]: {failure.get('message') or failure['code']}",
            err=True,
        )
