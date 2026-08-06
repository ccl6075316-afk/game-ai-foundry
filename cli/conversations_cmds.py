"""CLI: conversations list|show — read brief/IT/agent session transcripts."""

from __future__ import annotations

import json

import click

from conversations_ops import ConversationsError, list_sessions, show_session


@click.group("conversations")
def conversations_group() -> None:
    """Read conversation sessions on disk (IT / ops)."""


@conversations_group.command("list")
@click.option("--role", required=True, help="brief|it|programmer|product_host|advisor")
@click.option("--limit", default=30, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True)
def conversations_list_cmd(role: str, limit: int, as_json: bool) -> None:
    try:
        result = list_sessions(role, limit=limit)
    except ConversationsError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    click.echo(f"{result['role']} @ {result['path']} ({result['count']})")
    for s in result["sessions"]:
        click.echo(
            f"  {s.get('id')}\tmsgs={s.get('message_count', '?')}\t{s.get('updated_at') or ''}\t{s.get('title') or ''}"
        )


@conversations_group.command("show")
@click.option("--role", required=True, help="brief|it|programmer|product_host|advisor")
@click.option("--session-id", required=True, help="Session id (filename stem)")
@click.option("--tail", default=40, show_default=True, type=int, help="Last N messages")
@click.option("--json", "as_json", is_flag=True)
def conversations_show_cmd(role: str, session_id: str, tail: int, as_json: bool) -> None:
    try:
        result = show_session(role, session_id, tail=tail)
    except ConversationsError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    click.echo(f"{result['role']} {result['id']} msgs={result['message_count']} tail={result['tail']}")
    for m in result.get("messages") or []:
        if not isinstance(m, dict):
            continue
        role_m = m.get("role") or "?"
        content = str(m.get("content") or m.get("text") or "")
        click.echo(f"\n[{role_m}]\n{content[:2000]}")


def register_conversations_commands(cli: click.Group) -> None:
    cli.add_command(conversations_group)
