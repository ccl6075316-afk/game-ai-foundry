"""CLI: agent routing + GUI colleague agent turns (executor CLI)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click

from agent_routing import all_agents, resolve_agent
from agent_turn import (
    AgentTurnError,
    ROLE_KINDS,
    run_turn,
    session_status,
)
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


def register_agent_commands(cli_group: click.Group) -> None:
    @cli_group.group("agent")
    def agent_group() -> None:
        """GUI colleague Agent turns (executor CLI, not desktop apps)."""

    @agent_group.command("turn")
    @click.option(
        "--role",
        "role_kind",
        type=click.Choice(sorted(ROLE_KINDS)),
        required=True,
        help="GUI colleague role: product_host | programmer | it",
    )
    @click.option("--session-id", required=True, help="GUI session / conversation id")
    @click.option("--message", "-m", required=True, help="User message")
    @click.option(
        "--executor",
        type=click.Choice(["hermes", "codex", "cursor", "pi"]),
        default=None,
        help="Override config.agents.*.executor",
    )
    @click.option("--brief", "brief_path", type=click.Path(path_type=Path), default=None)
    @click.option("--progress", "progress_path", type=click.Path(path_type=Path), default=None)
    @click.option(
        "--instance-id",
        default=None,
        help="Current GUI colleague instance id (programmer: filter handoffs).",
    )
    @click.option(
        "--target-instance-id",
        default=None,
        help="Default programmer instance for product_host dispatch.",
    )
    @click.option(
        "--roster-json",
        default=None,
        help='JSON array of programmers: [{"id":"...","display_name":"..."}]',
    )
    @click.option("--timeout", default=600, show_default=True, type=int)
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def turn_cmd(
        ctx: click.Context,
        role_kind: str,
        session_id: str,
        message: str,
        executor: str | None,
        brief_path: Path | None,
        progress_path: Path | None,
        instance_id: str | None,
        target_instance_id: str | None,
        roster_json: str | None,
        timeout: int,
        as_json: bool,
    ) -> None:
        """Send one user message to the configured executor CLI and print the reply."""
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        roster: list[dict[str, str]] | None = None
        if roster_json:
            try:
                parsed = json.loads(roster_json)
            except json.JSONDecodeError as exc:
                click.echo(f"Error: invalid --roster-json: {exc}", err=True)
                sys.exit(1)
            if isinstance(parsed, list):
                roster = [
                    {
                        "id": str(r.get("id") or ""),
                        "display_name": str(r.get("display_name") or r.get("id") or ""),
                    }
                    for r in parsed
                    if isinstance(r, dict) and r.get("id")
                ]
        try:
            result = run_turn(
                role_kind=role_kind,
                session_id=session_id,
                message=message,
                config=config,
                executor=executor,
                brief_path=brief_path,
                progress_path=progress_path,
                timeout=timeout,
                instance_id=instance_id,
                programmer_roster=roster,
                default_target_instance_id=target_instance_id,
            )
        except AgentTurnError as exc:
            payload = {"ok": False, "status": "error", "error": str(exc)}
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        except subprocess.TimeoutExpired as exc:
            payload = {
                "ok": False,
                "status": "error",
                "error": f"executor timed out after {exc.timeout}s",
            }
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(f"Error: {payload['error']}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            click.echo(result["assistant_message"])

    @agent_group.command("status")
    @click.option("--role", "role_kind", type=click.Choice(sorted(ROLE_KINDS)), required=True)
    @click.option("--session-id", required=True)
    @click.option("--json", "as_json", is_flag=True)
    def status_cmd(role_kind: str, session_id: str, as_json: bool) -> None:
        """Show agent conversation session summary."""
        try:
            payload = session_status(role_kind, session_id)
        except AgentTurnError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        click.echo(text)
