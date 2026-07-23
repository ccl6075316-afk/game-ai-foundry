"""CLI — assets review (list / accept / replace / regenerate-plan)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from asset_review import (
    VALID_SOURCE,
    iter_review_rows,
    replace_local_file,
    row_id_for,
    set_review,
)
from assets_manifest import load_assets_manifest, save_assets_manifest
from pipeline_retry import _pick_reset_task_id, load_manifest_tasks

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLI_DIR = Path(__file__).resolve().parent


def _manifest_rel_for_cli(manifest_path: Path) -> str:
    manifest_path = manifest_path.resolve()
    try:
        return manifest_path.relative_to(_CLI_DIR.resolve()).as_posix()
    except ValueError:
        try:
            rel = manifest_path.relative_to(_REPO_ROOT.resolve())
            return f"../{rel.as_posix()}"
        except ValueError:
            return manifest_path.as_posix()


def _pick_regenerate_task_id(
    tasks: list[dict[str, Any]],
    asset: str,
    *,
    item: str | None = None,
) -> str | None:
    if not item:
        return _pick_reset_task_id(tasks, asset)

    item_l = str(item).strip().lower()
    asset_l = str(asset).strip().lower()
    suffix = f"__{item_l}"
    matched: list[dict[str, Any]] = []
    for task in tasks:
        task_asset = str(task.get("asset") or "").strip().lower()
        if task_asset and task_asset != asset_l:
            continue
        aid = str(task.get("asset_id") or "").lower()
        artifacts = task.get("artifacts") if isinstance(task.get("artifacts"), dict) else {}
        slug = str(artifacts.get("kit_item_slug") or "").strip().lower()
        if slug == item_l or suffix in aid or aid.endswith(suffix):
            matched.append(task)
    if not matched:
        return None

    failed = [t for t in matched if str(t.get("status") or "") == "failed"]
    pool = failed or matched
    for task in pool:
        if str(task.get("step") or "") == "image.generate":
            return str(task.get("id") or "") or None
    for task in pool:
        tid = str(task.get("id") or "")
        if ".image.generate" in tid:
            return tid or None
    return str(pool[0].get("id") or "") or None


def build_regenerate_plan(
    pipeline_manifest: Path,
    asset: str,
    *,
    item: str | None = None,
    jobs: int = 4,
) -> dict[str, Any]:
    tasks = load_manifest_tasks(pipeline_manifest)
    reset_task_id = _pick_regenerate_task_id(tasks, asset, item=item)
    if not reset_task_id:
        target = f"asset {asset!r}" + (f" item {item!r}" if item else "")
        raise ValueError(
            f"no reset_task_id for {target}; "
            "cannot regenerate without a matching pipeline task"
        )
    manifest_rel = _manifest_rel_for_cli(pipeline_manifest)
    commands = [
        "python gamefactory.py pipeline reset "
        f"--manifest {manifest_rel} --task-id {reset_task_id} --cascade",
        f"python gamefactory.py pipeline run --manifest {manifest_rel} --jobs {jobs}",
    ]
    return {"reset_task_id": reset_task_id, "commands": commands}


def register_assets_commands(cli_group: click.Group) -> None:
    @cli_group.group("assets")
    def assets_group() -> None:
        """Assets manifest — review rows, accept, replace, regenerate plan."""

    @assets_group.group("review")
    def review_group() -> None:
        """Soft review annotations on assets-manifest rows."""

    @review_group.command("list")
    @click.option(
        "--manifest",
        "manifest_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Path to assets-manifest.json.",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print rows as JSON.")
    def list_cmd(manifest_path: Path, as_json: bool) -> None:
        """List review rows expanded from assets-manifest."""
        try:
            manifest = load_assets_manifest(manifest_path)
            rows = iter_review_rows(manifest)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(rows, ensure_ascii=False, indent=2))
            return

        if not rows:
            click.echo("No assets in manifest.")
            return
        for row in rows:
            review = row.get("review") or {}
            path = row.get("canonical_path_repo") or "-"
            click.echo(
                f"{row.get('row_id')}\t{review.get('status', 'pending')}\t{path}"
            )

    @review_group.command("accept")
    @click.option(
        "--manifest",
        "manifest_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--asset", "asset_name", required=True, help="Asset name from brief.")
    @click.option("--item", "kit_item", default=None, help="icon_kit item slug.")
    @click.option("--json", "as_json", is_flag=True)
    def accept_cmd(
        manifest_path: Path,
        asset_name: str,
        kit_item: str | None,
        as_json: bool,
    ) -> None:
        """Mark a review row as accepted (soft annotation only)."""
        try:
            manifest = load_assets_manifest(manifest_path)
            review = set_review(
                manifest,
                asset_name=asset_name,
                kit_item_slug=kit_item,
                status="accepted",
            )
            save_assets_manifest(manifest_path, manifest)
            payload = {
                "ok": True,
                "row_id": row_id_for(asset_name, kit_item),
                "review": review,
            }
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        click.echo(f"accepted {payload['row_id']}")

    @review_group.command("replace")
    @click.option(
        "--manifest",
        "manifest_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--asset", "asset_name", required=True)
    @click.option("--item", "kit_item", default=None, help="icon_kit item slug.")
    @click.option(
        "--file",
        "source_file",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Absolute path to replacement image.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def replace_cmd(
        manifest_path: Path,
        asset_name: str,
        kit_item: str | None,
        source_file: Path,
        as_json: bool,
    ) -> None:
        """Copy a local file over the row canonical path and mark replaced."""
        try:
            result = replace_local_file(
                manifest_path,
                asset_name=asset_name,
                kit_item_slug=kit_item,
                source_abs=source_file,
                repo_root=_REPO_ROOT,
            )
        except (ValueError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
            return
        click.echo(f"replaced {result['row_id']} -> {result['path_repo']}")

    @review_group.command("mark-replaced")
    @click.option(
        "--manifest",
        "manifest_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--asset", "asset_name", required=True, help="Asset name from brief.")
    @click.option("--item", "kit_item", default=None, help="icon_kit item slug.")
    @click.option(
        "--source",
        "source",
        default="regenerate",
        type=click.Choice(sorted(VALID_SOURCE), case_sensitive=False),
        show_default=True,
        help="Review source for the replaced annotation.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def mark_replaced_cmd(
        manifest_path: Path,
        asset_name: str,
        kit_item: str | None,
        source: str,
        as_json: bool,
    ) -> None:
        """Mark a review row as replaced (soft annotation; no file copy)."""
        try:
            manifest = load_assets_manifest(manifest_path)
            assets = manifest.get("assets") if isinstance(manifest.get("assets"), dict) else {}
            if asset_name not in assets:
                raise ValueError(f"unknown asset: {asset_name!r}")
            review = set_review(
                manifest,
                asset_name=asset_name,
                kit_item_slug=kit_item,
                status="replaced",
                source=source,
            )
            save_assets_manifest(manifest_path, manifest)
            payload = {
                "ok": True,
                "row_id": row_id_for(asset_name, kit_item),
                "review": review,
            }
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        click.echo(f"replaced {payload['row_id']} source={source}")

    @review_group.command("regenerate-plan")
    @click.option(
        "--pipeline-manifest",
        "pipeline_manifest",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Pipeline manifest JSON (not assets-manifest).",
    )
    @click.option("--asset", "asset_name", required=True)
    @click.option("--item", "kit_item", default=None, help="icon_kit item slug.")
    @click.option("--jobs", default=4, show_default=True, type=int)
    @click.option("--json", "as_json", is_flag=True, help="Print plan JSON (default).")
    def regenerate_plan_cmd(
        pipeline_manifest: Path,
        asset_name: str,
        kit_item: str | None,
        jobs: int,
        as_json: bool,
    ) -> None:
        """Suggest pipeline reset + run commands for regenerating one row."""
        try:
            plan = build_regenerate_plan(
                pipeline_manifest,
                asset_name,
                item=kit_item,
                jobs=jobs,
            )
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        click.echo(json.dumps(plan, ensure_ascii=False, indent=2))
