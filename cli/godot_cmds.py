"""Godot project management subcommands for gamefactory CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

# Godot engine path — configurable, falls back to auto-detect
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "resources" / "godot-templates" / "default"


def _load_config() -> dict:
    config_path = Path.home() / ".gamefactory" / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _get_godot_exe() -> str:
    """Resolve Godot executable path."""
    config = _load_config().get("godot", {})
    path = config.get("engine_path")
    if path and Path(path).exists():
        return path
    # Auto-detect
    candidates = [
        r"E:\Godot_v4.6.1-stable_mono_win64\Godot_v4.6.1-stable_mono_win64_console.exe",
        r"E:\Godot_v4.6.1-stable_mono_win64\Godot_v4.6.1-stable_mono_win64.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return "godot"  # fall back to PATH


@click.command("init")
@click.option("--name", required=True, help="Project name.")
@click.option("--path", "project_path", required=True, type=click.Path(path_type=Path),
              help="Project directory (will be created).")
def init_cmd(name: str, project_path: Path) -> None:
    """Initialize a new Godot project from template."""
    if project_path.exists():
        click.echo(f"Error: {project_path} already exists", err=True)
        sys.exit(1)

    shutil.copytree(TEMPLATE_DIR, project_path)

    # Update project name in project.godot
    godot_file = project_path / "project.godot"
    content = godot_file.read_text()
    content = content.replace('config/name="Game"', f'config/name="{name}"')
    godot_file.write_text(content)

    click.echo(str(project_path.resolve()))


@click.command("inject")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Godot project directory.")
@click.option("--file", "file_path", required=True, type=click.Path(path_type=Path),
              help="Target file path relative to project root.")
@click.option("--content", default=None, help="File content. If not provided, reads from stdin.")
def inject_cmd(project_path: Path, file_path: Path, content: str | None) -> None:
    """Write a file into a Godot project."""
    if content is None:
        content = sys.stdin.read()

    target = project_path / file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    click.echo(str(target.resolve()))


@click.command("validate")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Godot project directory.")
def validate_cmd(project_path: Path) -> None:
    """Validate a Godot project using headless syntax check."""
    godot = _get_godot_exe()
    try:
        result = subprocess.run(
            [godot, "--headless", "--path", str(project_path), "--check-only", "--quit"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            click.echo(f"Validation failed:\n{result.stderr}", err=True)
            sys.exit(1)
        click.echo("OK")
    except subprocess.TimeoutExpired:
        click.echo("Error: validation timed out", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo(f"Error: Godot not found at '{godot}'. Set engine_path in config.", err=True)
        sys.exit(1)


@click.command("open")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Godot project directory.")
def open_cmd(project_path: Path) -> None:
    """Open a Godot project in the editor."""
    godot = _get_godot_exe().replace("_console.exe", ".exe")  # use GUI version for editor
    try:
        subprocess.Popen([godot, "--path", str(project_path), "--editor"])
        click.echo(f"Opening {project_path} in Godot...")
    except FileNotFoundError:
        click.echo(f"Error: Godot not found at '{godot}'.", err=True)
        sys.exit(1)


@click.command("export")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Godot project directory.")
@click.option("--target", required=True, type=click.Choice(["html5", "windows", "mac", "linux"]),
              help="Export target platform.")
@click.option("--output", "output_path", required=True, type=click.Path(path_type=Path),
              help="Output directory or file.")
def export_cmd(project_path: Path, target: str, output_path: Path) -> None:
    """Export a Godot project."""
    godot = _get_godot_exe()
    export_name = {
        "html5": "HTML5",
        "windows": "Windows Desktop",
        "mac": "macOS",
        "linux": "Linux/X11",
    }[target]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [godot, "--headless", "--path", str(project_path),
             "--export-release", export_name, str(output_path)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            click.echo(f"Export failed:\n{result.stderr}", err=True)
            sys.exit(1)
        click.echo(str(output_path.resolve()))
    except subprocess.TimeoutExpired:
        click.echo("Error: export timed out", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo(f"Error: Godot not found at '{godot}'.", err=True)
        sys.exit(1)
