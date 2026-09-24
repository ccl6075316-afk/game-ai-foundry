"""CLI: retained pipeline, API key, capability, and toolchain discovery."""

from __future__ import annotations

import json
import sys

import click

from env_discover import run_doctor


@click.command("doctor")
@click.option("--json", "as_json", is_flag=True, help="Print full JSON report.")
@click.pass_context
def doctor_cmd(ctx: click.Context, as_json: bool) -> None:
    """Detect pipeline readiness, API keys, capabilities, and local tools."""
    config = ctx.obj.get("config", {}) if ctx.obj else {}
    report = run_doctor(config)

    if as_json:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        return

    click.echo("Game AI Foundry — environment doctor\n")

    pipeline = report["pipeline"]
    mark = "yes" if pipeline.get("available") else "no"
    click.echo(f"Pipeline: [{mark}] {pipeline.get('reason')}")

    click.echo("\nCapabilities:")
    for key, ok in report["capabilities"].items():
        click.echo(f"  [{'yes' if ok else 'no'}] {key}")

    click.echo("\nTools:")
    for name, info in report["tools"].items():
        if info.get("available"):
            version = info.get("version") or info.get("path")
            click.echo(f"  {name:10} OK      {version}")
        else:
            click.echo(f"  {name:10} missing")

    cfg = report["config"]
    click.echo(f"\nConfig: {cfg['path']} ({'exists' if cfg['exists'] else 'missing'})")
    for key in (
        "host_key",
        "prompt_key",
        "code_key",
        "test_key",
        "seedance_key",
        "provider_accounts_key",
        "godot_engine_path",
        "toolchain_bin_dir",
        "toolchain_dotnet_dir",
    ):
        click.echo(f"  {key}: {cfg[key]}")

    if sys.platform == "win32" and not report["capabilities"]["godot_assemble"]:
        click.echo("Tip: Set godot.engine_path in ~/.gamefactory/config.json", err=True)
