"""CLI: deterministic workflow composition for external agents."""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import click

import assets_manifest as assets_manifest_module
import pipeline_manifest as pipeline_manifest_module
import progress as progress_module
from assets_manifest import save_assets_manifest as save_assets_manifest_file
from brief import audit_brief_for_export, load_brief_full
from host.retry_asset import retry_asset
from host.run_assets import run_assets
from pipeline_manifest import build_manifest, load_manifest, save_manifest
from plan_io import save_handoff as save_handoff_file
from production import derive_production, load_production, save_production, validate_production
from progress import init_progress, load_progress, save_progress
from project_paths import default_paths_for_brief
from workflow import (
    build_response,
    classify_manifest_state,
    classify_runner_state,
    emit_response,
    make_failure,
    manifest_failures,
    manifest_validation_errors,
    summarize_manifest,
)


class WorkflowInputError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _path_input(path: Path) -> str:
    return str(path.resolve())


def _require_brief(brief_path: Path) -> Path:
    brief = brief_path.expanduser().resolve()
    if not brief.is_file():
        raise WorkflowInputError("brief_missing", f"brief not found: {brief}")
    return brief


def _require_manifest(manifest_path: Path) -> Path:
    manifest = manifest_path.expanduser().resolve()
    if not manifest.is_file():
        raise WorkflowInputError("manifest_missing", f"manifest not found: {manifest}")
    return manifest


def _error_payload(
    *,
    command: str,
    stage: str,
    inputs: dict[str, Any],
    exc: Exception,
    code: str | None = None,
    outputs: list[str] | None = None,
    summary: dict[str, Any] | None = None,
    extra_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    failure_code = code or (exc.code if isinstance(exc, WorkflowInputError) else "workflow_error")
    summary_data = {"error_type": type(exc).__name__, **(summary or {})}
    failures = [make_failure(failure_code, str(exc))]
    failures.extend(extra_failures or [])
    return build_response(
        command=command,
        ok=False,
        stage=stage,
        status="blocked",
        next_action="fix_input",
        inputs=inputs,
        outputs=outputs or [],
        summary=summary_data,
        failures=failures,
    )


def _paths_summary(paths: dict[str, Any], *, manifest_path: Path) -> dict[str, Any]:
    production_path = Path(paths["production"])
    progress_path = Path(paths["progress"])
    return {
        "brief": _path_input(Path(paths["brief"])),
        "project_root": _path_input(Path(paths["project_root"])) if paths.get("project_root") else None,
        "output_dir": _path_input(Path(paths["output_dir"])),
        "plans_dir": _path_input(Path(paths["plans_dir"])),
        "godot_project": _path_input(Path(paths["godot_project"])),
        "production": _path_input(production_path),
        "production_exists": production_path.is_file(),
        "progress": _path_input(progress_path),
        "progress_exists": progress_path.is_file(),
        "manifest": _path_input(manifest_path),
        "manifest_exists": manifest_path.is_file(),
        "isolated": bool(paths.get("isolated")),
    }


def _progress_summary(progress: dict[str, Any] | None) -> dict[str, Any]:
    if progress is None:
        return {"exists": False}
    phases = progress.get("phases") if isinstance(progress.get("phases"), dict) else {}
    godot_tasks = phases.get("godot_tasks") if isinstance(phases.get("godot_tasks"), list) else []
    counts: dict[str, int] = {}
    for task in godot_tasks:
        if isinstance(task, dict):
            status = str(task.get("status") or "pending")
            counts[status] = counts.get(status, 0) + 1
    return {
        "exists": True,
        "schema_version": (progress.get("progress_meta") or {}).get("schema_version"),
        "pipeline_run": (phases.get("pipeline_run") or {}).get("status"),
        "godot_task_counts": counts,
    }


def _progress_validation_errors(progress: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    meta = progress.get("progress_meta")
    if not isinstance(meta, dict):
        errors.append("missing progress_meta object")
    elif meta.get("schema_version") != 1:
        errors.append("progress_meta.schema_version must be 1")
    phases = progress.get("phases")
    if not isinstance(phases, dict):
        errors.append("missing phases object")
    elif not isinstance(phases.get("godot_tasks"), list):
        errors.append("phases.godot_tasks must be a list")
    return errors


def _validation_failures(errors: list[str], code: str) -> list[dict[str, Any]]:
    return [make_failure(code, error) for error in errors]


@contextmanager
def _defer_pipeline_manifest_writes() -> Iterator[tuple[list[tuple[Path, dict[str, Any]]], dict[Path, dict[str, Any]]]]:
    handoffs: list[tuple[Path, dict[str, Any]]] = []
    assets_writes: dict[Path, dict[str, Any]] = {}
    original_handoff_save = pipeline_manifest_module.save_handoff
    original_assets_save = assets_manifest_module.save_assets_manifest

    def capture_handoff(path: Path, data: dict[str, Any]) -> None:
        handoffs.append((path.resolve(), copy.deepcopy(data)))

    def capture_assets(path: Path, data: dict[str, Any]) -> None:
        assets_writes[path.resolve()] = copy.deepcopy(data)

    pipeline_manifest_module.save_handoff = capture_handoff
    assets_manifest_module.save_assets_manifest = capture_assets
    try:
        yield handoffs, assets_writes
    finally:
        pipeline_manifest_module.save_handoff = original_handoff_save
        assets_manifest_module.save_assets_manifest = original_assets_save


def _build_manifest_in_memory(
    brief: Path,
    *,
    output_dir: Path,
    plans_dir: Path,
    godot_project: Path,
) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any]]], dict[Path, dict[str, Any]]]:
    with _defer_pipeline_manifest_writes() as (handoffs, assets_writes):
        manifest = build_manifest(
            brief,
            output_dir=output_dir,
            plans_dir=plans_dir,
            godot_project=godot_project,
        )
    if not assets_writes:
        raise ValueError("pipeline manifest build did not produce an assets manifest")
    return manifest, handoffs, assets_writes


@contextmanager
def _init_progress_from_memory(
    production_path: Path,
    production: dict[str, Any],
    *,
    brief_path: Path,
    project_path: Path,
) -> Iterator[dict[str, Any]]:
    original_load_production = progress_module.load_production
    progress_module.load_production = lambda _path: production
    try:
        yield init_progress(
            brief_path=brief_path,
            production_path=production_path,
            project_path=project_path,
        )
    finally:
        progress_module.load_production = original_load_production


def _missing_directories(path: Path) -> list[Path]:
    missing: list[Path] = []
    current = path.parent
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    return list(reversed(missing))


def _rollback_new_files(
    paths: list[Path],
    directories: list[Path],
) -> list[str]:
    residual: list[str] = []
    for path in reversed(paths):
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError:
            residual.append(_path_input(path))
    for directory in reversed(directories):
        if not directory.exists():
            continue
        try:
            directory.rmdir()
        except OSError:
            residual.append(_path_input(directory))
    return list(dict.fromkeys(residual))


@click.group("workflow")
def workflow_group() -> None:
    """Deterministic external-agent workflow commands."""


@workflow_group.command("context")
@click.option("--brief", "brief_path", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print one stable JSON object.")
def context_cmd(brief_path: Path, as_json: bool) -> None:
    """Read Brief and existing deterministic project state."""
    command = "context"
    stage = "design"
    inputs = {"brief": str(brief_path)}
    try:
        brief = _require_brief(brief_path)
        paths = default_paths_for_brief(brief)
        production_path = Path(paths["production"])
        progress_path = Path(paths["progress"])
        manifest_path = Path(paths["manifest"])

        project, assets, graphs = load_brief_full(brief)
        brief_errors = audit_brief_for_export(
            project, assets, animation_graphs=graphs, brief_path=brief
        )
        production = load_production(production_path) if production_path.is_file() else None
        production_errors = (
            validate_production(production, brief_path=brief) if production is not None else []
        )
        progress = load_progress(progress_path) if progress_path.is_file() else None
        progress_errors = _progress_validation_errors(progress) if progress is not None else []
        manifest = load_manifest(manifest_path) if manifest_path.is_file() else None
        manifest_errors = manifest_validation_errors(manifest) if manifest is not None else []
        manifest_state = summarize_manifest(manifest) if manifest is not None else None

        failures = _validation_failures(brief_errors, "brief_invalid")
        failures.extend(_validation_failures(production_errors, "production_invalid"))
        failures.extend(_validation_failures(progress_errors, "progress_invalid"))
        failures.extend(_validation_failures(manifest_errors, "manifest_invalid"))
        missing = [
            name
            for name, exists in (
                ("production", production_path.is_file()),
                ("progress", progress_path.is_file()),
                ("manifest", manifest_path.is_file()),
            )
            if not exists
        ]

        if failures:
            status, next_action = "blocked", "fix_input"
        elif missing:
            status, next_action = "blocked", "derive_production"
        elif manifest_state is not None:
            status, next_action = classify_manifest_state(manifest_state)
        else:
            status, next_action = "blocked", "derive_production"

        payload = build_response(
            command=command,
            ok=not failures,
            stage=stage,
            status=status,
            next_action=next_action,
            inputs=inputs,
            summary={
                "paths": _paths_summary(paths, manifest_path=manifest_path),
                "brief": {
                    "title": project.title,
                    "asset_count": len(assets),
                    "animation_graph_count": len(graphs),
                    "valid": not brief_errors,
                },
                "production": {
                    "exists": production is not None,
                    "valid": production is not None and not production_errors,
                },
                "progress": _progress_summary(progress),
                "manifest": manifest_state,
                "missing": missing,
            },
            failures=failures,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        payload = _error_payload(command=command, stage=stage, inputs=inputs, exc=exc)

    emit_response(payload, as_json=as_json)
    if not payload["ok"]:
        raise SystemExit(1)


@workflow_group.command("init")
@click.option("--brief", "brief_path", required=True, type=click.Path(path_type=Path))
@click.option("--manifest", "manifest_path", default=None, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print one stable JSON object.")
def init_cmd(brief_path: Path, manifest_path: Path | None, as_json: bool) -> None:
    """Create missing deterministic state while preserving existing files."""
    command = "init"
    stage = "production"
    inputs = {"brief": str(brief_path), "manifest": str(manifest_path) if manifest_path else None}
    attempted_outputs: list[str] = []
    created_targets: list[Path] = []
    created_directories: list[Path] = []
    try:
        brief = _require_brief(brief_path)
        paths = default_paths_for_brief(brief)
        production_path = Path(paths["production"]).resolve()
        progress_path = Path(paths["progress"]).resolve()
        resolved_manifest = (
            manifest_path.expanduser().resolve()
            if manifest_path is not None
            else Path(paths["manifest"]).resolve()
        )
        inputs["manifest"] = str(resolved_manifest)

        project, brief_assets, graphs = load_brief_full(brief)
        brief_errors = audit_brief_for_export(
            project, brief_assets, animation_graphs=graphs, brief_path=brief
        )
        if brief_errors:
            raise WorkflowInputError("brief_invalid", "; ".join(brief_errors))

        if production_path.is_file():
            production = load_production(production_path)
            production_is_new = False
        else:
            production = derive_production(brief)
            production_is_new = True
        production_errors = validate_production(production, brief_path=brief)
        if production_errors:
            raise WorkflowInputError("production_invalid", "; ".join(production_errors))

        handoff_writes: list[tuple[Path, dict[str, Any]]] = []
        assets_writes: dict[Path, dict[str, Any]] = {}
        if resolved_manifest.is_file():
            manifest = load_manifest(resolved_manifest)
            manifest_is_new = False
        else:
            manifest, handoff_writes, assets_writes = _build_manifest_in_memory(
                brief,
                output_dir=Path(paths["output_dir"]),
                plans_dir=Path(paths["plans_dir"]),
                godot_project=Path(paths["godot_project"]),
            )
            manifest_is_new = True
        manifest_errors = manifest_validation_errors(manifest)
        if manifest_errors:
            raise WorkflowInputError("manifest_invalid", "; ".join(manifest_errors))

        if progress_path.is_file():
            progress = load_progress(progress_path)
            progress_is_new = False
            progress_errors = _progress_validation_errors(progress)
            if progress_errors:
                raise WorkflowInputError("progress_invalid", "; ".join(progress_errors))
        else:
            with _init_progress_from_memory(
                production_path,
                production,
                brief_path=brief,
                project_path=Path(paths["godot_project"]),
            ) as progress:
                pass
            progress_is_new = True

        handoff_targets = [
            (path, data) for path, data in handoff_writes if not path.exists()
        ]
        assets_target = next(iter(assets_writes.items()), None)
        assets_is_new = assets_target is not None and not assets_target[0].exists()
        target_specs: list[tuple[Path, bool]] = [
            (production_path, production_is_new),
            (resolved_manifest, manifest_is_new),
            (progress_path, progress_is_new),
            *[(path, True) for path, _ in handoff_targets],
            *([(assets_target[0], True)] if assets_is_new and assets_target else []),
        ]
        created_targets = [path for path, is_new in target_specs if is_new]
        attempted_outputs = [
            path
            for path, _ in [
                (production_path, production_is_new),
                (resolved_manifest, manifest_is_new),
                (progress_path, progress_is_new),
                *[(path, True) for path, _ in handoff_writes],
                *([(assets_target[0], True)] if assets_target else []),
            ]
        ]
        attempted_output_strings = [_path_input(path) for path in attempted_outputs]

        for target in created_targets:
            for directory in _missing_directories(target):
                if directory not in created_directories:
                    created_directories.append(directory)

        # All state has now been built and validated in memory.
        for directory in created_directories:
            directory.mkdir(parents=True, exist_ok=True)

        if production_is_new:
            save_production(production, production_path)
        if manifest_is_new:
            save_manifest(resolved_manifest, manifest)
        if progress_is_new:
            save_progress(progress, progress_path)
        for handoff_path, handoff_data in handoff_targets:
            save_handoff_file(handoff_path, handoff_data)
        if assets_is_new and assets_target:
            save_assets_manifest_file(assets_target[0], assets_target[1])

        summary = summarize_manifest(manifest)
        status, next_action = classify_manifest_state(summary)
        all_outputs = [
            _path_input(path)
            for path, _ in target_specs
        ]
        payload = build_response(
            command=command,
            ok=True,
            stage=stage,
            status=status,
            next_action=next_action,
            inputs=inputs,
            outputs=list(dict.fromkeys(all_outputs)),
            summary={
                "created": [_path_input(path) for path in created_targets],
                "created_directories": [_path_input(path) for path in created_directories],
                "preserved": [
                    _path_input(path)
                    for path, is_new in target_specs
                    if not is_new
                ],
                "outputs": list(dict.fromkeys(all_outputs)),
                "manifest": summary,
            },
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        if created_targets or created_directories:
            residual = _rollback_new_files(created_targets, created_directories)
        else:
            residual = []
        extra_failures = (
            [make_failure("rollback_failed", "init rollback left residual files")]
            if residual
            else []
        )
        payload = _error_payload(
            command=command,
            stage=stage,
            inputs=inputs,
            exc=exc,
            code=exc.code if isinstance(exc, WorkflowInputError) else "init_failed",
            outputs=attempted_output_strings if "attempted_output_strings" in locals() else [],
            summary={
                "created": residual,
                "outputs": attempted_output_strings
                if "attempted_output_strings" in locals()
                else [],
            },
            extra_failures=extra_failures,
        )

    emit_response(payload, as_json=as_json)
    if not payload["ok"]:
        raise SystemExit(1)


@workflow_group.command("run")
@click.option("--manifest", "manifest_path", required=True, type=click.Path(path_type=Path))
@click.option(
    "--stage",
    default="assets",
    show_default=True,
    help="Workflow stage. Only assets is currently supported.",
)
@click.option("--auto-fix/--no-auto-fix", default=True, show_default=True)
@click.option("--run-prompts", is_flag=True, default=False)
@click.option("--jobs", default=4, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True, help="Print one stable JSON object.")
def run_cmd(
    manifest_path: Path,
    stage: str,
    auto_fix: bool,
    run_prompts: bool,
    jobs: int,
    as_json: bool,
) -> None:
    """Run an existing stage through the deterministic asset runner."""
    command = "run"
    inputs = {
        "manifest": str(manifest_path),
        "stage": stage,
        "auto_fix": auto_fix,
        "run_prompts": run_prompts,
        "jobs": jobs,
    }
    if stage != "assets":
        payload = _error_payload(
            command=command,
            stage="assets",
            inputs=inputs,
            exc=ValueError(f"unsupported workflow stage: {stage}"),
            code="unsupported_stage",
        )
        emit_response(payload, as_json=as_json)
        raise SystemExit(1)

    try:
        manifest_file = _require_manifest(manifest_path)
        load_manifest(manifest_file)
        result = run_assets(
            manifest_file,
            jobs=jobs,
            run_prompts=run_prompts,
            run_game_dev=False,
            auto_fix=auto_fix,
        )
        summary = summarize_manifest(load_manifest(manifest_file))
        status, next_action = classify_runner_state(summary, result)
        failures = manifest_failures(summary)
        if not result.get("ok") and not failures:
            failures = [
                make_failure(
                    "run_failed",
                    str(result.get("message") or "workflow run failed"),
                )
            ]
        payload = build_response(
            command=command,
            ok=bool(result.get("ok")),
            stage="assets",
            status=status,
            next_action=next_action,
            inputs=inputs,
            outputs=[_path_input(manifest_file)],
            summary={
                "runner": {
                    "stopped_reason": result.get("stopped_reason"),
                    "repair_rounds": result.get("repair_rounds"),
                    "complete": result.get("complete"),
                    "paused": result.get("paused"),
                    "blocked": result.get("blocked"),
                    "run_exit_code": result.get("run_exit_code"),
                },
                "manifest": summary,
            },
            failures=failures,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        payload = _error_payload(command=command, stage="assets", inputs=inputs, exc=exc)

    emit_response(payload, as_json=as_json)
    if not payload["ok"]:
        raise SystemExit(1)


@workflow_group.command("resume")
@click.option("--manifest", "manifest_path", required=True, type=click.Path(path_type=Path))
@click.option("--task-id", "task_id", required=True)
@click.option("--recraft-prompt", is_flag=True, default=False)
@click.option("--json", "as_json", is_flag=True, help="Print one stable JSON object.")
def resume_cmd(
    manifest_path: Path,
    task_id: str,
    recraft_prompt: bool,
    as_json: bool,
) -> None:
    """Delegate failed-task recovery to the existing retry runner."""
    command = "resume"
    inputs = {
        "manifest": str(manifest_path),
        "task_id": task_id,
        "recraft_prompt": recraft_prompt,
    }
    try:
        manifest_file = _require_manifest(manifest_path)
        result = retry_asset(
            manifest_file,
            task_id=task_id,
            recraft_prompt=recraft_prompt,
        )
        summary = summarize_manifest(load_manifest(manifest_file))
        status, next_action = classify_runner_state(summary, result)
        failures = manifest_failures(summary)
        if not result.get("ok") and not failures:
            failures = [
                make_failure(
                    "resume_failed",
                    str(result.get("message") or "workflow resume failed"),
                )
            ]
        payload = build_response(
            command=command,
            ok=bool(result.get("ok")),
            stage="assets",
            status=status,
            next_action=next_action,
            inputs=inputs,
            outputs=[_path_input(manifest_file)],
            summary={
                "runner": {
                    "asset": result.get("asset"),
                    "reset_task_id": result.get("reset_task_id"),
                    "recraft_prompt": result.get("recraft_prompt"),
                    "run_prompts": result.get("run_prompts"),
                    "reset_ids": result.get("reset_ids"),
                    "run_exit_code": result.get("run_exit_code"),
                    "complete": result.get("complete"),
                    "paused": result.get("paused"),
                    "blocked": result.get("blocked"),
                },
                "manifest": summary,
            },
            failures=failures,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        payload = _error_payload(command=command, stage="assets", inputs=inputs, exc=exc)

    emit_response(payload, as_json=as_json)
    if not payload["ok"]:
        raise SystemExit(1)


@workflow_group.command("status")
@click.option("--manifest", "manifest_path", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print one stable JSON object.")
def status_cmd(manifest_path: Path, as_json: bool) -> None:
    """Read manifest state without reconcile or disk writes."""
    command = "status"
    inputs = {"manifest": str(manifest_path)}
    try:
        manifest_file = _require_manifest(manifest_path)
        summary = summarize_manifest(load_manifest(manifest_file))
        status, next_action = classify_manifest_state(summary)
        payload = build_response(
            command=command,
            ok=True,
            stage="assets",
            status=status,
            next_action=next_action,
            inputs=inputs,
            summary={"manifest": summary},
            failures=manifest_failures(summary),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        payload = _error_payload(command=command, stage="assets", inputs=inputs, exc=exc)

    emit_response(payload, as_json=as_json)
    if not payload["ok"]:
        raise SystemExit(1)


@workflow_group.command("validate")
@click.option("--brief", "brief_path", required=True, type=click.Path(path_type=Path))
@click.option("--production", "production_path", default=None, type=click.Path(path_type=Path))
@click.option("--manifest", "manifest_path", default=None, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print one stable JSON object.")
def validate_cmd(
    brief_path: Path,
    production_path: Path | None,
    manifest_path: Path | None,
    as_json: bool,
) -> None:
    """Validate Brief and optional production/manifest without writes."""
    command = "validate"
    stage = "design"
    inputs = {
        "brief": str(brief_path),
        "production": str(production_path) if production_path else None,
        "manifest": str(manifest_path) if manifest_path else None,
    }
    failures: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"brief": {}, "production": None, "manifest": None}
    manifest_summary: dict[str, Any] | None = None
    try:
        brief = _require_brief(brief_path)
        project, assets, graphs = load_brief_full(brief)
        brief_errors = audit_brief_for_export(
            project, assets, animation_graphs=graphs, brief_path=brief
        )
        failures.extend(_validation_failures(brief_errors, "brief_invalid"))
        summary["brief"] = {
            "title": project.title,
            "asset_count": len(assets),
            "animation_graph_count": len(graphs),
            "valid": not brief_errors,
        }

        if production_path is not None:
            production_file = production_path.expanduser().resolve()
            if not production_file.is_file():
                failures.append(
                    make_failure(
                        "production_missing",
                        f"production not found: {production_file}",
                    )
                )
            else:
                production = load_production(production_file)
                production_errors = validate_production(production, brief_path=brief)
                failures.extend(
                    _validation_failures(production_errors, "production_invalid")
                )
                summary["production"] = {
                    "path": str(production_file),
                    "valid": not production_errors,
                    "errors": production_errors,
                }

        if manifest_path is not None:
            manifest_file = manifest_path.expanduser().resolve()
            if not manifest_file.is_file():
                failures.append(
                    make_failure(
                        "manifest_missing",
                        f"manifest not found: {manifest_file}",
                    )
                )
            else:
                manifest = load_manifest(manifest_file)
                manifest_errors = manifest_validation_errors(manifest)
                failures.extend(
                    _validation_failures(manifest_errors, "manifest_invalid")
                )
                manifest_summary = summarize_manifest(manifest)
                state, next_state_action = classify_manifest_state(manifest_summary)
                summary["manifest"] = {
                    "path": str(manifest_file),
                    "valid": not manifest_errors,
                    "errors": manifest_errors,
                    "state": state,
                    "next_action": next_state_action,
                    "summary": manifest_summary,
                }

        valid = not failures
        if not valid:
            status, next_action = "blocked", "fix_input"
        elif manifest_summary is not None:
            status, next_action = classify_manifest_state(manifest_summary)
        else:
            status, next_action = "done", "derive_production"
        payload = build_response(
            command=command,
            ok=valid,
            stage=stage,
            status=status,
            next_action=next_action,
            inputs=inputs,
            summary=summary,
            failures=failures,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        payload = _error_payload(command=command, stage=stage, inputs=inputs, exc=exc)

    emit_response(payload, as_json=as_json)
    if not payload["ok"]:
        raise SystemExit(1)


__all__ = ["workflow_group"]
