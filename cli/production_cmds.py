"""CLI — production doc derive / validate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from production import (
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
