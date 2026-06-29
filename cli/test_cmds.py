"""Tester role CLI — plan, play, screenshot, vision analysis."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from godot_screenshot import capture_screenshot
from playtest_plan import build_playtest_from_brief, load_playtest_plan, save_playtest_plan
from test_analysis import (
    TestAnalysisError,
    analyze_screenshot,
    build_validation_report,
    criteria_from_brief,
)
from visual_target import resolve_visual_reference_path


def _load_config() -> dict:
    config_path = Path.home() / ".gamefactory" / "config.json"
    if not config_path.is_file():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _slug(project_path: Path, brief_path: Path | None) -> str:
    if brief_path:
        return brief_path.stem.replace("-brief", "").replace(".example", "")
    return project_path.name


def _default_report_path(project_path: Path, brief_path: Path | None) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("..") / "output" / _slug(project_path, brief_path) / "validation" / f"report-{ts}.json"


def _default_screenshot_path(project_path: Path, brief_path: Path | None) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("..") / "output" / _slug(project_path, brief_path) / "validation" / "screenshots" / f"{ts}.png"


def _default_playtest_plan_path(brief_path: Path) -> Path:
    stem = brief_path.stem.replace(".json", "")
    return Path("..") / "plans" / f"playtest_{stem}.json"


def _default_play_screenshot_dir(project_path: Path, brief_path: Path | None) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("..") / "output" / _slug(project_path, brief_path) / "validation" / f"play-{ts}"


@click.group("test")
def test_group() -> None:
    """Tester agent — playtest plan, command playback, vision QA (ITERATIVE §6)."""


@test_group.command("plan")
@click.option(
    "--brief",
    "brief_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Frozen brief / design+production doc.",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Write playtest JSON (default: plans/playtest_<brief>.json).",
)
def plan_cmd(brief_path: Path, output_path: Path | None) -> None:
    """Generate playtest command JSON from brief (design doc → test harness)."""
    plan = build_playtest_from_brief(brief_path)
    out = output_path or _default_playtest_plan_path(brief_path)
    path = save_playtest_plan(plan, out)
    click.echo(str(path))
    click.echo(
        json.dumps(
            {"steps": len(plan["steps"]), "actions": plan.get("input_actions", [])},
            ensure_ascii=False,
        ),
        err=True,
    )


@test_group.command("play")
@click.option(
    "--project",
    "project_path",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--plan",
    "plan_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Playtest JSON from `test plan`.",
)
@click.option("--brief", "brief_path", default=None, type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", "output_path", default=None, type=click.Path(path_type=Path))
@click.option("--skip-validate", is_flag=True, help="Skip godot validate before play.")
@click.option("--skip-analyze", is_flag=True, help="Run commands + screenshots only.")
def play_cmd(
    project_path: Path,
    plan_path: Path,
    brief_path: Path | None,
    output_path: Path | None,
    skip_validate: bool,
    skip_analyze: bool,
) -> None:
    """Execute playtest JSON: input simulation + screenshots + per-step vision QA."""
    from godot_cmds import _run_validate
    from godot_playtest import run_playtest_plan

    config = _load_config()
    plan = load_playtest_plan(plan_path)
    if brief_path is None and plan.get("brief_path"):
        bp = Path(str(plan["brief_path"]))
        if bp.is_file():
            brief_path = bp

    build_ok = True
    build_error: str | None = None
    if not skip_validate:
        try:
            _run_validate(project_path)
        except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            build_ok = False
            build_error = str(exc)

    manifest = None
    play_error: str | None = None
    screenshot_dir: Path | None = None
    if build_ok:
        screenshot_dir = _default_play_screenshot_dir(project_path, brief_path)
        try:
            manifest = run_playtest_plan(
                project_path,
                plan_path,
                screenshot_dir,
                manifest_path=screenshot_dir / "manifest.json",
            )
        except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            build_ok = False
            play_error = str(exc)
            build_error = play_error

    visual_results: list[dict] = []
    failed_any = False
    if build_ok and manifest and not skip_analyze:
        shots: dict = manifest.get("screenshots", {})
        checks = plan.get("visual_checks") or []
        for check in checks:
            if not isinstance(check, dict):
                continue
            name = str(check.get("screenshot", ""))
            shot_path = shots.get(name)
            if not shot_path or not Path(shot_path).is_file():
                visual_results.append(
                    {"screenshot": name, "status": "skipped", "reason": "missing capture"}
                )
                continue
            criterion = str(check.get("criterion", ""))
            source = str(check.get("source", "playtest.visual_checks"))
            try:
                ref_path = resolve_visual_reference_path(brief_path) if brief_path else None
                analysis = analyze_screenshot(
                    Path(shot_path),
                    [{"source": source, "criterion": criterion}],
                    config=config,
                    reference_image_path=ref_path,
                )
            except TestAnalysisError as exc:
                analysis = {"status": "inconclusive", "summary": str(exc)}
            visual_results.append({"screenshot": name, "path": shot_path, "analysis": analysis})
            if analysis.get("status") == "failed":
                failed_any = True

    criteria = plan.get("acceptance_criteria") or (
        criteria_from_brief(brief_path) if brief_path else []
    )
    boot_shot = None
    if manifest and manifest.get("screenshots"):
        boot_shot = next(iter(manifest["screenshots"].values()), None)

    overall_analysis = None
    if visual_results:
        statuses = [r.get("analysis", {}).get("status") for r in visual_results if "analysis" in r]
        if failed_any or any(s == "failed" for s in statuses):
            overall_analysis = {"status": "failed", "visual_checks": visual_results}
        elif any(s == "inconclusive" for s in statuses):
            overall_analysis = {"status": "inconclusive", "visual_checks": visual_results}
        else:
            overall_analysis = {"status": "passed", "visual_checks": visual_results}

    report = build_validation_report(
        brief_path=brief_path,
        project_path=project_path,
        screenshot_path=Path(boot_shot) if boot_shot else None,
        build_ok=build_ok,
        build_error=build_error,
        analysis=overall_analysis,
        criteria=criteria if isinstance(criteria, list) else [],
    )
    vr = report["validation_report"]
    vr["playtest_plan"] = str(plan_path.resolve())
    vr["playtest_manifest"] = manifest
    vr["layers"]["playtest"] = {"ok": build_ok and manifest is not None, "error": play_error}

    out = output_path or _default_report_path(project_path, brief_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    click.echo(f"report: {out.resolve()}", err=True)
    if screenshot_dir:
        click.echo(f"screenshots: {screenshot_dir.resolve()}", err=True)

    status = vr["status"]
    if not build_ok or status == "failed" or failed_any:
        sys.exit(2)
    if status == "inconclusive":
        sys.exit(1)


@test_group.command("screenshot")
@click.option(
    "--project",
    "project_path",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("-o", "--output", "output_path", default=None, type=click.Path(path_type=Path))
@click.option("--brief", "brief_path", default=None, type=click.Path(exists=True, path_type=Path))
@click.option("--wait-frames", default=8, show_default=True)
def screenshot_cmd(
    project_path: Path,
    output_path: Path | None,
    brief_path: Path | None,
    wait_frames: int,
) -> None:
    """Single headless viewport screenshot."""
    out = output_path or _default_screenshot_path(project_path, brief_path)
    try:
        result = capture_screenshot(project_path, out, wait_frames=wait_frames)
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


@test_group.command("analyze")
@click.option("--image", "image_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--brief", "brief_path", default=None, type=click.Path(exists=True, path_type=Path))
@click.option("--criteria-file", default=None, type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", "output_path", default=None, type=click.Path(path_type=Path))
def analyze_cmd(
    image_path: Path,
    brief_path: Path | None,
    criteria_file: Path | None,
    output_path: Path | None,
) -> None:
    """Vision LLM analysis vs brief criteria."""
    config = _load_config()
    if criteria_file:
        criteria = json.loads(criteria_file.read_text(encoding="utf-8"))
    elif brief_path:
        criteria = criteria_from_brief(brief_path)
    else:
        criteria = [{"source": "default", "criterion": "Scene renders correctly."}]

    try:
        ref_path = resolve_visual_reference_path(brief_path) if brief_path else None
        analysis = analyze_screenshot(
            image_path,
            criteria,
            config=config,
            reference_image_path=ref_path,
        )
    except TestAnalysisError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    payload = {"analysis": analysis, "criteria": criteria, "screenshot": str(image_path)}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        click.echo(str(output_path.resolve()))
    else:
        click.echo(text)
    if analysis.get("status") == "failed":
        sys.exit(2)


@test_group.command("run")
@click.option("--project", "project_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--brief", "brief_path", default=None, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--plan",
    "plan_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="If set (or plans/playtest_<brief>.json exists), runs `test play` instead of single screenshot.",
)
@click.option("-o", "--output", "output_path", default=None, type=click.Path(path_type=Path))
@click.option("--skip-analyze", is_flag=True)
def run_cmd(
    project_path: Path,
    brief_path: Path | None,
    plan_path: Path | None,
    output_path: Path | None,
    skip_analyze: bool,
) -> None:
    """Autonomous QA: playtest plan if available, else validate + single screenshot."""
    if brief_path and plan_path is None:
        candidate = _default_playtest_plan_path(brief_path)
        if candidate.is_file():
            plan_path = candidate

    if plan_path is not None:
        ctx = click.get_current_context()
        ctx.invoke(
            play_cmd,
            project_path=project_path,
            plan_path=plan_path,
            brief_path=brief_path,
            output_path=output_path,
            skip_validate=False,
            skip_analyze=skip_analyze,
        )
        return

    from godot_cmds import _run_validate

    config = _load_config()
    criteria = criteria_from_brief(brief_path) if brief_path else [
        {"source": "default", "criterion": "Main scene boots headless."}
    ]
    build_ok = True
    build_error: str | None = None
    try:
        _run_validate(project_path)
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        build_ok = False
        build_error = str(exc)

    screenshot_path: Path | None = None
    if build_ok:
        screenshot_path = _default_screenshot_path(project_path, brief_path)
        try:
            capture_screenshot(project_path, screenshot_path)
        except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            build_ok = False
            build_error = str(exc)

    analysis = None
    if build_ok and screenshot_path and not skip_analyze:
        try:
            ref_path = resolve_visual_reference_path(brief_path) if brief_path else None
            analysis = analyze_screenshot(
                screenshot_path,
                criteria,
                config=config,
                reference_image_path=ref_path,
            )
        except TestAnalysisError as exc:
            analysis = {"status": "inconclusive", "summary": str(exc), "failed_criteria": []}

    report = build_validation_report(
        brief_path=brief_path,
        project_path=project_path,
        screenshot_path=screenshot_path,
        build_ok=build_ok,
        build_error=build_error,
        analysis=analysis,
        criteria=criteria,
    )
    out = output_path or _default_report_path(project_path, brief_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    click.echo(f"report: {out.resolve()}", err=True)
    status = report["validation_report"]["status"]
    if status == "failed" or not build_ok:
        sys.exit(2)
    if status == "inconclusive":
        sys.exit(1)
