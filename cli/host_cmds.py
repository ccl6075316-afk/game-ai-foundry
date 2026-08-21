"""CLI: host bridge commands for single-asset / batch pipeline repair."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from host.retry_asset import retry_asset
from host.run_assets import run_assets


@click.group("host")
def host_group() -> None:
    """Host bridge — thin wrappers for GUI and safe_cli pipeline repair."""


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
            auto_fix=auto_fix,
        )
    except (ValueError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("ok"):
        sys.exit(result.get("run_exit_code") or 1)
