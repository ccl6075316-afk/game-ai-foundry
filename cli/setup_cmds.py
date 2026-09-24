"""CLI: startup toolchain checks and provider account management."""

from __future__ import annotations

import json
import sys

import click

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
        for component_id, error in result["errors"].items():
            click.echo(f"失败 {component_id}: {error}", err=True)
        sys.exit(1)


@setup_group.group("provider")
def setup_provider_group() -> None:
    """Manage provider_accounts (confirmed write path)."""


@setup_provider_group.command("upsert")
@click.option("--provider", "provider_id", required=True, help="Account id: openrouter/deepseek/kimi/… or user slug")
@click.option("--api-key", "api_key", default=None, help="API key (prefer env GAMEFACTORY_PROVIDER_API_KEY).")
@click.option(
    "--api-key-env",
    "api_key_env",
    default=None,
    help="Env var name holding the key (default GAMEFACTORY_PROVIDER_API_KEY).",
)
@click.option("--api-base", "api_base", default=None, help="API base URL (required for user accounts).")
@click.option("--text-model", "text_model", default=None, help="Optional default text model.")
@click.option("--image-model", "image_model", default=None, help="Optional default image model.")
@click.option("--label", "label", default=None, help="Display label (user accounts).")
@click.option(
    "--kind",
    "kind",
    type=click.Choice(["builtin", "user"], case_sensitive=False),
    default=None,
    help="Account kind override (builtin ids only for builtin).",
)
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
    help="Required: user confirmed this write.",
)
@click.option("--json", "as_json", is_flag=True, help="Print JSON result (never includes raw key).")
def setup_provider_upsert_cmd(
    provider_id: str,
    api_key: str | None,
    api_key_env: str | None,
    api_base: str | None,
    text_model: str | None,
    image_model: str | None,
    label: str | None,
    kind: str | None,
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
        image_model=image_model,
        label=label,
        kind=kind,
        set_active_text=set_active_text,
        i_confirm=i_confirm,
    )
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        click.echo(
            f"已写入 {result.get('provider')}（kind={result.get('kind') or '-'}, has_api_key=yes"
            f", set_active_text={bool(result.get('set_active_text'))}）"
        )
    else:
        click.echo(f"失败: {result.get('error')}", err=True)
    if not result.get("ok"):
        sys.exit(1)


@setup_provider_group.command("list")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result (never includes raw key).")
def setup_provider_list_cmd(as_json: bool) -> None:
    """List provider_accounts entries."""
    from provider_upsert import list_provider_accounts

    result = list_provider_accounts()
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        accounts = result.get("accounts") or []
        if not accounts:
            click.echo("（无 provider_accounts 条目）")
        for item in accounts:
            click.echo(
                f"- {item.get('id')} kind={item.get('kind')} "
                f"label={item.get('label') or '-'} "
                f"has_api_key={'yes' if item.get('has_api_key') else 'no'}"
            )
    else:
        click.echo(f"失败: {result.get('error')}", err=True)
    if not result.get("ok"):
        sys.exit(1)


@setup_provider_group.command("remove")
@click.option("--provider", "provider_id", required=True, help="Account id to remove.")
@click.option(
    "--i-confirm",
    "i_confirm",
    is_flag=True,
    help="Required: user confirmed this deletion.",
)
@click.option("--json", "as_json", is_flag=True, help="Print JSON result.")
def setup_provider_remove_cmd(
    provider_id: str,
    i_confirm: bool,
    as_json: bool,
) -> None:
    """Remove provider_accounts entry after reference guard."""
    from provider_upsert import remove_provider_account

    result = remove_provider_account(
        provider=provider_id,
        i_confirm=i_confirm,
    )
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        click.echo(f"已删除 {result.get('provider')}")
    else:
        click.echo(f"失败: {result.get('error')}", err=True)
    if not result.get("ok"):
        sys.exit(1)


@setup_provider_group.command("models")
@click.option("--provider", "provider_id", required=True, help="Account id to fetch models for.")
@click.option("--api-key", "api_key_override", default=None, help="Preview key (not saved).")
@click.option("--api-base", "api_base_override", default=None, help="Preview api_base (not saved).")
@click.option("--json", "as_json", is_flag=True, help="Print JSON result (never includes raw key).")
def setup_provider_models_cmd(
    provider_id: str,
    api_key_override: str | None,
    api_base_override: str | None,
    as_json: bool,
) -> None:
    """Fetch OpenAI-compatible /models for a provider account."""
    from provider_models import fetch_provider_models

    result = fetch_provider_models(
        provider=provider_id,
        api_key_override=api_key_override,
        api_base_override=api_base_override,
    )
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        models = result.get("models") or []
        click.echo(f"{result.get('provider')}: {len(models)} 个模型")
    else:
        click.echo(f"失败: {result.get('error')}", err=True)
    if not result.get("ok"):
        sys.exit(1)
