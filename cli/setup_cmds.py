"""CLI: startup toolchain check and optional auto-install."""

from __future__ import annotations

import json
import sys

import click

from executor_setup import all_executor_status, run_executor_step
from toolchain_setup import check_toolchain, ensure_components, install_component


@click.group("setup")
def setup_group() -> None:
    """Check or install local toolchain pieces (ffmpeg, godot, dotnet)."""


@setup_group.command("check")
@click.option("--json", "as_json", is_flag=True, help="Print JSON report.")
def setup_check_cmd(as_json: bool) -> None:
    """List missing pipeline tools and recommended download actions."""
    report = check_toolchain()
    if as_json:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        return

    click.echo("Game AI Foundry — toolchain check\n")
    for item in report["components"]:
        mark = "OK" if item["available"] else "缺失"
        req = "必需" if item["required"] else "可选"
        click.echo(f"  [{mark}] {item['label']} ({req}) — {item['action']}")
        if item.get("path"):
            click.echo(f"         {item['path']}")

    if report["missing_required"]:
        click.echo(f"\n缺少必需项: {', '.join(report['missing_required'])}", err=True)
    if report["missing_optional"]:
        click.echo(f"缺少可选项: {', '.join(report['missing_optional'])}")


@setup_group.command("install")
@click.argument("component_id")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
def setup_install_cmd(component_id: str, as_json: bool) -> None:
    """Auto-install a component (ffmpeg, godot, dotnet)."""
    try:

        def _progress(msg: str) -> None:
            if not as_json:
                click.echo(msg, err=True)
            else:
                click.echo(json.dumps({"progress": msg}, ensure_ascii=False), err=True)

        result = install_component(component_id, progress=_progress)
        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            click.echo(f"已安装 {component_id}")
    except Exception as exc:
        if as_json:
            click.echo(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            sys.exit(1)
        raise click.ClickException(str(exc)) from exc


@setup_group.command("ensure")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
@click.option(
    "--only",
    multiple=True,
    help="Limit to component ids (ffmpeg, godot, dotnet). Default: all auto.",
)
def setup_ensure_cmd(as_json: bool, only: tuple[str, ...]) -> None:
    """Detect missing auto-install components and install them."""

    def _progress(msg: str) -> None:
        if not as_json:
            click.echo(msg, err=True)
        else:
            click.echo(json.dumps({"progress": msg}, ensure_ascii=False), err=True)

    result = ensure_components(list(only) if only else None, progress=_progress)
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            sys.exit(1)
        return

    if result["installed"]:
        click.echo(f"已安装: {', '.join(result['installed'])}")
    if result["skipped"]:
        click.echo(f"已就绪: {', '.join(result['skipped'])}")
    if result["errors"]:
        for cid, err in result["errors"].items():
            click.echo(f"失败 {cid}: {err}", err=True)
        sys.exit(1)


@setup_group.group("executor")
def setup_executor_group() -> None:
    """Step-by-step setup for Codex / Hermes / Cursor executors."""


@setup_executor_group.command("status")
@click.option("--json", "as_json", is_flag=True, help="Print JSON report.")
def setup_executor_status_cmd(as_json: bool) -> None:
    """Show install/login/configure progress for each executor."""
    report = all_executor_status()
    if as_json:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        return

    click.echo("Game AI Foundry — executor setup\n")
    for info in report["executors"].values():
        mark = "就绪" if info["ready"] else "未完成"
        click.echo(f"  [{mark}] {info['label']}")
        for step in info["steps"]:
            sm = "OK" if step["done"] else ("→" if step.get("active") else "…")
            click.echo(f"      [{sm}] {step['label']}")


@setup_executor_group.command("step")
@click.argument("executor_id")
@click.argument("step_id")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
def setup_executor_step_cmd(executor_id: str, step_id: str, as_json: bool) -> None:
    """Run one executor setup step (install_cli, login, configure_api, …)."""
    try:

        def _progress(msg: str) -> None:
            if not as_json:
                click.echo(msg, err=True)
            else:
                click.echo(json.dumps({"progress": msg}, ensure_ascii=False), err=True)

        result = run_executor_step(executor_id, step_id, progress=_progress)
        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            click.echo(f"完成 {executor_id}/{step_id}")
    except Exception as exc:
        if as_json:
            click.echo(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            sys.exit(1)
        raise click.ClickException(str(exc)) from exc
