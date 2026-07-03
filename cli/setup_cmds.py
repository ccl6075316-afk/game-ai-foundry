"""CLI: startup toolchain check and optional auto-install."""

from __future__ import annotations

import json
import sys

import click

from toolchain_setup import check_toolchain, install_component


@click.group("setup")
def setup_group() -> None:
    """Check or install local toolchain pieces (ffmpeg, rembg, etc.)."""


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
    """Auto-install a component (ffmpeg or rembg). Godot/.NET use download links."""
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
