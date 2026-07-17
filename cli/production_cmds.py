"""CLI — production doc derive / validate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from production import (
    apply_production_delta,
    create_production_delta,
    default_delta_path,
    default_production_path,
    derive_production,
    load_production,
    save_production,
    validate_production,
)


def register_production_commands(cli_group: click.Group) -> None:
    @cli_group.group("production")
    def production_group() -> None:
        """Engineering blueprint — derive from brief, validate for scaffold/code."""

    @production_group.command("derive")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Frozen brief JSON (post export).",
    )
    @click.option(
        "-o",
        "--output",
        "output_path",
        default=None,
        type=click.Path(path_type=Path),
        help="Write production JSON (default: plans/production_<brief>.json).",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print full JSON to stdout.")
    @click.option(
        "--validate/--no-validate",
        default=True,
        help="Run validate after derive (default: validate).",
    )
    def derive_cmd(
        brief_path: Path,
        output_path: Path | None,
        as_json: bool,
        validate: bool,
    ) -> None:
        """Derive production.json engineering blueprint from frozen brief."""
        try:
            data = derive_production(brief_path)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if validate:
            errors = validate_production(data, brief_path=brief_path)
            if errors:
                click.echo("Derived production failed validation:", err=True)
                for err in errors:
                    click.echo(f"  - {err}", err=True)
                sys.exit(1)

        out = output_path or default_production_path(brief_path)
        path = save_production(data, out)

        if as_json:
            click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            doc = data.get("production_doc") or {}
            meta = data.get("production_meta") or {}
            click.echo(f"production: {path}")
            click.echo(f"  genre_preset: {meta.get('genre_preset')}")
            click.echo(f"  godot_tasks: {len(doc.get('godot_tasks') or [])}")
            click.echo(f"  main_scene: {(doc.get('scaffold') or {}).get('main_scene')}")

    @production_group.command("validate")
    @click.option(
        "--production",
        "production_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="production.json to validate.",
    )
    @click.option(
        "--brief",
        "brief_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
        help="Optional brief for cross-check.",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print result as JSON.")
    def validate_cmd(
        production_path: Path,
        brief_path: Path | None,
        as_json: bool,
    ) -> None:
        """Validate production.json schema and optional brief alignment."""
        try:
            data = load_production(production_path)
            if brief_path is None:
                meta = data.get("production_meta") or {}
                bp = meta.get("brief_path")
                if bp and Path(bp).is_file():
                    brief_path = Path(bp)
            errors = validate_production(data, brief_path=brief_path)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {
            "ok": not errors,
            "production": str(production_path.resolve()),
            "errors": errors,
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        elif errors:
            click.echo("Invalid production:", err=True)
            for err in errors:
                click.echo(f"  - {err}", err=True)
        else:
            click.echo(f"OK — {production_path.resolve()}")

        if errors:
            sys.exit(1)

    @production_group.command("show")
    @click.option(
        "--production",
        "production_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True, help="Print full document.")
    def show_cmd(production_path: Path, as_json: bool) -> None:
        """Summarize production doc (tasks, scenes, validation)."""
        try:
            data = load_production(production_path)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(data, ensure_ascii=False, indent=2))
            return

        doc = data.get("production_doc") or {}
        meta = data.get("production_meta") or {}
        click.echo(f"title: {doc.get('title')}")
        click.echo(f"genre: {doc.get('genre')} (preset: {meta.get('genre_preset')})")
        click.echo(f"main_scene: {(doc.get('scaffold') or {}).get('main_scene')}")
        click.echo("scenes:")
        for scene in doc.get("scenes") or []:
            if isinstance(scene, dict):
                click.echo(f"  - {scene.get('path')} ({scene.get('role')})")
        click.echo("godot_tasks:")
        for task in doc.get("godot_tasks") or []:
            if isinstance(task, dict):
                deps = task.get("depends_on") or []
                dep_s = f" deps={deps}" if deps else ""
                click.echo(f"  - [{task.get('status', '?')}] {task.get('id')}: {task.get('title')}{dep_s}")
        val = doc.get("validation") or {}
        click.echo("acceptance_criteria:")
        for c in val.get("acceptance_criteria") or []:
            click.echo(f"  - {c}")

    @production_group.command("delta")
    @click.option("--change-id", required=True, help="Stable id, e.g. 002-add-double-jump")
    @click.option("--intent", "user_intent", required=True, help="User Change Request intent")
    @click.option("--asset", "assets", multiple=True, help="Asset task name (repeatable)")
    @click.option("--task", "tasks", multiple=True, help="Godot task title (repeatable)")
    @click.option(
        "--output",
        "output_path",
        type=click.Path(path_type=Path),
        default=None,
        help="Write delta JSON (default: plans/changes/<id>.production-delta.json).",
    )
    @click.option("--json", "as_json", is_flag=True)
    def delta_create_cmd(
        change_id: str,
        user_intent: str,
        assets: tuple[str, ...],
        tasks: tuple[str, ...],
        output_path: Path | None,
        as_json: bool,
    ) -> None:
        """Create a Production Delta file from a Change Request intent."""
        try:
            data = create_production_delta(
                change_id=change_id,
                user_intent=user_intent,
                asset_tasks=list(assets),
                godot_tasks=list(tasks),
            )
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        out = output_path or default_delta_path(change_id)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if as_json:
            click.echo(json.dumps({"ok": True, "path": str(out.resolve()), "delta": data}, ensure_ascii=False, indent=2))
            return
        click.echo(f"production-delta: {out.resolve()}")
        click.echo(f"godot_tasks: {len(data['production_delta']['godot_tasks'])}")

    @production_group.command("apply-delta")
    @click.option(
        "--delta",
        "delta_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="production-delta JSON",
    )
    @click.option(
        "--production",
        "production_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Target production.json",
    )
    @click.option("--dry-run", is_flag=True, help="Validate merge without writing")
    @click.option(
        "--progress",
        "progress_path",
        type=click.Path(path_type=Path),
        default=None,
        help="Also sync new godot_tasks into this progress.json",
    )
    @click.option("--json", "as_json", is_flag=True)
    def apply_delta_cmd(
        delta_path: Path,
        production_path: Path,
        dry_run: bool,
        progress_path: Path | None,
        as_json: bool,
    ) -> None:
        """Merge a Production Delta into production.json (append tasks + acceptance)."""
        from progress import load_progress, save_progress, sync_progress_from_production

        try:
            production = load_production(production_path)
            delta = json.loads(delta_path.read_text(encoding="utf-8"))
            if not isinstance(delta, dict):
                raise ValueError("delta must be a JSON object")
            merged = apply_production_delta(production, delta)
            errors = validate_production(merged)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if errors:
            click.echo("Merged production failed validation:", err=True)
            for e in errors:
                click.echo(f"  - {e}", err=True)
            sys.exit(2)
        meta = (merged.get("production_meta") or {}).get("applied_deltas") or []
        last = meta[-1] if meta else {}
        sync_result: dict = {"added": [], "skipped": []}
        if not dry_run:
            save_production(merged, production_path)
            if progress_path:
                try:
                    if progress_path.is_file():
                        prog = load_progress(progress_path)
                    else:
                        from progress import init_progress

                        prog = init_progress(
                            brief_path=None,
                            production_path=production_path,
                        )
                    sync_result = sync_progress_from_production(prog, merged)
                    save_progress(prog, progress_path)
                except (ValueError, OSError, json.JSONDecodeError) as exc:
                    click.echo(f"Warning: progress sync failed: {exc}", err=True)
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "ok": True,
                        "dry_run": dry_run,
                        "production": str(production_path.resolve()),
                        "tasks_added": last.get("tasks_added"),
                        "change_id": last.get("change_id"),
                        "progress": str(progress_path.resolve()) if progress_path else None,
                        "progress_tasks_added": sync_result.get("added"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        click.echo(f"{'dry-run OK' if dry_run else 'applied'}: {production_path.resolve()}")
        click.echo(f"change_id: {last.get('change_id')}")
        click.echo(f"tasks_added: {last.get('tasks_added')}")
        if progress_path and not dry_run:
            click.echo(f"progress_tasks_added: {sync_result.get('added')}")
