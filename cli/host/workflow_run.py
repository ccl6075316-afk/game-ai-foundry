"""One-shot external-agent workflow bridge.

This module keeps the six workflow commands deterministic while giving an
external agent a single auditable entry point.  It intentionally delegates to
the existing ``gamefactory.py workflow`` commands instead of creating a new
state store.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from project_paths import default_paths_for_brief
from workflow.contract import build_response, make_failure


Runner = Callable[[list[str]], dict[str, Any]]


def _step_stage(argv: list[str]) -> str:
    if argv and argv[0] in {"context", "validate"}:
        return "design"
    if argv and argv[0] == "init":
        return "production"
    return "assets"


def _error_payload(argv: list[str], message: str) -> dict[str, Any]:
    return build_response(
        command=" ".join(argv[:2]) if argv else "workflow",
        ok=False,
        stage=_step_stage(argv),
        status="blocked",
        next_action="fix_input",
        inputs={"argv": argv},
        failures=[make_failure("workflow_error", message)],
    )


def _run_cli_step(argv: list[str], *, timeout_sec: int = 3600) -> dict[str, Any]:
    """Run one existing workflow command and parse its stable JSON response."""
    script = Path(__file__).resolve().parents[1] / "gamefactory.py"
    env = {
        **os.environ,
        "GAMEFACTORY_ROOT": str(script.parent.parent),
        "PYTHONIOENCODING": "utf-8",
    }
    command = [sys.executable, str(script), *argv, "--json"]
    try:
        proc = subprocess.run(
            command,
            cwd=str(script.parent),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit_code": 1, "payload": _error_payload(argv, str(exc))}

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = _error_payload(argv, "workflow command returned non-JSON output")
    return {"exit_code": proc.returncode, "payload": payload}


def _record_step(steps: list[dict[str, Any]], argv: list[str], result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload") if isinstance(result.get("payload"), dict) else _error_payload(argv, "invalid workflow response")
    record = {
        "command": " ".join(argv[:2]),
        "argv": argv,
        "exit_code": result.get("exit_code", 1),
        "ok": bool(payload.get("ok")),
        "status": payload.get("status"),
        "next_action": payload.get("next_action"),
        "outputs": payload.get("outputs") or [],
        "failures": payload.get("failures") or [],
    }
    steps.append(record)
    return payload


def _final_response(
    *,
    payload: dict[str, Any],
    steps: list[dict[str, Any]],
    inputs: dict[str, Any],
    dry_run: bool,
    i_confirm: bool,
) -> dict[str, Any]:
    outputs: list[str] = []
    for step in steps:
        for output in step.get("outputs") or []:
            if output not in outputs:
                outputs.append(output)
    failures = list(payload.get("failures") or [])
    ok = bool(payload.get("ok")) and not failures
    return build_response(
        command="host workflow-run",
        ok=ok,
        stage=str(payload.get("stage") or "assets"),
        status=str(payload.get("status") or "blocked"),
        next_action=str(payload.get("next_action") or "fix_input"),
        inputs=inputs,
        outputs=outputs,
        summary={
            "steps": steps,
            "final": payload,
            "dry_run": bool(dry_run),
            "confirmed": bool(i_confirm),
        },
        failures=failures,
    )


def _blocked_response(
    *,
    code: str,
    message: str,
    steps: list[dict[str, Any]],
    inputs: dict[str, Any],
    stage: str,
    status: str,
    next_action: str,
    dry_run: bool,
    i_confirm: bool,
) -> dict[str, Any]:
    payload = build_response(
        command="host workflow-run",
        ok=False,
        stage=stage,
        status=status,
        next_action=next_action,
        inputs=inputs,
        failures=[make_failure(code, message)],
    )
    return _final_response(
        payload=payload,
        steps=steps,
        inputs=inputs,
        dry_run=dry_run,
        i_confirm=i_confirm,
    )


def run_workflow(
    brief_path: Path | str,
    *,
    production_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
    stage: str = "assets",
    auto_fix: bool = True,
    run_prompts: bool = False,
    jobs: int = 4,
    auto_resume: bool = True,
    max_resumes: int = 3,
    dry_run: bool = False,
    i_confirm: bool = False,
    detach: bool = False,
    timeout_sec: int = 3600,
    runner: Runner | None = None,
) -> dict[str, Any]:
    """Execute context/validate/init/run/status/resume as one safe chain."""
    brief = Path(brief_path).expanduser().resolve()
    paths = default_paths_for_brief(brief)
    production = Path(production_path or paths["production"]).expanduser().resolve()
    manifest = Path(manifest_path or paths["manifest"]).expanduser().resolve()
    run_step = runner or (lambda argv: _run_cli_step(argv, timeout_sec=timeout_sec))
    steps: list[dict[str, Any]] = []
    inputs = {
        "brief": str(brief),
        "production": str(production),
        "manifest": str(manifest),
        "stage": stage,
        "auto_fix": bool(auto_fix),
        "run_prompts": bool(run_prompts),
        "jobs": int(jobs),
        "auto_resume": bool(auto_resume),
        "max_resumes": int(max_resumes),
        "dry_run": bool(dry_run),
        "i_confirm": bool(i_confirm),
        "detach": bool(detach),
    }

    context = _record_step(steps, ["workflow", "context", "--brief", str(brief)], run_step(["workflow", "context", "--brief", str(brief)]))
    if not context.get("ok"):
        return _final_response(payload=context, steps=steps, inputs=inputs, dry_run=dry_run, i_confirm=i_confirm)

    validate_argv = ["workflow", "validate", "--brief", str(brief)]
    if production.is_file():
        validate_argv += ["--production", str(production)]
    if manifest.is_file():
        validate_argv += ["--manifest", str(manifest)]
    validation = _record_step(steps, validate_argv, run_step(validate_argv))
    if not validation.get("ok"):
        return _final_response(payload=validation, steps=steps, inputs=inputs, dry_run=dry_run, i_confirm=i_confirm)
    if dry_run:
        return _final_response(payload=validation, steps=steps, inputs=inputs, dry_run=dry_run, i_confirm=i_confirm)
    if not i_confirm:
        return _blocked_response(
            code="confirmation_required",
            message="host workflow-run writes state and runs generation; pass --i-confirm once",
            steps=steps,
            inputs=inputs,
            stage=str(validation.get("stage") or "design"),
            status="blocked",
            next_action=str(validation.get("next_action") or "derive_production"),
            dry_run=dry_run,
            i_confirm=i_confirm,
        )

    missing = set((context.get("summary") or {}).get("missing") or [])
    if validation.get("next_action") == "derive_production" or missing:
        init_argv = ["workflow", "init", "--brief", str(brief), "--manifest", str(manifest)]
        init = _record_step(steps, init_argv, run_step(init_argv))
        if not init.get("ok"):
            return _final_response(payload=init, steps=steps, inputs=inputs, dry_run=dry_run, i_confirm=i_confirm)

        validate_argv = ["workflow", "validate", "--brief", str(brief), "--production", str(production), "--manifest", str(manifest)]
        validation = _record_step(steps, validate_argv, run_step(validate_argv))
        if not validation.get("ok"):
            return _final_response(payload=validation, steps=steps, inputs=inputs, dry_run=dry_run, i_confirm=i_confirm)

    current = validation
    if current.get("next_action") == "run":
        run_argv = [
            "workflow",
            "run",
            "--manifest",
            str(manifest),
            "--stage",
            stage,
            "--auto-fix" if auto_fix else "--no-auto-fix",
            "--jobs",
            str(jobs),
        ]
        if run_prompts:
            run_argv.append("--run-prompts")
        if detach:
            run_argv.append("--detach")
        current = _record_step(steps, run_argv, run_step(run_argv))
        status_argv = ["workflow", "status", "--manifest", str(manifest)]
        if detach:
            job_id = (current.get("summary") or {}).get("job_id")
            jobs_dir = (current.get("summary") or {}).get("jobs_dir")
            if job_id:
                status_argv += ["--job-id", str(job_id)]
            if jobs_dir:
                status_argv += ["--jobs-dir", str(jobs_dir)]
            current = _record_step(steps, status_argv, run_step(status_argv))
            return _final_response(
                payload=current, steps=steps, inputs=inputs, dry_run=dry_run, i_confirm=i_confirm
            )
        current = _record_step(steps, status_argv, run_step(status_argv))

    resumed: set[str] = set()
    while auto_resume and current.get("status") == "failed" and current.get("next_action") == "resume" and len(resumed) < max_resumes:
        failed_ids = [str(value) for value in ((current.get("summary") or {}).get("manifest") or {}).get("failed_ids") or []]
        task_id = next((value for value in failed_ids if value not in resumed), None)
        if not task_id:
            break
        resumed.add(task_id)
        resume_argv = ["workflow", "resume", "--manifest", str(manifest), "--task-id", task_id]
        if run_prompts:
            resume_argv.append("--recraft-prompt")
        current = _record_step(steps, resume_argv, run_step(resume_argv))
        status_argv = ["workflow", "status", "--manifest", str(manifest)]
        current = _record_step(steps, status_argv, run_step(status_argv))

    return _final_response(payload=current, steps=steps, inputs=inputs, dry_run=dry_run, i_confirm=i_confirm)
