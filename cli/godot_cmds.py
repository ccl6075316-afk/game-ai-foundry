"""Godot project management subcommands for gamefactory CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

from godot_assemble import GodotAssembleError, assemble_from_plan, init_project_from_template
from toolchain_paths import resolve_dotnet, resolve_godot, toolchain_env
from godot_import import GodotImportError, import_sprite_frames
from plan_io import load_godot_handoff

_REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DEFAULT = _REPO_ROOT / "resources" / "godot-templates" / "default"
TEMPLATE_DOTNET = _REPO_ROOT / "resources" / "godot-templates" / "dotnet"


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
    config = _load_config()
    resolved = resolve_godot(config)
    if resolved:
        return resolved
    return "godot"


def _template_dir(template: str) -> Path:
    if template == "dotnet":
        return TEMPLATE_DOTNET
    return TEMPLATE_DEFAULT


@click.command("init")
@click.option("--name", required=True, help="Project name.")
@click.option("--path", "project_path", required=True, type=click.Path(path_type=Path),
              help="Project directory (will be created).")
@click.option(
    "--template",
    type=click.Choice(["dotnet", "default"]),
    default="dotnet",
    show_default=True,
    help="Project template (dotnet = Godot 4 C# / .NET).",
)
def init_cmd(name: str, project_path: Path, template: str) -> None:
    """Initialize a new Godot project from template."""
    if project_path.exists() and any(project_path.iterdir()):
        click.echo(f"Error: {project_path} already exists and is not empty", err=True)
        sys.exit(1)

    try:
        init_project_from_template(project_path, project_name=name, template=template)
    except GodotAssembleError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(str(project_path.resolve()))


@click.command("import-sprites")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Godot project directory.")
@click.option("--asset", required=True, help="Asset / animation id (folder name under assets/sprites/).")
@click.option("--input-dir", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Directory of frame PNGs.")
@click.option("--pattern", default="frame_*.png", show_default=True)
@click.option("--fps", type=float, default=12.0, show_default=True)
@click.option("--animation-name", default=None, help="SpriteFrames animation name (default: asset id).")
@click.option("--loop/--no-loop", default=True)
@click.option(
    "--skip-lead-frames",
    type=int,
    default=0,
    show_default=True,
    help="Drop first N frames (i2v morph from reference still).",
)
@click.option(
    "--skip-lead-ratio",
    type=float,
    default=None,
    help="Drop this fraction of leading frames before sampling (default 0.25).",
)
@click.option(
    "--skip-trail-ratio",
    type=float,
    default=None,
    help="Drop this fraction of trailing frames after trim (default from config).",
)
@click.option(
    "--sample-frames",
    "sample_frames",
    type=int,
    default=None,
    help="After trim, evenly sample to this many frames (brief sprite_frames / config).",
)
@click.option(
    "--pre-trimmed/--no-pre-trimmed",
    default=False,
    help="Input already time-trimmed by split-frames (skip lead/trail drop).",
)
@click.option(
    "--pre-sampled/--no-pre-sampled",
    default=False,
    help="Input already sampled to sprite frame count (skip resample).",
)
@click.option(
    "--trim-lead/--no-trim-lead",
    default=None,
    help="Trim i2v head before sampling (default from config).",
)
@click.option(
    "--trim-trail/--no-trim-trail",
    default=None,
    help="Trim clip tail before sampling (default from config).",
)
def import_sprites_cmd(
    project_path: Path,
    asset: str,
    input_dir: Path,
    pattern: str,
    fps: float,
    animation_name: str | None,
    loop: bool,
    skip_lead_frames: int,
    skip_lead_ratio: float | None,
    skip_trail_ratio: float | None,
    sample_frames: int | None,
    pre_trimmed: bool,
    pre_sampled: bool,
    trim_lead: bool | None,
    trim_trail: bool | None,
) -> None:
    """Copy PNG frames into project and generate SpriteFrames .tres."""
    config_path = Path.home() / ".gamefactory" / "config.json"
    config: dict = {}
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}

    try:
        result = import_sprite_frames(
            project_path,
            asset=asset,
            input_dir=input_dir,
            pattern=pattern,
            fps=fps,
            animation_name=animation_name,
            loop=loop,
            skip_lead_frames=skip_lead_frames,
            skip_trail_ratio=skip_trail_ratio,
            skip_lead_ratio=skip_lead_ratio,
            sample_frames=sample_frames,
            pre_trimmed=pre_trimmed,
            pre_sampled=pre_sampled,
            trim_lead=trim_lead,
            trim_trail=trim_trail,
            config=config if isinstance(config, dict) else {},
        )
    except GodotImportError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(json.dumps(result, ensure_ascii=False))


def _run_validate(project_path: Path) -> None:
    """Import assets, build C#, and boot the main scene headless."""
    godot = _get_godot_exe()
    project_path = project_path.resolve()
    config = _load_config()
    env = toolchain_env(config)

    csproj_files = list(project_path.glob("*.csproj"))
    if csproj_files:
        dotnet = resolve_dotnet(config) or "dotnet"
        build = subprocess.run(
            [dotnet, "build", str(csproj_files[0])],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            env=env,
        )
        if build.returncode != 0:
            raise RuntimeError(f"dotnet build failed:\n{build.stderr}\n{build.stdout}")

    import_result = subprocess.run(
        [godot, "--headless", "--path", str(project_path), "--import", "--quit"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )
    combined = (import_result.stdout or "") + (import_result.stderr or "")
    import_errors = [ln for ln in combined.splitlines() if "ERROR:" in ln]
    if import_result.returncode != 0 or import_errors:
        raise RuntimeError(
            "Godot import failed:\n" + "\n".join(import_errors or combined.splitlines()[-20:])
        )

    run_result = subprocess.run(
        [godot, "--headless", "--path", str(project_path), "--quit-after", "3"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )
    combined = (run_result.stdout or "") + (run_result.stderr or "")
    run_errors = [ln for ln in combined.splitlines() if "ERROR:" in ln]
    if run_result.returncode != 0 or run_errors:
        raise RuntimeError(
            "Godot run failed:\n" + "\n".join(run_errors or combined.splitlines()[-20:])
        )


@click.command("assemble")
@click.option(
    "--assemble-file",
    "assemble_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Godot-assembler handoff JSON (consumer_role: godot-assembler).",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Run godot validate after assembly.",
)
def assemble_cmd(assemble_path: Path, validate: bool) -> None:
    """godot-assembler agent: build .NET project from handoff plan."""
    try:
        handoff = load_godot_handoff(assemble_path)
        result = assemble_from_plan(handoff["plan"])
    except (ValueError, json.JSONDecodeError, OSError, GodotAssembleError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    project_path = Path(result["project_path"])
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    try:
        from assets_manifest import update_assets_manifest_after_assemble

        am_path = update_assets_manifest_after_assemble(assemble_path, result, handoff=handoff)
        if am_path is not None:
            click.echo(f"assets-manifest: {am_path}", err=True)
    except (ValueError, json.JSONDecodeError, OSError):
        pass

    if validate:
        try:
            _run_validate(project_path)
            click.echo("OK")
        except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(2)


@click.command("scaffold")
@click.option(
    "--production",
    "production_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="production.json from `production derive`.",
)
@click.option(
    "--project",
    "project_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Godot project dir (default: games/<slug> from production).",
)
@click.option(
    "--progress",
    "progress_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Update progress.json scaffold phase on success.",
)
@click.option("--validate/--no-validate", default=True, help="Run godot validate after scaffold.")
def scaffold_cmd(
    production_path: Path,
    project_path: Path | None,
    progress_path: Path | None,
    validate: bool,
) -> None:
    """Build compilable Godot shell from production.json (scenes, stubs, InputMap)."""
    from godot_scaffold import GodotScaffoldError, scaffold_from_production

    try:
        result = scaffold_from_production(production_path, project_path=project_path)
    except (GodotScaffoldError, ValueError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if validate:
        try:
            _run_validate(Path(result["project_path"]))
            result["validate"] = "pass"
        except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            result["validate"] = "fail"
            result["validate_error"] = str(exc)
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
            click.echo(f"Scaffold wrote files but validate failed: {exc}", err=True)
            sys.exit(2)

    if progress_path or result.get("brief_path"):
        try:
            from progress import (
                append_memory,
                default_progress_path,
                load_progress,
                save_progress,
                update_phase,
                init_progress,
            )

            prog_path = progress_path or default_progress_path(production_path=production_path)
            if prog_path.is_file():
                progress = load_progress(prog_path)
            else:
                brief = Path(result["brief_path"]) if result.get("brief_path") else None
                progress = init_progress(
                    brief_path=brief,
                    production_path=production_path,
                    project_path=Path(result["project_path"]),
                )
            update_phase(progress, "scaffold", status="done")
            append_memory(progress, "godot scaffold completed")
            save_progress(progress, prog_path)
            result["progress_path"] = str(prog_path.resolve())
        except (ValueError, OSError) as exc:
            result["progress_warning"] = str(exc)

    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


@click.command("dev-context")
@click.option(
    "--brief",
    "brief_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Product brief JSON.",
)
@click.option(
    "--project",
    "project_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Godot project directory (assemble output).",
)
@click.option(
    "--assemble-file",
    "assemble_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Optional godot-assembler handoff for assemble metadata.",
)
@click.option(
    "--production",
    "production_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Optional production.json (default: plans/production_<brief>.json if present).",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Write godot-developer handoff JSON (consumer_role: godot-developer).",
)
def dev_context_cmd(
    brief_path: Path,
    project_path: Path,
    assemble_path: Path | None,
    production_path: Path | None,
    output_path: Path | None,
) -> None:
    """Build godot-developer handoff from brief + assembled project (Pass 4)."""
    from godot_dev import build_godot_dev_plan
    from plan_io import build_godot_dev_handoff, save_handoff

    try:
        plan = build_godot_dev_plan(
            brief_path,
            project_path=project_path,
            assemble_handoff_path=assemble_path,
            production_path=production_path,
        )
        handoff = build_godot_dev_handoff(
            plan,
            context={
                "authoritative_sources": plan.get("authoritative_sources"),
                "contract_rules": plan.get("contract_rules"),
            },
        )
        payload = json.dumps(handoff, ensure_ascii=False, indent=2)
        if output_path is not None:
            save_handoff(output_path, handoff)
            click.echo(str(output_path.resolve()))
        else:
            click.echo(payload)
        click.echo(
            json.dumps(
                {
                    "consumer_role": "godot-developer",
                    "project_path": plan["project_path"],
                    "delegate": "codex or cursor — implement C# per plan.implementation_goals",
                },
                ensure_ascii=False,
            ),
            err=True,
        )
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@click.command("screenshot")
@click.option(
    "--project",
    "project_path",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Godot project directory.",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="PNG output path.",
)
@click.option("--wait-frames", default=8, show_default=True, help="Frames before capture.")
def screenshot_cmd(project_path: Path, output_path: Path, wait_frames: int) -> None:
    """Capture headless viewport screenshot of main scene."""
    from godot_screenshot import capture_screenshot

    try:
        result = capture_screenshot(project_path, output_path, wait_frames=wait_frames)
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


@click.command("validate")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Godot project directory.")
def validate_cmd(project_path: Path) -> None:
    """Validate project: import assets, build C#, boot main scene headless."""
    try:
        _run_validate(project_path)
        click.echo("OK")
    except subprocess.TimeoutExpired:
        click.echo("Error: validation timed out", err=True)
        sys.exit(1)
    except FileNotFoundError:
        godot = _get_godot_exe()
        click.echo(f"Error: Godot not found at '{godot}'. Set engine_path in config.", err=True)
        sys.exit(1)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)


@click.command("open")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Godot project directory.")
def open_cmd(project_path: Path) -> None:
    """Open a Godot project in the editor."""
    godot = _get_godot_exe().replace("_console.exe", ".exe")
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
            capture_output=True,
            text=True,
            timeout=300,
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
