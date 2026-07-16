"""CLI — project progress ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from progress import (
    append_memory,
    default_progress_path,
    init_progress,
    load_progress,
    save_progress,
    update_phase,
    update_task_status,
    update_validation_layer,
)


def register_project_commands(cli_group: click.Group) -> None:
    @cli_group.group("project")
    def project_group() -> None:
        """Project-wide progress and resume state."""

    @project_group.group("progress")
    def progress_group() -> None:
        """Task + validation progress for agent resume."""

    @progress_group.command("init")
    @click.option("--brief", "brief_path", default=None, type=click.Path(exists=True, path_type=Path))
    @click.option(
        "--production",
        "production_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--project", "project_path", default=None, type=click.Path(path_type=Path))
    @click.option("-o", "--output", "output_path", default=None, type=click.Path(path_type=Path))
    def init_cmd(
        brief_path: Path | None,
        production_path: Path,
        project_path: Path | None,
        output_path: Path | None,
    ) -> None:
        """Create progress.json from production.godot_tasks."""
        try:
            data = init_progress(
                brief_path=brief_path,
                production_path=production_path,
                project_path=project_path,
            )
            out = output_path or default_progress_path(
                brief_path=brief_path,
                production_path=production_path,
            )
            path = save_progress(data, out)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(str(path))

    @progress_group.command("show")
    @click.option(
        "--progress",
        "progress_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    def show_cmd(progress_path: Path, as_json: bool) -> None:
        """Show progress summary or full JSON."""
        try:
            data = load_progress(progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(data, ensure_ascii=False, indent=2))
            return
        meta = data.get("progress_meta") or {}
        click.echo(f"slug: {meta.get('slug')}")
        click.echo(f"project: {meta.get('project_path')}")
        phases = data.get("phases") or {}
        click.echo(f"scaffold: {(phases.get('scaffold') or {}).get('status')}")
        val = phases.get("validation") or {}
        click.echo(f"validate: {val.get('validate')}  playtest: {val.get('playtest')}")
        click.echo("godot_tasks:")
        for task in phases.get("godot_tasks") or []:
            if isinstance(task, dict):
                click.echo(f"  [{task.get('status')}] {task.get('id')}: {task.get('title')}")

    @progress_group.command("task")
    @click.option("--progress", "progress_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option("--id", "task_id", required=True)
    @click.option(
        "--status",
        required=True,
        type=click.Choice(["pending", "in_progress", "done", "failed", "blocked"]),
    )
    @click.option("--error", default=None, help="Failure note when status=failed.")
    def task_cmd(progress_path: Path, task_id: str, status: str, error: str | None) -> None:
        """Update a godot_task status (typically after harness/validate)."""
        try:
            data = load_progress(progress_path)
            update_task_status(data, task_id, status, error=error)
            save_progress(data, progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(f"OK task {task_id} -> {status}")

    @progress_group.command("validation")
    @click.option("--progress", "progress_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option("--layer", required=True, type=click.Choice(["validate", "unit", "playtest", "regression"]))
    @click.option("--status", required=True, type=click.Choice(["pass", "fail", "not_run", "inconclusive"]))
    @click.option("--error", default=None)
    @click.option("--report", "report_path", default=None, type=click.Path(path_type=Path))
    def validation_cmd(
        progress_path: Path,
        layer: str,
        status: str,
        error: str | None,
        report_path: Path | None,
    ) -> None:
        """Record validation layer result."""
        try:
            data = load_progress(progress_path)
            update_validation_layer(
                data,
                layer,
                status,
                error=error,
                report_path=str(report_path.resolve()) if report_path else None,
            )
            save_progress(data, progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(f"OK validation.{layer} -> {status}")

    @progress_group.command("note")
    @click.option("--progress", "progress_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.argument("message")
    def note_cmd(progress_path: Path, message: str) -> None:
        """Append a memory note for the next agent session."""
        try:
            data = load_progress(progress_path)
            append_memory(data, message)
            save_progress(data, progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo("OK")
