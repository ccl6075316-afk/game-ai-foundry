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
    recraft_prompt: bool = False,
) -> str | None:
    if recraft_prompt and not item:
        asset_l = str(asset).strip().lower()
        for task in tasks:
            if str(task.get("step") or "") != "prompt.craft":
                continue
            tid = str(task.get("id") or "")
            task_asset = str(task.get("asset") or "").strip().lower()
            asset_id = str(task.get("asset_id") or "").strip().lower()
            if (
                task_asset == asset_l
                or asset_id == asset_l
                or tid.lower().startswith(f"{asset_l}.")
            ):
                return tid or None
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
    recraft_prompt: bool = False,
) -> dict[str, Any]:
    tasks = load_manifest_tasks(pipeline_manifest)
    reset_task_id = _pick_regenerate_task_id(
        tasks,
        asset,
        item=item,
        recraft_prompt=recraft_prompt,
    )
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


def _targets_from_rows(
    assets_manifest_path: Path,
    row_ids: list[str],
) -> list[tuple[str, str | None]]:
    manifest = load_assets_manifest(assets_manifest_path)
    rows = iter_review_rows(manifest)
    by_id = {str(r.get("row_id") or ""): r for r in rows}
    out: list[tuple[str, str | None]] = []
    seen: set[tuple[str, str | None]] = set()
    for rid in row_ids:
        row = by_id.get(str(rid).strip())
        if not row:
            continue
        asset_name = str(row.get("asset_name") or "").strip()
        if not asset_name:
            continue
        slug = str(row.get("kit_item_slug") or "").strip() or None
        key = (asset_name, slug)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def regenerate_assets_batch(
    pipeline_manifest: Path,
    targets: list[tuple[str, str | None]],
    *,
    jobs: int = 4,
    reset_only: bool = False,
    recraft_prompt: bool = True,
) -> dict[str, Any]:
    """Reset cascade for multiple review rows; optionally run pipeline once."""
    if not targets:
        raise ValueError("no regenerate targets")

    from pipeline_manifest import load_manifest, save_manifest
    from pipeline_runner import reset_task_cascade, run_pipeline

    pipeline_manifest = pipeline_manifest.resolve()
    manifest = load_manifest(pipeline_manifest)
    tasks = load_manifest_tasks(pipeline_manifest)

    reset_task_ids: list[str] = []
    all_reset_ids: list[str] = []
    skipped: list[dict[str, str]] = []

    for asset_name, kit_item in targets:
        tid = _pick_regenerate_task_id(
            tasks,
            asset_name,
            item=kit_item,
            recraft_prompt=recraft_prompt,
        )
        if not tid:
            skipped.append({"asset": asset_name, "item": kit_item or ""})
            continue
        reset_task_ids.append(tid)
        ids = reset_task_cascade(manifest, tid)
        all_reset_ids.extend(ids)

    if not reset_task_ids:
        raise ValueError("no matching pipeline tasks for targets")

    save_manifest(pipeline_manifest, manifest)

    manifest_rel = _manifest_rel_for_cli(pipeline_manifest)
    result: dict[str, Any] = {
        "reset_task_ids": reset_task_ids,
        "reset_ids": all_reset_ids,
        "skipped": skipped,
        "reset_only": reset_only,
        "recraft_prompt": recraft_prompt,
        "targets": [{"asset": a, "item": i or ""} for a, i in targets],
    }

    if reset_only:
        result["ok"] = True
        result["message"] = f"Reset {len(reset_task_ids)} target(s); run pipeline to regenerate."
        return result

    run_prompts = recraft_prompt
    run_result = run_pipeline(
        pipeline_manifest,
        jobs=jobs,
        run_prompts=run_prompts,
    )
    exit_code = 0 if run_result.complete else (2 if run_result.paused else 1)
    result.update(
        {
            "ok": run_result.complete,
            "run_prompts": run_prompts,
            "run_exit_code": exit_code,
            "summary": run_result.summary,
            "message": run_result.message,
            "complete": run_result.complete,
            "paused": run_result.paused,
            "blocked": run_result.blocked,
        }
    )
    return result


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
    @click.option(
        "--recraft-prompt",
        is_flag=True,
        help="Reset from prompt.craft (recommended when brief/spec changed).",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print plan JSON (default).")
    def regenerate_plan_cmd(
        pipeline_manifest: Path,
        asset_name: str,
        kit_item: str | None,
        jobs: int,
        recraft_prompt: bool,
        as_json: bool,
    ) -> None:
        """Suggest pipeline reset + run commands for regenerating one row."""
        try:
            plan = build_regenerate_plan(
                pipeline_manifest,
                asset_name,
                item=kit_item,
                jobs=jobs,
                recraft_prompt=recraft_prompt,
            )
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        click.echo(json.dumps(plan, ensure_ascii=False, indent=2))

    @review_group.command("regenerate-batch")
    @click.option(
        "--pipeline-manifest",
        "pipeline_manifest",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Pipeline manifest JSON.",
    )
    @click.option(
        "--assets-manifest",
        "assets_manifest_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
        help="assets-manifest.json (required when using --row-id).",
    )
    @click.option("--asset", "asset_names", multiple=True, help="Brief asset name (repeatable).")
    @click.option("--item", "kit_items", multiple=True, help="icon_kit slug paired with --asset.")
    @click.option("--row-id", "row_ids", multiple=True, help="Review row_id from assets review list.")
    @click.option("--jobs", default=4, show_default=True, type=int)
    @click.option(
        "--reset-only",
        is_flag=True,
        help="Only reset tasks to pending; do not run pipeline.",
    )
    @click.option(
        "--no-recraft-prompt",
        is_flag=True,
        help="Reset from image.generate instead of prompt.craft.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def regenerate_batch_cmd(
        pipeline_manifest: Path,
        assets_manifest_path: Path | None,
        asset_names: tuple[str, ...],
        kit_items: tuple[str, ...],
        row_ids: tuple[str, ...],
        jobs: int,
        reset_only: bool,
        no_recraft_prompt: bool,
        as_json: bool,
    ) -> None:
        """Reset + optionally run pipeline for multiple assets / review rows."""
        targets: list[tuple[str, str | None]] = []
        if row_ids:
            if assets_manifest_path is None:
                click.echo("Error: --assets-manifest required with --row-id", err=True)
                sys.exit(1)
            try:
                targets.extend(_targets_from_rows(assets_manifest_path, list(row_ids)))
            except (ValueError, json.JSONDecodeError, OSError) as exc:
                click.echo(f"Error: {exc}", err=True)
                sys.exit(1)
        if asset_names:
            items = list(kit_items)
            for idx, asset_name in enumerate(asset_names):
                item = items[idx] if idx < len(items) else None
                item_s = str(item or "").strip() or None
                targets.append((str(asset_name).strip(), item_s))
        if not targets:
            click.echo("Error: provide --row-id and/or --asset", err=True)
            sys.exit(1)
        try:
            result = regenerate_assets_batch(
                pipeline_manifest,
                targets,
                jobs=jobs,
                reset_only=reset_only,
                recraft_prompt=not no_recraft_prompt,
            )
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
            return
        click.echo(
            f"reset {len(result.get('reset_task_ids') or [])} target(s)"
            + (" (pending — run pipeline to regenerate)" if reset_only else "")
        )
