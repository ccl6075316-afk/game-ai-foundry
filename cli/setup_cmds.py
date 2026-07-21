"""CLI: startup toolchain check and optional auto-install."""

from __future__ import annotations

import json
import sys

import click

from executor_setup import all_executor_status, run_executor_step
from pi_runtime import pi_status, run_pi_smoke
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
@click.option(
    "--provider",
    "provider_id",
    default=None,
    help="Hermes configure_api / Codex sync_api: Foundry provider id (openrouter/deepseek/kimi/…).",
)
@click.option(
    "--instance-id",
    "instance_id",
    default=None,
    help="Codex sync_api: roster instance id for agents.instances overlay.",
)
def setup_executor_step_cmd(
    executor_id: str,
    step_id: str,
    as_json: bool,
    provider_id: str | None,
    instance_id: str | None,
) -> None:
    """Run one executor setup step (install_cli, login, configure_api, …)."""
    try:

        def _progress(msg: str) -> None:
            if not as_json:
                click.echo(msg, err=True)
            else:
                click.echo(json.dumps({"progress": msg}, ensure_ascii=False), err=True)

        result = run_executor_step(
            executor_id,
            step_id,
            progress=_progress,
            provider_id=provider_id,
            instance_id=instance_id,
        )
        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            click.echo(f"完成 {executor_id}/{step_id}")
            if result.get("message"):
                click.echo(result["message"])
    except Exception as exc:
        if as_json:
            click.echo(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            sys.exit(1)
        raise click.ClickException(str(exc)) from exc


@setup_group.group("pi")
def setup_pi_group() -> None:
    """Embedded Pi coding-agent (Release runtime / Spike 0)."""


@setup_pi_group.command("status")
@click.option("--json", "as_json", is_flag=True, help="Print JSON report.")
def setup_pi_status_cmd(as_json: bool) -> None:
    """Show whether embedded Pi + Node + API key are ready."""
    report = pi_status()
    if as_json:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        if not report.get("ready"):
            sys.exit(1)
        return

    mark = "就绪" if report.get("ready") else "未就绪"
    click.echo(f"Game AI Foundry — embedded Pi [{mark}]")
    click.echo(f"  package: {report.get('package')}@{report.get('pin_version')}")
    click.echo(f"  runtime: {report.get('runtime_root') or '(missing)'}")
    click.echo(f"  node:    {report.get('node') or '(missing)'}")
    auth = report.get("auth") or {}
    click.echo(
        f"  auth:    provider={auth.get('provider') or '-'} "
        f"key={'yes' if auth.get('has_api_key') else 'no'}"
    )
    if report.get("size_mb") is not None:
        click.echo(f"  size:    {report['size_mb']} MB")
    if report.get("hint"):
        click.echo(f"  hint:    {report['hint']}", err=True)
    if not report.get("ready"):
        sys.exit(1)


@setup_pi_group.command("smoke")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
@click.option("--timeout", default=90.0, show_default=True, help="Seconds before abort.")
def setup_pi_smoke_cmd(as_json: bool, timeout: float) -> None:
    """One no-tool Pi turn using config API key (Spike 0)."""
    result = run_pi_smoke(timeout_sec=timeout)
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            sys.exit(1)
        return

    if result.get("ok"):
        click.echo(f"Pi smoke OK ({result.get('provider')}/{result.get('model')})")
        out = (result.get("stdout") or "").strip()
        if out:
            click.echo(out[:500])
        return

    click.echo(f"Pi smoke FAILED: {result.get('error')}", err=True)
    if result.get("stderr"):
        click.echo(result["stderr"][-800:], err=True)
    sys.exit(1)

@setup_group.group("provider")
def setup_provider_group() -> None:
    """Manage provider_accounts (IT toolbox write path)."""


@setup_provider_group.command("upsert")
@click.option("--provider", "provider_id", required=True, help="Account id: openrouter/deepseek/kimi/…")
@click.option("--api-key", "api_key", default=None, help="API key (prefer env GAMEFACTORY_PROVIDER_API_KEY).")
@click.option(
    "--api-key-env",
    "api_key_env",
    default=None,
    help="Env var name holding the key (default GAMEFACTORY_PROVIDER_API_KEY).",
)
@click.option("--api-base", "api_base", default=None, help="Optional API base URL.")
@click.option("--text-model", "text_model", default=None, help="Optional default text model.")
@click.option(
    "--set-active-text/--no-set-active-text",
    default=True,
    show_default=True,
    help="Also switch host / current text provider to this account.",
)
@click.option(
    "--i-confirm",
    "i_confirm",
    is_flag=True,
    help="Required: user confirmed write in IT chat (or equivalent).",
)
@click.option("--json", "as_json", is_flag=True, help="Print JSON result (never includes raw key).")
def setup_provider_upsert_cmd(
    provider_id: str,
    api_key: str | None,
    api_key_env: str | None,
    api_base: str | None,
    text_model: str | None,
    set_active_text: bool,
    i_confirm: bool,
    as_json: bool,
) -> None:
    """Upsert provider_accounts entry after user confirmation."""
    from provider_upsert import upsert_provider_account

    result = upsert_provider_account(
        provider=provider_id,
        api_key=api_key,
        api_key_env=api_key_env,
        api_base=api_base,
        text_model=text_model,
        set_active_text=set_active_text,
        i_confirm=i_confirm,
    )
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        click.echo(
            f"已写入 {result.get('provider')}（has_api_key=yes"
            f", set_active_text={bool(result.get('set_active_text'))}）"
        )
    else:
        click.echo(f"失败: {result.get('error')}", err=True)
    if not result.get("ok"):
        sys.exit(1)
