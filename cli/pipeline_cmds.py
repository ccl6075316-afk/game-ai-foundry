"""CLI commands for pipeline DAG scheduling."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from pipeline_manifest import (
    TASK_DONE,
    TASK_FAILED,
    TASK_RUNNING,
    build_manifest,
    load_manifest,
    merge_manifest_status,
    ready_tasks,
    reconcile_manifest,
    record_task,
    save_manifest,
    status_summary,
)
from pipeline_runner import reset_task_cascade, run_pipeline


@click.group("pipeline")
def pipeline_group() -> None:
    """Brief → DAG manifest for concurrent asset production."""


@pipeline_group.command("plan")
@click.option(
    "--brief",
    "brief_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Project brief JSON (communication phase output).",
)
@click.option(
    "-o",
    "--output",
    "manifest_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Write manifest JSON (e.g. pipeline/manifest.json).",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Asset output directory (default: projects/<slug>/output or output/<brief-stem>).",
)
@click.option(
    "--plans-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Plan handoff directory (default: projects/<slug>/plans or plans/).",
)
@click.option(
    "--sprite-frames",
    default=24,
    show_default=True,
    type=int,
    help="Default sprite frame count for video animations (3–4s clips).",
)
@click.option(
    "--godot/--no-godot",
    default=True,
    help="Append godot-assembler assemble task after assets.",
)
@click.option(
    "--godot-project",
    default=None,
    type=click.Path(path_type=Path),
    help="Godot project path (default: projects/<slug>/game or games/<brief-stem>).",
)
@click.option(
    "--merge",
    "merge_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Preserve task status from an existing manifest.",
)
@click.option(
    "--max-wave",
    "max_wave",
    default=None,
    type=int,
    help="Only schedule assets with production_wave <= N (design ledger stays full).",
)
@click.option(
    "--game-dev/--no-game-dev",
    default=True,
    help="Append Pass 4 godot-developer dev-context task after assemble.",
)
def plan_cmd(
    brief_path: Path,
    manifest_path: Path,
    output_dir: Path | None,
    plans_dir: Path | None,
    sprite_frames: int,
    godot: bool,
    godot_project: Path | None,
    merge_path: Path | None,
    max_wave: int | None,
    game_dev: bool,
) -> None:
    """Build task DAG from brief (what to generate, animation deps, layers)."""
    try:
        manifest = build_manifest(
            brief_path,
            output_dir=output_dir,
            plans_dir=plans_dir,
            sprite_frames_default=sprite_frames,
            godot_project=godot_project,
            include_godot=godot,
            include_game_dev=game_dev and godot,
            max_wave=max_wave,
        )
        if merge_path is not None:
            merge_manifest_status(manifest, load_manifest(merge_path))
        from project_paths import default_paths_for_brief

        _defs = default_paths_for_brief(brief_path)
        Path(_defs["plans_dir"]).mkdir(parents=True, exist_ok=True)
        Path(_defs["output_dir"]).mkdir(parents=True, exist_ok=True)
        manifest_path = Path(manifest_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        save_manifest(manifest_path, manifest)
        from assets_manifest import refresh_assets_manifest_from_pipeline

        refresh_assets_manifest_from_pipeline(manifest)
        summary = status_summary(manifest)
        click.echo(str(manifest_path.resolve()))
        click.echo(
            json.dumps(
                {
                    "tasks": summary["total"],
                    "layers": max((t.get("layer", 0) for t in manifest["tasks"]), default=0),
                    "ready": summary["ready_ids"],
                },
                ensure_ascii=False,
            )
        )
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("status")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--json", "as_json", is_flag=True, help="Print full JSON summary.")
def status_cmd(manifest_path: Path, as_json: bool) -> None:
    """Summarize manifest progress and list ready tasks.

    Also reconciles disk: missing outputs (e.g. user-deleted) are reset to pending.
    """
    try:
        manifest = load_manifest(manifest_path)
        synced = reconcile_manifest(manifest)
        if synced["total"]:
            save_manifest(manifest_path, manifest)
            from assets_manifest import refresh_assets_manifest_from_pipeline

            refresh_assets_manifest_from_pipeline(manifest)
        summary = status_summary(manifest)
        if synced["invalidated"]:
            summary["invalidated"] = synced["invalidated"]
            summary["invalidated_ids"] = synced["invalidated_ids"]
        if as_json:
            summary["ready_tasks"] = ready_tasks(manifest)
            click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
            return
        click.echo(f"brief: {summary['brief']}")
        click.echo(f"tasks: {summary['total']}  counts: {summary['counts']}")
        click.echo(f"ready ({summary['ready_count']}): {', '.join(summary['ready_ids']) or '-'}")
        if synced["invalidated"]:
            click.echo(
                f"invalidated missing artifacts ({synced['invalidated']}): "
                f"{', '.join(synced['invalidated_ids'])}"
            )
        if summary["failed_ids"]:
            click.echo(f"failed: {', '.join(summary['failed_ids'])}")
        if summary["done"]:
            click.echo("pipeline: complete")
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("ready")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--role",
    default=None,
    help="Filter ready tasks by task role (e.g. image-generator).",
)
@click.option("--json", "as_json", is_flag=True, help="Print task objects as JSON array.")
def ready_cmd(manifest_path: Path, role: str | None, as_json: bool) -> None:
    """List tasks ready to run (dependencies satisfied, status pending)."""
    try:
        manifest = load_manifest(manifest_path)
        tasks = ready_tasks(manifest)
        if role:
            tasks = [t for t in tasks if t.get("role") == role]
        if as_json:
            click.echo(json.dumps(tasks, ensure_ascii=False, indent=2))
            return
        for task in tasks:
            click.echo(f"{task['id']}\t{task['role']}\t{task['command']}")
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("record")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--task-id", required=True, help="Task id from manifest (e.g. knight.image.generate).")
@click.option(
    "--status",
    type=click.Choice([TASK_RUNNING, TASK_DONE, TASK_FAILED], case_sensitive=False),
    required=True,
)
@click.option("--exit-code", type=int, default=None, help="Shell exit code from the task command.")
@click.option("--result-json", default=None, help="Inline JSON result payload.")
@click.option(
    "--result-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Read result JSON from file (e.g. captured stdout).",
)
def record_cmd(
    manifest_path: Path,
    task_id: str,
    status: str,
    exit_code: int | None,
    result_json: str | None,
    result_file: Path | None,
) -> None:
    """Update task status after a worker finishes (orchestrator calls this)."""
    try:
        manifest = load_manifest(manifest_path)
        result: dict | None = None
        if result_file is not None:
            result = json.loads(result_file.read_text(encoding="utf-8"))
        elif result_json:
            result = json.loads(result_json)
        if exit_code is not None:
            payload = dict(result or {})
            payload["exit_code"] = exit_code
            if exit_code != 0 and status == TASK_DONE:
                status = TASK_FAILED
            result = payload
        record_task(manifest, task_id, status=status, result=result)
        save_manifest(manifest_path, manifest)
        from assets_manifest import refresh_assets_manifest_from_pipeline

        refresh_assets_manifest_from_pipeline(manifest)
        click.echo(json.dumps(status_summary(manifest), ensure_ascii=False))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("reconcile")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
def reconcile_cmd(manifest_path: Path) -> None:
    """Sync tasks with disk: missing outputs → pending; existing outputs → done."""
    try:
        manifest = load_manifest(manifest_path)
        synced = reconcile_manifest(manifest)
        save_manifest(manifest_path, manifest)
        from assets_manifest import refresh_assets_manifest_from_pipeline

        refresh_assets_manifest_from_pipeline(manifest)
        summary = status_summary(manifest)
        click.echo(
            json.dumps(
                {
                    "invalidated": synced["invalidated"],
                    "promoted": synced["promoted"],
                    "invalidated_ids": synced["invalidated_ids"],
                    "reconciled": synced["total"],
                    **summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("show")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.argument("task_id")
def show_cmd(manifest_path: Path, task_id: str) -> None:
    """Print one task entry from the manifest."""
    try:
        manifest = load_manifest(manifest_path)
        from pipeline_manifest import task_by_id

        click.echo(json.dumps(task_by_id(manifest, task_id), ensure_ascii=False, indent=2))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("run")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--jobs",
    default=4,
    show_default=True,
    type=int,
    help="Max parallel subprocesses per wave.",
)
@click.option(
    "--run-prompts",
    is_flag=True,
    help="Include prompt.craft (LLM). Default: skip if plan file exists.",
)
@click.option(
    "--run-game-dev",
    is_flag=True,
    help="Run Pass 4 godot.dev-context (writes dev handoff). Default: skip (leave to an external implementation workflow).",
)
@click.option(
    "--skip-roles",
    default=None,
    help="Comma-separated roles to skip (default: prompt-crafter when not --run-prompts).",
)
@click.option(
    "--stop-on-fail/--no-stop-on-fail",
    default=True,
    help="Pause when a task exits non-zero (exit 2 = validation).",
)
@click.option(
    "--timeout",
    "task_timeout",
    default=1800.0,
    show_default=True,
    type=float,
    help="Per-task subprocess timeout in seconds.",
)
@click.option(
    "--retries",
    "network_retries",
    default=3,
    show_default=True,
    type=int,
    help="Extra attempts after network/timeout failures (0 = no retry).",
)
@click.option(
    "--retry-backoff",
    default=2.0,
    show_default=True,
    type=float,
    help="Base seconds between network retries (doubles each attempt).",
)
@click.option("--dry-run", is_flag=True, help="Print wave without executing commands.")
@click.option(
    "--detach",
    is_flag=True,
    help="Start run in background and return job_id immediately (poll with pipeline job status).",
)
@click.option(
    "--jobs-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Detached job store directory (default: <manifest-dir>/jobs).",
)
@click.option("--json", "as_json", is_flag=True, help="Print JSON (required shape for --detach).")
def run_cmd(
    manifest_path: Path,
    jobs: int,
    run_prompts: bool,
    run_game_dev: bool,
    skip_roles: str | None,
    stop_on_fail: bool,
    task_timeout: float,
    network_retries: int,
    retry_backoff: float,
    dry_run: bool,
    detach: bool,
    jobs_dir: Path | None,
    as_json: bool,
) -> None:
    """Run ready manifest tasks via subprocess. Default skips prompt.craft."""
    if detach:
        from async_job import (
            job_public_view,
            jobs_dir_for_manifest,
            start_detached_job,
        )

        if dry_run:
            click.echo("Error: --detach cannot be combined with --dry-run.", err=True)
            sys.exit(1)
        store = Path(jobs_dir) if jobs_dir else jobs_dir_for_manifest(manifest_path)
        child: list[str] = [
            sys.executable,
            str(Path(__file__).resolve().parent / "gamefactory.py"),
            "pipeline",
            "run",
            "--manifest",
            str(Path(manifest_path).resolve()),
            "--jobs",
            str(jobs),
            "--timeout",
            str(task_timeout),
            "--retries",
            str(network_retries),
            "--retry-backoff",
            str(retry_backoff),
        ]
        if run_prompts:
            child.append("--run-prompts")
        if run_game_dev:
            child.append("--run-game-dev")
        if skip_roles:
            child.extend(["--skip-roles", skip_roles])
        if not stop_on_fail:
            child.append("--no-stop-on-fail")
        try:
            job = start_detached_job(
                child,
                cwd=Path.cwd(),
                jobs_dir=store,
                python_executable=sys.executable,
            )
        except (OSError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        view = job_public_view(job)
        view["command"] = "pipeline run --detach"
        view["next_action"] = "poll"
        view["outputs"] = list(view.get("outputs") or []) + [str(Path(manifest_path).resolve())]
        view["summary"]["manifest"] = str(Path(manifest_path).resolve())
        view["summary"]["jobs_dir"] = str(store.resolve())
        click.echo(json.dumps(view, ensure_ascii=False, indent=2))
        return

    skip: set[str] | None = None
    if skip_roles:
        skip = {r.strip() for r in skip_roles.split(",") if r.strip()}

    def _on_start(task: dict) -> None:
        click.echo(f"→ {task['id']}", err=True)

    def _on_finish(outcome) -> None:
        extra = ""
        attempts = (outcome.result or {}).get("attempts")
        if attempts and attempts > 1:
            extra = f" (after {attempts} attempts)"
        click.echo(
            f"  {outcome.task_id}: exit {outcome.exit_code} → {outcome.status}{extra}",
            err=True,
        )

    def _on_retry(task_id: str, attempt: int, max_retries: int, wait_s: float, _outcome) -> None:
        click.echo(
            f"  ↻ {task_id}: network/timeout error — retry {attempt}/{max_retries} in {wait_s:.0f}s",
            err=True,
        )

    try:
        result = run_pipeline(
            manifest_path,
            jobs=jobs,
            skip_roles=skip,
            run_prompts=run_prompts,
            run_game_dev=run_game_dev,
            stop_on_fail=stop_on_fail,
            task_timeout=task_timeout,
            dry_run=dry_run,
            network_retries=network_retries,
            retry_backoff=retry_backoff,
            on_task_start=_on_start,
            on_task_finish=_on_finish,
            on_task_retry=_on_retry,
        )
        payload = {
            "complete": result.complete,
            "paused": result.paused,
            "blocked": result.blocked,
            "message": result.message,
            "summary": result.summary,
        }
        if result.last_outcome:
            payload["last_task"] = result.last_outcome.task_id
            payload["last_exit_code"] = result.last_outcome.exit_code
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        if result.blocked or result.paused:
            sys.exit(2 if result.paused else 1)
        if not result.complete and not dry_run:
            sys.exit(1)
    except (ValueError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("reset")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--task-id", required=True, help="Task to reset to pending.")
@click.option(
    "--cascade/--no-cascade",
    default=True,
    help="Also reset downstream dependents.",
)
def reset_cmd(manifest_path: Path, task_id: str, cascade: bool) -> None:
    """Reset task(s) to pending after prompt fix or manual retry."""
    try:
        manifest = load_manifest(manifest_path)
        if cascade:
            reset_ids = reset_task_cascade(manifest, task_id)
        else:
            from pipeline_runner import reset_task

            reset_task(manifest, task_id)
            reset_ids = [task_id]
        save_manifest(manifest_path, manifest)
        if not cascade:
            from assets_manifest import refresh_assets_manifest_from_pipeline

            refresh_assets_manifest_from_pipeline(manifest, invalidated_task_ids=reset_ids)
        click.echo(json.dumps({"reset": reset_ids}, ensure_ascii=False, indent=2))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("diagnose")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
def diagnose_cmd(manifest_path: Path) -> None:
    """Classify failed tasks: code-healable vs needing deterministic external remediation."""
    try:
        from pipeline_heal import diagnose_and_heal_file

        report = diagnose_and_heal_file(manifest_path, apply=False)
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("heal")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--apply/--dry-run",
    default=True,
    help="Reset code-healable failed tasks (default: apply).",
)
def heal_cmd(manifest_path: Path, apply: bool) -> None:
    """Reset simple failed tasks (API size / network / missing file). Route the rest to external remediation."""
    try:
        from pipeline_heal import diagnose_and_heal_file

        report = diagnose_and_heal_file(manifest_path, apply=apply)
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        if apply and report.get("healed"):
            from assets_manifest import refresh_assets_manifest_from_pipeline
            from pipeline_manifest import load_manifest

            refresh_assets_manifest_from_pipeline(load_manifest(manifest_path))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@pipeline_group.command("suggest-retry")
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--asset", "assets", multiple=True, help="Asset name to reset (repeatable)")
@click.option("--jobs", default=2, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True)
def suggest_retry_cmd(manifest_path: Path, assets: tuple[str, ...], jobs: int, as_json: bool) -> None:
    """Print whitelisted reset+run commands for named assets (external Agent next_actions)."""
    from pipeline_retry import suggest_retry_commands

    # Prefer path relative to cli cwd for copy-paste
    try:
        rel = Path("..") / "pipeline" / manifest_path.name
        if not rel.is_file():
            rel = manifest_path
    except Exception:
        rel = manifest_path
    cmds = suggest_retry_commands(
        manifest_rel=str(rel),
        asset_names=list(assets),
        jobs=jobs,
    )
    if as_json:
        click.echo(json.dumps({"commands": cmds, "manifest": str(manifest_path.resolve())}, ensure_ascii=False, indent=2))
        return
    for c in cmds:
        click.echo(c)


@pipeline_group.group("job")
def pipeline_job_group() -> None:
    """Detached file-backed jobs for external-agent polling."""


@pipeline_job_group.command("start")
@click.option(
    "--jobs-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory for job JSON + logs.",
)
@click.option(
    "--cwd",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Working directory for the detached command.",
)
@click.option("--json", "as_json", is_flag=True, default=True, help="Print JSON (default).")
@click.argument("argv", nargs=-1, required=True)
def pipeline_job_start_cmd(
    jobs_dir: Path,
    cwd: Path,
    as_json: bool,
    argv: tuple[str, ...],
) -> None:
    """Start any command as a detached job; return job_id immediately."""
    from async_job import job_public_view, start_detached_job

    try:
        job = start_detached_job(list(argv), cwd=cwd, jobs_dir=jobs_dir)
    except (OSError, ValueError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    view = job_public_view(job)
    view["command"] = "pipeline job start"
    if as_json:
        click.echo(json.dumps(view, ensure_ascii=False, indent=2))
    else:
        click.echo(f"job_id={job['job_id']} status={job['status']} next_action=poll")


@pipeline_job_group.command("status")
@click.option(
    "--jobs-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--job-id", required=True)
@click.option("--json", "as_json", is_flag=True, default=True)
def pipeline_job_status_cmd(jobs_dir: Path, job_id: str, as_json: bool) -> None:
    """Refresh and print one job's file-backed status."""
    from async_job import job_public_view, refresh_job

    try:
        job = refresh_job(jobs_dir, job_id)
    except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    view = job_public_view(job)
    if as_json:
        click.echo(json.dumps(view, ensure_ascii=False, indent=2))
    else:
        click.echo(f"{job_id} status={view['status']} next_action={view['next_action']}")
    if view["status"] == "failed":
        sys.exit(1)


@pipeline_job_group.command("wait")
@click.option(
    "--jobs-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--job-id", required=True)
@click.option("--timeout", "timeout_sec", default=600.0, type=float)
@click.option("--poll-interval", default=1.0, type=float)
@click.option("--json", "as_json", is_flag=True, default=True)
def pipeline_job_wait_cmd(
    jobs_dir: Path,
    job_id: str,
    timeout_sec: float,
    poll_interval: float,
    as_json: bool,
) -> None:
    """Block until job reaches done/failed (for local scripts/tests)."""
    from async_job import job_public_view, wait_for_job

    try:
        job = wait_for_job(
            jobs_dir,
            job_id,
            timeout_sec=timeout_sec,
            poll_sec=poll_interval,
        )
    except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    view = job_public_view(job)
    if as_json:
        click.echo(json.dumps(view, ensure_ascii=False, indent=2))
    if view["status"] != "done":
        sys.exit(1)
