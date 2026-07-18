"""CLI — project progress ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from progress import (
    append_memory,
    default_progress_path,
    init_progress,
    load_progress,
    save_progress,
    sync_progress_from_production,
    update_phase,
    update_task_status,
    update_validation_layer,
)


def register_project_commands(cli_group: click.Group) -> None:
    @cli_group.group("project")
    def project_group() -> None:
        """Project-wide progress and resume state."""

    @project_group.group("progress")
    def progress_group() -> None:
        """Task + validation progress for agent resume."""

    @progress_group.command("init")
    @click.option("--brief", "brief_path", default=None, type=click.Path(exists=True, path_type=Path))
    @click.option(
        "--production",
        "production_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--project", "project_path", default=None, type=click.Path(path_type=Path))
    @click.option("-o", "--output", "output_path", default=None, type=click.Path(path_type=Path))
    def init_cmd(
        brief_path: Path | None,
        production_path: Path,
        project_path: Path | None,
        output_path: Path | None,
    ) -> None:
        """Create progress.json from production.godot_tasks."""
        try:
            data = init_progress(
                brief_path=brief_path,
                production_path=production_path,
                project_path=project_path,
            )
            out = output_path or default_progress_path(
                brief_path=brief_path,
                production_path=production_path,
            )
            path = save_progress(data, out)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(str(path))

    @progress_group.command("show")
    @click.option(
        "--progress",
        "progress_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    def show_cmd(progress_path: Path, as_json: bool) -> None:
        """Show progress summary or full JSON."""
        try:
            data = load_progress(progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(data, ensure_ascii=False, indent=2))
            return
        meta = data.get("progress_meta") or {}
        click.echo(f"slug: {meta.get('slug')}")
        click.echo(f"project: {meta.get('project_path')}")
        phases = data.get("phases") or {}
        click.echo(f"scaffold: {(phases.get('scaffold') or {}).get('status')}")
        val = phases.get("validation") or {}
        click.echo(f"validate: {val.get('validate')}  playtest: {val.get('playtest')}")
        click.echo("godot_tasks:")
        for task in phases.get("godot_tasks") or []:
            if isinstance(task, dict):
                click.echo(f"  [{task.get('status')}] {task.get('id')}: {task.get('title')}")

    @progress_group.command("task")
    @click.option("--progress", "progress_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option("--id", "task_id", required=True)
    @click.option(
        "--status",
        required=True,
        type=click.Choice(["pending", "in_progress", "done", "failed", "blocked"]),
    )
    @click.option("--error", default=None, help="Failure note when status=failed.")
    def task_cmd(progress_path: Path, task_id: str, status: str, error: str | None) -> None:
        """Update a godot_task status (typically after harness/validate)."""
        try:
            data = load_progress(progress_path)
            update_task_status(data, task_id, status, error=error)
            save_progress(data, progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(f"OK task {task_id} -> {status}")

    @progress_group.command("sync")
    @click.option(
        "--progress",
        "progress_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option(
        "--production",
        "production_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    def sync_cmd(progress_path: Path, production_path: Path, as_json: bool) -> None:
        """Pull new production.godot_tasks into progress (skip existing ids)."""
        from production import load_production

        try:
            prog = load_progress(progress_path)
            prod = load_production(production_path)
            result = sync_progress_from_production(prog, prod)
            save_progress(prog, progress_path)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(
                json.dumps(
                    {"ok": True, "progress": str(progress_path.resolve()), **result},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        click.echo(f"OK added={result['added']} skipped={len(result['skipped'])}")

    @progress_group.command("validation")
    @click.option("--progress", "progress_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option("--layer", required=True, type=click.Choice(["validate", "unit", "playtest", "regression"]))
    @click.option("--status", required=True, type=click.Choice(["pass", "fail", "not_run", "inconclusive"]))
    @click.option("--error", default=None)
    @click.option("--report", "report_path", default=None, type=click.Path(path_type=Path))
    def validation_cmd(
        progress_path: Path,
        layer: str,
        status: str,
        error: str | None,
        report_path: Path | None,
    ) -> None:
        """Record validation layer result."""
        try:
            data = load_progress(progress_path)
            update_validation_layer(
                data,
                layer,
                status,
                error=error,
                report_path=str(report_path.resolve()) if report_path else None,
            )
            save_progress(data, progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(f"OK validation.{layer} -> {status}")

    @progress_group.command("note")
    @click.option("--progress", "progress_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.argument("message")
    def note_cmd(progress_path: Path, message: str) -> None:
        """Append a memory note for the next agent session."""
        try:
            data = load_progress(progress_path)
            append_memory(data, message)
            save_progress(data, progress_path)
        except (ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo("OK")

    @project_group.command("action")
    @click.option("--cmd", "command", required=True, help="Full or relative gamefactory CLI line")
    @click.option("--dry-run", is_flag=True, help="Only validate whitelist, do not execute")
    @click.option("--timeout", default=600, show_default=True, type=int)
    @click.option("--json", "as_json", is_flag=True)
    def action_cmd(command: str, dry_run: bool, timeout: int, as_json: bool) -> None:
        """Run one whitelisted next_action (post-triage pipeline / validate / …)."""
        import os
        import subprocess

        from safe_cli import SafeCliError, normalize_action

        info = normalize_action(command)
        if not info["ok"]:
            payload = {"ok": False, "error": info["error"], "raw": command}
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(f"Error: {info['error']}", err=True)
            sys.exit(1)
        argv = info["argv"]
        if dry_run:
            payload = {"ok": True, "dry_run": True, "argv": argv, "label": info["label"]}
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(" ".join(argv))
            return

        root = Path(__file__).resolve().parent.parent
        cli_dir = Path(__file__).resolve().parent
        python = sys.executable
        full = [python, "gamefactory.py", *argv]
        env = {**os.environ, "GAMEFACTORY_ROOT": str(root), "PYTHONIOENCODING": "utf-8"}
        try:
            proc = subprocess.Popen(
                full,
                cwd=str(cli_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,
            )
        except OSError as exc:
            payload = {"ok": False, "error": str(exc), "argv": argv}
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(str(exc), err=True)
            sys.exit(1)

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        def _pump(stream, sink: list[str], *, err: bool) -> None:
            assert stream is not None
            for line in stream:
                sink.append(line)
                # Stream to parent so Electron onLine can forward to GUI
                if as_json:
                    # Keep JSON final payload clean: mirror to stderr for live log
                    sys.stderr.write(line)
                    sys.stderr.flush()
                elif err:
                    sys.stderr.write(line)
                    sys.stderr.flush()
                else:
                    sys.stdout.write(line)
                    sys.stdout.flush()

        import threading

        t_out = threading.Thread(target=_pump, args=(proc.stdout, stdout_chunks), kwargs={"err": False})
        t_err = threading.Thread(target=_pump, args=(proc.stderr, stderr_chunks), kwargs={"err": True})
        t_out.start()
        t_err.start()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            payload = {"ok": False, "error": f"timed out after {timeout}s", "argv": argv}
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(payload["error"], err=True)
            sys.exit(1)
        t_out.join(timeout=5)
        t_err.join(timeout=5)

        payload = {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "argv": argv,
            "label": info["label"],
            "stdout": "".join(stdout_chunks)[-8000:],
            "stderr": "".join(stderr_chunks)[-4000:],
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        if proc.returncode != 0:
            sys.exit(proc.returncode)

    @project_group.group("handoff")
    def handoff_group() -> None:
        """Dispatch packages from 项目经理 → 程序员 (file bus)."""

    @handoff_group.command("list")
    @click.option(
        "--status",
        default="open",
        type=click.Choice(["open", "claimed", "done", "cancelled", "all"]),
        show_default=True,
    )
    @click.option(
        "--target-instance-id",
        default=None,
        help="Filter: this instance + untargeted (broadcast) handoffs.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def handoff_list_cmd(status: str, target_instance_id: str | None, as_json: bool) -> None:
        """List handoff files under plans/handoffs/."""
        from handoff import list_handoffs

        st = None if status == "all" else status
        items = list_handoffs(
            status=st,
            target_role=None,
            target_instance_id=target_instance_id,
        )
        if as_json:
            click.echo(json.dumps({"handoffs": items, "count": len(items)}, ensure_ascii=False, indent=2))
            return
        if not items:
            click.echo("(no handoffs)")
            return
        for item in items:
            tid = item.get("target_instance_id") or "-"
            click.echo(
                f"{item.get('id')}\t{item.get('status')}\t{item.get('triage')}\t"
                f"{tid}\t{item.get('title')}"
            )

    @handoff_group.command("show")
    @click.argument("handoff_id")
    @click.option("--json", "as_json", is_flag=True)
    def handoff_show_cmd(handoff_id: str, as_json: bool) -> None:
        """Show one handoff JSON."""
        from handoff import HandoffError, handoff_path, load_handoff

        path = handoff_path(handoff_id)
        try:
            if not path.is_file():
                raise HandoffError(f"not found: {path}")
            data = load_handoff(path)
        except (HandoffError, OSError, json.JSONDecodeError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        click.echo(text)

    @handoff_group.command("status")
    @click.argument("handoff_id")
    @click.option(
        "--set",
        "new_status",
        required=True,
        type=click.Choice(["open", "claimed", "done", "cancelled"]),
    )
    def handoff_status_cmd(handoff_id: str, new_status: str) -> None:
        """Update handoff status."""
        from handoff import HandoffError, handoff_path, set_handoff_status

        path = handoff_path(handoff_id)
        try:
            if not path.is_file():
                raise HandoffError(f"not found: {path}")
            set_handoff_status(path, new_status)
        except (HandoffError, OSError, json.JSONDecodeError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(f"OK {handoff_id} -> {new_status}")

    @project_group.command("migrate-layout")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--slug", default=None, help="projects/<slug>/ (default: from title or stem)")
    @click.option(
        "--manifest",
        "manifest_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
        help="Legacy pipeline manifest to rewrite into projects/<slug>/pipeline/",
    )
    @click.option("--json", "as_json", is_flag=True)
    def migrate_layout_cmd(
        brief_path: Path,
        slug: str | None,
        manifest_path: Path | None,
        as_json: bool,
    ) -> None:
        """Move a flat/cli-resources brief into projects/<slug>/ (isolated layout)."""
        from project_paths import migrate_legacy_brief_to_project

        try:
            result = migrate_legacy_brief_to_project(
                brief_path,
                slug=slug,
                manifest_path=manifest_path,
            )
        except (OSError, ValueError, FileExistsError, FileNotFoundError, json.JSONDecodeError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            click.echo(f"OK → {result['brief']}")
            for k, v in (result.get("moved") or {}).items():
                click.echo(f"  {k}: {v}")
