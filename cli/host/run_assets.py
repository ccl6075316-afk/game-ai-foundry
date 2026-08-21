"""Batch pipeline run with optional diagnose/heal/fix_commands auto-repair loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config_cmds import apply_config_set
from pipeline_heal import can_auto_fix_without_agent, diagnose_and_heal_file
from pipeline_manifest import load_manifest, save_manifest
from pipeline_runner import PipelineRunResult, reset_task, reset_task_cascade, run_pipeline
from safe_cli import SafeCliError, normalize_action


def _run_exit_code(result: PipelineRunResult) -> int:
    if result.complete:
        return 0
    if result.paused:
        return 2
    if result.blocked:
        return 1
    return 1


def _safe_diagnosis(manifest_path: Path) -> dict[str, Any] | None:
    """Best-effort diagnose for GUI copy when auto-fix stops."""
    try:
        return diagnose_and_heal_file(manifest_path, apply=False)
    except (ValueError, OSError, SafeCliError):
        return None


def _failure_fingerprints(diagnosis: dict[str, Any]) -> frozenset[tuple[str, str]]:
    items = list(diagnosis.get("items") or [])
    if not items:
        items = list(diagnosis.get("needs_hermes") or []) + list(diagnosis.get("auto_healable") or [])
    out: set[tuple[str, str]] = set()
    for item in items:
        task_id = str(item.get("task_id") or "")
        kind = str(item.get("kind") or "")
        if task_id:
            out.add((task_id, kind))
    return frozenset(out)


def _argv_flag(argv: list[str], name: str) -> str | None:
    for index, token in enumerate(argv):
        if token == name and index + 1 < len(argv):
            return argv[index + 1]
    return None


def _argv_has_flag(argv: list[str], name: str) -> bool:
    return name in argv


def _run_round_record(
    *,
    phase: str,
    run_result: PipelineRunResult,
    repair_round: int | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "phase": phase,
        "complete": run_result.complete,
        "paused": run_result.paused,
        "blocked": run_result.blocked,
        "exit_code": _run_exit_code(run_result),
        "message": run_result.message,
        "summary": run_result.summary,
    }
    if repair_round is not None:
        record["repair_round"] = repair_round
    return record


def _execute_fix_commands(
    manifest_path: Path,
    fix_commands: list[str],
    *,
    default_jobs: int,
    default_run_prompts: bool,
) -> dict[str, Any]:
    """Apply whitelisted fix_commands in-process where possible."""
    manifest_path = manifest_path.resolve()
    manifest = load_manifest(manifest_path)
    executed: list[dict[str, Any]] = []
    deferred_run: dict[str, Any] | None = None

    for raw in fix_commands:
        info = normalize_action(str(raw))
        if not info["ok"]:
            raise ValueError(info.get("error") or f"fix command not allowed: {raw}")
        argv = info["argv"]
        if len(argv) < 2:
            raise ValueError(f"unsupported fix command: {raw}")

        if argv[0] == "pipeline" and argv[1] == "reset":
            task_id = _argv_flag(argv, "--task-id")
            if not task_id:
                raise ValueError(f"pipeline reset missing --task-id: {raw}")
            cascade = not _argv_has_flag(argv, "--no-cascade")
            if cascade:
                reset_ids = reset_task_cascade(manifest, task_id)
            else:
                reset_task(manifest, task_id)
                reset_ids = [task_id]
            executed.append(
                {
                    "action": "reset",
                    "command": raw,
                    "task_id": task_id,
                    "cascade": cascade,
                    "reset_ids": reset_ids,
                }
            )
            continue

        if argv[0] == "config" and argv[1] == "set":
            key = _argv_flag(argv, "--key")
            value = _argv_flag(argv, "--value")
            if not key or value is None:
                raise ValueError(f"config set missing --key/--value: {raw}")
            result = apply_config_set(key, value)
            executed.append({"action": "config_set", "command": raw, **result})
            continue

        if argv[0] == "pipeline" and argv[1] == "run":
            jobs_raw = _argv_flag(argv, "--jobs")
            jobs = int(jobs_raw) if jobs_raw is not None else default_jobs
            deferred_run = {
                "command": raw,
                "jobs": jobs,
                "run_prompts": _argv_has_flag(argv, "--run-prompts") or default_run_prompts,
            }
            executed.append({"action": "pipeline_run", **deferred_run})
            continue

        raise ValueError(f"unsupported fix command: {raw}")

    save_manifest(manifest_path, manifest)

    run_result: PipelineRunResult | None = None
    if deferred_run is not None:
        run_result = run_pipeline(
            manifest_path,
            jobs=int(deferred_run["jobs"]),
            run_prompts=bool(deferred_run["run_prompts"]),
        )

    return {"executed": executed, "run_result": run_result}


def run_assets(
    manifest_path: Path,
    *,
    jobs: int = 4,
    run_prompts: bool = False,
    auto_fix: bool = True,
    max_repair_rounds: int = 2,
) -> dict[str, Any]:
    """Run the pipeline; optionally auto-repair validation/config failures up to max rounds."""
    manifest_path = manifest_path.resolve()
    rounds: list[dict[str, Any]] = []
    repair_rounds = 0
    prior_fingerprints: frozenset[tuple[str, str]] | None = None

    run_result = run_pipeline(manifest_path, jobs=jobs, run_prompts=run_prompts)
    rounds.append(_run_round_record(phase="initial_run", run_result=run_result))

    if run_result.complete:
        return {
            "ok": True,
            "stopped_reason": "complete",
            "repair_rounds": 0,
            "rounds": rounds,
            "summary": run_result.summary,
            "message": run_result.message,
            "complete": True,
            "paused": False,
            "blocked": False,
            "run_exit_code": 0,
        }

    if not auto_fix:
        return {
            "ok": False,
            "stopped_reason": "error",
            "repair_rounds": 0,
            "rounds": rounds,
            "summary": run_result.summary,
            "message": run_result.message,
            "complete": False,
            "paused": run_result.paused,
            "blocked": run_result.blocked,
            "run_exit_code": _run_exit_code(run_result),
            "diagnosis": _safe_diagnosis(manifest_path),
        }

    stopped_reason = "max_rounds"
    last_diagnosis: dict[str, Any] | None = None
    while repair_rounds < max_repair_rounds:
        try:
            heal_report = diagnose_and_heal_file(manifest_path, apply=True)
        except (ValueError, OSError, SafeCliError) as exc:
            return {
                "ok": False,
                "stopped_reason": "error",
                "repair_rounds": repair_rounds,
                "rounds": rounds,
                "summary": run_result.summary,
                "message": str(exc),
                "complete": False,
                "paused": run_result.paused,
                "blocked": run_result.blocked,
                "run_exit_code": _run_exit_code(run_result),
                "error": str(exc),
                "diagnosis": _safe_diagnosis(manifest_path),
            }

        diagnosis = heal_report.get("diagnose") if isinstance(heal_report.get("diagnose"), dict) else heal_report
        if isinstance(diagnosis, dict):
            last_diagnosis = diagnosis
        fingerprints = _failure_fingerprints(diagnosis)
        healed = [str(t) for t in (heal_report.get("healed") or []) if t]
        failed_count = int(diagnosis.get("failed_count") or 0)
        auto_fixable = bool(
            heal_report.get("auto_fix_without_agent")
            if heal_report.get("auto_fix_without_agent") is not None
            else can_auto_fix_without_agent(diagnosis)
        )
        rounds.append(
            {
                "phase": "diagnose",
                "repair_round": repair_rounds + 1,
                "fingerprints": [list(item) for item in sorted(fingerprints)],
                "healed": healed,
                "failed_count": failed_count,
                "auto_fix_without_agent": auto_fixable,
            }
        )

        # Code-owned heal resets failed→pending; post diagnose then has no needs_hermes,
        # so can_auto_fix is false — still must re-run, not bail to needs_agent.
        if healed and failed_count == 0 and not fingerprints:
            repair_rounds += 1
            rounds.append(
                {
                    "phase": "repair",
                    "repair_round": repair_rounds,
                    "fix_commands": [],
                    "executed": [{"action": "code_heal", "healed": healed}],
                }
            )
            run_result = run_pipeline(
                manifest_path,
                jobs=jobs,
                run_prompts=run_prompts,
            )
            rounds.append(
                _run_round_record(phase="run", run_result=run_result, repair_round=repair_rounds)
            )
            if run_result.complete:
                return {
                    "ok": True,
                    "stopped_reason": "complete",
                    "repair_rounds": repair_rounds,
                    "rounds": rounds,
                    "summary": run_result.summary,
                    "message": run_result.message,
                    "complete": True,
                    "paused": False,
                    "blocked": False,
                    "run_exit_code": 0,
                }
            if prior_fingerprints is not None and fingerprints == prior_fingerprints:
                stopped_reason = "max_rounds"
                break
            prior_fingerprints = fingerprints
            continue

        if not can_auto_fix_without_agent(diagnosis):
            return {
                "ok": False,
                "stopped_reason": "needs_agent",
                "repair_rounds": repair_rounds,
                "rounds": rounds,
                "summary": diagnosis.get("summary") or run_result.summary,
                "message": run_result.message,
                "complete": False,
                "paused": run_result.paused,
                "blocked": run_result.blocked,
                "run_exit_code": _run_exit_code(run_result),
                "diagnosis": diagnosis,
            }

        fix_commands = list(
            heal_report.get("fix_commands")
            or diagnosis.get("fix_commands")
            or []
        )
        try:
            fix_out = _execute_fix_commands(
                manifest_path,
                fix_commands,
                default_jobs=jobs,
                default_run_prompts=run_prompts or any(
                    "--run-prompts" in str(line) for line in fix_commands
                ),
            )
        except (ValueError, OSError) as exc:
            return {
                "ok": False,
                "stopped_reason": "error",
                "repair_rounds": repair_rounds,
                "rounds": rounds,
                "summary": run_result.summary,
                "message": str(exc),
                "complete": False,
                "paused": run_result.paused,
                "blocked": run_result.blocked,
                "run_exit_code": _run_exit_code(run_result),
                "error": str(exc),
                "diagnosis": last_diagnosis or _safe_diagnosis(manifest_path),
            }

        repair_rounds += 1
        rounds.append(
            {
                "phase": "repair",
                "repair_round": repair_rounds,
                "fix_commands": fix_commands,
                "executed": fix_out.get("executed") or [],
            }
        )

        run_result = fix_out.get("run_result")
        if run_result is None:
            repair_run_prompts = run_prompts or any("--run-prompts" in str(line) for line in fix_commands)
            run_result = run_pipeline(
                manifest_path,
                jobs=jobs,
                run_prompts=repair_run_prompts,
            )
        rounds.append(_run_round_record(phase="run", run_result=run_result, repair_round=repair_rounds))

        if run_result.complete:
            return {
                "ok": True,
                "stopped_reason": "complete",
                "repair_rounds": repair_rounds,
                "rounds": rounds,
                "summary": run_result.summary,
                "message": run_result.message,
                "complete": True,
                "paused": False,
                "blocked": False,
                "run_exit_code": 0,
            }

        if prior_fingerprints is not None and fingerprints == prior_fingerprints:
            stopped_reason = "max_rounds"
            break
        prior_fingerprints = fingerprints

    return {
        "ok": False,
        "stopped_reason": stopped_reason,
        "repair_rounds": repair_rounds,
        "rounds": rounds,
        "summary": run_result.summary,
        "message": run_result.message,
        "complete": False,
        "paused": run_result.paused,
        "blocked": run_result.blocked,
        "run_exit_code": _run_exit_code(run_result),
        "diagnosis": last_diagnosis or _safe_diagnosis(manifest_path),
    }
