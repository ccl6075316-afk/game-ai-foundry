"""CLI: agent routing configuration (Hermes / Cursor / Codex / pipeline)."""

from __future__ import annotations

import json
import sys

import click

from agent_routing import all_agents, resolve_agent
from roles import ALL_ROLES


@click.group("agents")
def agents_group() -> None:
    """Show role → executor / skill routing (configurable mix)."""


@agents_group.command("show")
@click.option(
    "--discover",
    is_flag=True,
    help="Merge local executor availability (same probes as `doctor`).",
)
@click.pass_context
def show_cmd(ctx: click.Context, discover: bool) -> None:
    """List all agent roles with resolved executor and skill package."""
    config = ctx.obj.get("config", {}) if ctx.obj else {}
    agents = all_agents(config)
    if discover:
        from env_discover import discover_agents, discover_executors

        executors = discover_executors()
        agents = discover_agents(config, executors)
    click.echo(json.dumps(agents, indent=2, ensure_ascii=False))


@agents_group.command("resolve")
@click.option("--role", required=True, type=click.Choice(list(ALL_ROLES)))
@click.pass_context
def resolve_cmd(ctx: click.Context, role: str) -> None:
    """Resolve one role (for main agent delegation)."""
    config = ctx.obj.get("config", {}) if ctx.obj else {}
    try:
        resolved = resolve_agent(role, config)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    click.echo(json.dumps(resolved, indent=2, ensure_ascii=False))
