"""Hermes Agent / Codex integration commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from hermes_pack import (
    HERMES_PACKAGES,
    dump_paths_json,
    hermes_source_dir,
    install_hermes_skills,
    sync_hermes_skills,
)


@click.group("hermes")
def hermes_group() -> None:
    """Hermes Agent / Codex skill install and path helpers."""


@hermes_group.command("sync")
@click.option(
    "--output",
    "output_dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Write SKILL.md packages (default: resources/hermes/).",
)
def sync_cmd(output_dir: Path | None) -> None:
    """Regenerate Hermes SKILL.md files from resources/skills/."""
    written = sync_hermes_skills(output_dir)
    for path in written:
        click.echo(str(path.resolve()))


@hermes_group.command("install")
@click.option(
    "--target",
    "install_dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Hermes skills dir (default: ~/.hermes/skills or $HERMES_SKILLS_DIR).",
)
@click.option("--copy", "use_copy", is_flag=True, help="Copy instead of symlink.")
@click.option("--no-sync", is_flag=True, help="Skip regenerating SKILL.md before install.")
def install_cmd(install_dir: Path | None, use_copy: bool, no_sync: bool) -> None:
    """Install game-factory skills into Hermes (~/.hermes/skills by default)."""
    try:
        result = install_hermes_skills(
            install_dir,
            sync_first=not no_sync,
            use_symlink=not use_copy,
        )
    except OSError as exc:
        click.echo(f"Error installing Hermes skills: {exc}", err=True)
        sys.exit(1)

    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@hermes_group.command("paths")
def paths_cmd() -> None:
    """Print repo/cli/config paths for Hermes terminal workdir setup."""
    click.echo(dump_paths_json())


@hermes_group.command("list")
def list_cmd() -> None:
    """List Hermes skill package names and roles."""
    rows = []
    for name, meta in HERMES_PACKAGES.items():
        rows.append(
            {
                "package": name,
                "role": meta.get("role"),
                "description": meta["description"],
            }
        )
    click.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@hermes_group.command("show")
@click.argument("package")
def show_cmd(package: str) -> None:
    """Print generated SKILL.md for a package."""
    if package not in HERMES_PACKAGES:
        click.echo(
            f"Unknown package '{package}'. Known: {', '.join(HERMES_PACKAGES)}",
            err=True,
        )
        sys.exit(1)
    path = hermes_source_dir() / package / "SKILL.md"
    if not path.is_file():
        sync_hermes_skills()
    click.echo(path.read_text(encoding="utf-8"))
