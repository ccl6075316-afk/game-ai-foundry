"""CLI: environment discovery (Hermes / Codex / Cursor / toolchain)."""

from __future__ import annotations

import json
import sys

import click

from env_discover import run_doctor


@click.command("doctor")
@click.option("--json", "as_json", is_flag=True, help="Print full JSON report.")
@click.pass_context
def doctor_cmd(ctx: click.Context, as_json: bool) -> None:
    """Detect local executors and toolchain before configuring agents.

    Hermes, Codex, and Cursor are not shipped with this repo — this command
    probes PATH, Hermes skill install dir, config keys, and Godot/dotnet/ffmpeg.
    """
    config = ctx.obj.get("config", {}) if ctx.obj else {}
    report = run_doctor(config)

    if as_json:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        return

    caps = report["capabilities"]
    click.echo("Game AI Foundry — environment doctor\n")

    click.echo("Capabilities:")
    for key, ok in caps.items():
        mark = "yes" if ok else "no"
        click.echo(f"  [{mark}] {key}")

    click.echo("\nExecutors (not bundled — detected on this machine):")
    for name, info in report["executors"].items():
        status = "OK" if info.get("available") else "missing"
        extra = info.get("cli") or info.get("reason") or ""
        click.echo(f"  {name:10} {status:7} {extra}")
        for hint in info.get("hints") or []:
            click.echo(f"             → {hint}")

    click.echo("\nTools:")
    for name, info in report["tools"].items():
        if info.get("available"):
            ver = info.get("version") or info.get("path")
            click.echo(f"  {name:10} OK      {ver}")
        else:
            click.echo(f"  {name:10} missing")

    cfg = report["config"]
    click.echo(f"\nConfig: {cfg['path']} ({'exists' if cfg['exists'] else 'missing'})")
    for k in ("openrouter_key", "seedance_key", "godot_engine_path"):
        click.echo(f"  {k}: {cfg[k]}")

    needs_action = [
        role
        for role, a in report["agents"].items()
        if a.get("action_required")
    ]
    if needs_action:
        click.echo("\nAgents needing executor fallback or install:")
        for role in needs_action:
            a = report["agents"][role]
            click.echo(
                f"  {role}: configured={a['configured_executor']} "
                f"→ suggest {a['suggested_executor']}"
            )

    if not caps["hermes_orchestration"] and not caps["cursor_sessions"]:
        click.echo(
            "\nTip: No Hermes/Cursor detected — use Cursor chat (you) or install Hermes; "
            "asset batch work still runs via `pipeline run`.",
            err=True,
        )

    if sys.platform == "win32" and not caps["godot_assemble"]:
        click.echo("Tip: Set godot.engine_path in ~/.gamefactory/config.json", err=True)
