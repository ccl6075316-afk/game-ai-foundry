"""CLI commands for pipeline DAG scheduling."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from pipeline_manifest import (
    TASK_DONE,
    TASK_FAILED,
    TASK_RUNNING,
    build_manifest,
    load_manifest,
    merge_manifest_status,
    ready_tasks,
    reconcile_manifest,
    record_task,
    save_manifest,
    status_summary,
)
from pipeline_runner import reset_task_cascade, run_pipeline


@click.group("pipeline")
def pipeline_group() -> None:
    """Brief → DAG manifest for concurrent asset production."""


@pipeline_group.command("plan")
@click.option(
    "--brief",
    "brief_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Project brief JSON (communication phase output).",
)
@click.option(
    "-o",
    "--output",
    "manifest_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Write manifest JSON (e.g. pipeline/manifest.json).",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Asset output directory (default: output/<brief-stem>).",
)
@click.option(
    "--plans-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Plan handoff directory (default: plans/).",
)
@click.option(
    "--sprite-frames",
    default=8,
    show_default=True,
    type=int,
    help="Default sprite frame count for video animations.",
)
@click.option(
    "--merge",
    "merge_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Preserve task status from an existing manifest.",
)
def plan_cmd(
    brief_path: Path,
    manifest_path: Path,
    output_dir: Path | None,
    plans_dir: Path | None,
    sprite_frames: int,
    merge_path: Path | None,
) -> None:
    """Build task DAG from brief (what to generate, animation deps, layers)."""
    try:
        manifest = build_manifest(
            brief_path,
            output_dir=output_dir,
            plans_dir=plans_dir,
            sprite_frames_default=sprite_frames,
        )
        if merge_path is not None:
            merge_manifest_status(manifest, load_manifest(merge_path))
        save_manifest(manifest_path, manifest)
        summary = status_summary(manifest)
        click.echo(str(manifest_path.resolve()))
        click.echo(
            json.dumps(
                {
                    "tasks": summary["total"],
                    "layers": max((t.get("layer", 0) for t in manifest["tasks"]), default=0),
                    "ready": summary["ready_ids"],
                },
                ensure_ascii=False,
            )
        )
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("status")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--json", "as_json", is_flag=True, help="Print full JSON summary.")
def status_cmd(manifest_path: Path, as_json: bool) -> None:
    """Summarize manifest progress and list ready tasks."""
    try:
        manifest = load_manifest(manifest_path)
        summary = status_summary(manifest)
        if as_json:
            summary["ready_tasks"] = ready_tasks(manifest)
            click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
            return
        click.echo(f"brief: {summary['brief']}")
        click.echo(f"tasks: {summary['total']}  counts: {summary['counts']}")
        click.echo(f"ready ({summary['ready_count']}): {', '.join(summary['ready_ids']) or '-'}")
        if summary["failed_ids"]:
            click.echo(f"failed: {', '.join(summary['failed_ids'])}")
        if summary["done"]:
            click.echo("pipeline: complete")
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("ready")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--role",
    default=None,
    help="Filter ready tasks by agent role (e.g. image-generator).",
)
@click.option("--json", "as_json", is_flag=True, help="Print task objects as JSON array.")
def ready_cmd(manifest_path: Path, role: str | None, as_json: bool) -> None:
    """List tasks ready to run (dependencies satisfied, status pending)."""
    try:
        manifest = load_manifest(manifest_path)
        tasks = ready_tasks(manifest)
        if role:
            tasks = [t for t in tasks if t.get("role") == role]
        if as_json:
            click.echo(json.dumps(tasks, ensure_ascii=False, indent=2))
            return
        for task in tasks:
            click.echo(f"{task['id']}\t{task['role']}\t{task['command']}")
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("record")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--task-id", required=True, help="Task id from manifest (e.g. knight.image.generate).")
@click.option(
    "--status",
    type=click.Choice([TASK_RUNNING, TASK_DONE, TASK_FAILED], case_sensitive=False),
    required=True,
)
@click.option("--exit-code", type=int, default=None, help="Shell exit code from the task command.")
@click.option("--result-json", default=None, help="Inline JSON result payload.")
@click.option(
    "--result-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Read result JSON from file (e.g. captured stdout).",
)
def record_cmd(
    manifest_path: Path,
    task_id: str,
    status: str,
    exit_code: int | None,
    result_json: str | None,
    result_file: Path | None,
) -> None:
    """Update task status after a worker finishes (orchestrator calls this)."""
    try:
        manifest = load_manifest(manifest_path)
        result: dict | None = None
        if result_file is not None:
            result = json.loads(result_file.read_text(encoding="utf-8"))
        elif result_json:
            result = json.loads(result_json)
        if exit_code is not None:
            payload = dict(result or {})
            payload["exit_code"] = exit_code
            if exit_code != 0 and status == TASK_DONE:
                status = TASK_FAILED
            result = payload
        record_task(manifest, task_id, status=status, result=result)
        save_manifest(manifest_path, manifest)
        click.echo(json.dumps(status_summary(manifest), ensure_ascii=False))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("reconcile")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
def reconcile_cmd(manifest_path: Path) -> None:
    """Mark pending tasks done when artifact files already exist on disk."""
    try:
        manifest = load_manifest(manifest_path)
        updated = reconcile_manifest(manifest)
        save_manifest(manifest_path, manifest)
        summary = status_summary(manifest)
        click.echo(
            json.dumps(
                {"reconciled": updated, **summary},
                ensure_ascii=False,
                indent=2,
            )
        )
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("show")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.argument("task_id")
def show_cmd(manifest_path: Path, task_id: str) -> None:
    """Print one task entry from the manifest."""
    try:
        manifest = load_manifest(manifest_path)
        from pipeline_manifest import task_by_id

        click.echo(json.dumps(task_by_id(manifest, task_id), ensure_ascii=False, indent=2))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("run")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--jobs",
    default=4,
    show_default=True,
    type=int,
    help="Max parallel subprocesses per wave.",
)
@click.option(
    "--run-prompts",
    is_flag=True,
    help="Include prompt.craft (LLM). Default: skip if plan file exists.",
)
@click.option(
    "--skip-roles",
    default=None,
    help="Comma-separated roles to skip (default: prompt-crafter when not --run-prompts).",
)
@click.option(
    "--stop-on-fail/--no-stop-on-fail",
    default=True,
    help="Pause when a task exits non-zero (exit 2 = validation).",
)
@click.option(
    "--timeout",
    "task_timeout",
    default=1800.0,
    show_default=True,
    type=float,
    help="Per-task subprocess timeout in seconds.",
)
@click.option("--dry-run", is_flag=True, help="Print wave without executing commands.")
def run_cmd(
    manifest_path: Path,
    jobs: int,
    run_prompts: bool,
    skip_roles: str | None,
    stop_on_fail: bool,
    task_timeout: float,
    dry_run: bool,
) -> None:
    """Run ready manifest tasks via subprocess (no Hermes). Default skips prompt.craft."""
    skip: set[str] | None = None
    if skip_roles:
        skip = {r.strip() for r in skip_roles.split(",") if r.strip()}

    def _on_start(task: dict) -> None:
        click.echo(f"→ {task['id']}", err=True)

    def _on_finish(outcome) -> None:
        click.echo(
            f"  {outcome.task_id}: exit {outcome.exit_code} → {outcome.status}",
            err=True,
        )

    try:
        result = run_pipeline(
            manifest_path,
            jobs=jobs,
            skip_roles=skip,
            run_prompts=run_prompts,
            stop_on_fail=stop_on_fail,
            task_timeout=task_timeout,
            dry_run=dry_run,
            on_task_start=_on_start,
            on_task_finish=_on_finish,
        )
        payload = {
            "complete": result.complete,
            "paused": result.paused,
            "blocked": result.blocked,
            "message": result.message,
            "summary": result.summary,
        }
        if result.last_outcome:
            payload["last_task"] = result.last_outcome.task_id
            payload["last_exit_code"] = result.last_outcome.exit_code
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        if result.blocked or result.paused:
            sys.exit(2 if result.paused else 1)
        if not result.complete and not dry_run:
            sys.exit(1)
    except (ValueError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("reset")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--task-id", required=True, help="Task to reset to pending.")
@click.option(
    "--cascade/--no-cascade",
    default=True,
    help="Also reset downstream dependents.",
)
def reset_cmd(manifest_path: Path, task_id: str, cascade: bool) -> None:
    """Reset task(s) to pending after prompt fix or manual retry."""
    try:
        manifest = load_manifest(manifest_path)
        if cascade:
            reset_ids = reset_task_cascade(manifest, task_id)
        else:
            from pipeline_runner import reset_task

            reset_task(manifest, task_id)
            reset_ids = [task_id]
        save_manifest(manifest_path, manifest)
        click.echo(json.dumps({"reset": reset_ids}, ensure_ascii=False, indent=2))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
