"""CLI: deterministic repair bridge commands for pipeline repair."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from host.retry_asset import retry_asset
from host.run_assets import run_assets
from host.workflow_run import run_workflow


@click.group("host")
def host_group() -> None:
    """Deterministic repair bridge — wrappers for pipeline repair."""


@host_group.command("retry-asset")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Pipeline manifest JSON.",
)
@click.option("--asset", default=None, help="Asset name to repair.")
@click.option("--task-id", default=None, help="Explicit task id to reset (overrides asset pick).")
@click.option(
    "--recraft-prompt",
    is_flag=True,
    default=False,
    help="Force prompt.craft via pipeline run --run-prompts after reset.",
)
@click.option("--jobs", default=4, show_default=True, type=int, help="Parallel pipeline jobs.")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
def retry_asset_cmd(
    manifest_path: Path,
    asset: str | None,
    task_id: str | None,
    recraft_prompt: bool,
    jobs: int,
    as_json: bool,
) -> None:
    """Reset one asset's failed task (cascade) and re-run the pipeline."""
    try:
        result = retry_asset(
            manifest_path,
            asset=asset,
            task_id=task_id,
            recraft_prompt=recraft_prompt,
            jobs=jobs,
        )
    except (ValueError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("ok"):
        sys.exit(result.get("run_exit_code") or 1)


@host_group.command("run-assets")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Pipeline manifest JSON.",
)
@click.option(
    "--run-prompts",
    is_flag=True,
    default=False,
    help="Include prompt.craft tasks in pipeline run.",
)
@click.option(
    "--run-game-dev",
    is_flag=True,
    default=False,
    help="Run Pass 4 godot.dev-context (writes programmer handoff).",
)
@click.option(
    "--auto-fix/--no-auto-fix",
    default=True,
    show_default=True,
    help="Diagnose and execute whitelisted fix_commands after failures.",
)
@click.option("--jobs", default=4, show_default=True, type=int, help="Parallel pipeline jobs.")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
def run_assets_cmd(
    manifest_path: Path,
    run_prompts: bool,
    run_game_dev: bool,
    auto_fix: bool,
    jobs: int,
    as_json: bool,
) -> None:
    """Run the full pipeline; optionally auto-repair validation/config failures."""
    try:
        result = run_assets(
            manifest_path,
            jobs=jobs,
            run_prompts=run_prompts,
            run_game_dev=run_game_dev,
            auto_fix=auto_fix,
        )
    except (ValueError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("ok"):
        sys.exit(result.get("run_exit_code") or 1)


@host_group.command("workflow-run")
@click.option("--brief", "brief_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--production", "production_path", default=None, type=click.Path(path_type=Path))
@click.option("--manifest", "manifest_path", default=None, type=click.Path(path_type=Path))
@click.option("--stage", default="assets", show_default=True)
@click.option("--auto-fix/--no-auto-fix", default=True, show_default=True)
@click.option("--run-prompts", is_flag=True, default=False)
@click.option("--jobs", default=4, show_default=True, type=int)
@click.option("--auto-resume/--no-auto-resume", default=True, show_default=True)
@click.option("--max-resumes", default=3, show_default=True, type=int)
@click.option("--dry-run", is_flag=True, default=False, help="Only run context/validate.")
@click.option("--i-confirm", is_flag=True, default=False, help="One user confirmation for writes/generation.")
@click.option(
    "--detach",
    is_flag=True,
    default=False,
    help="Detach assets run; return next_action=poll with job_id (skip in-process auto-resume).",
)
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
def workflow_run_cmd(
    brief_path: Path,
    production_path: Path | None,
    manifest_path: Path | None,
    stage: str,
    auto_fix: bool,
    run_prompts: bool,
    jobs: int,
    auto_resume: bool,
    max_resumes: int,
    dry_run: bool,
    i_confirm: bool,
    detach: bool,
    as_json: bool,
) -> None:
    """Run the external-agent workflow as one auditable chain."""
    result = run_workflow(
        brief_path,
        production_path=production_path,
        manifest_path=manifest_path,
        stage=stage,
        auto_fix=auto_fix,
        run_prompts=run_prompts,
        jobs=jobs,
        auto_resume=auto_resume,
        max_resumes=max_resumes,
        dry_run=dry_run,
        i_confirm=i_confirm,
        detach=detach,
    )
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"{result['command']}: {result['status']} -> {result['next_action']}")
        for failure in result.get("failures") or []:
            click.echo(f"failure[{failure['kind']}]: {failure.get('message') or failure['code']}", err=True)
    if not result.get("ok"):
        sys.exit(1)
