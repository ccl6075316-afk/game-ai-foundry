"""CLI commands for brief brainstorming."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from brief_brainstorm import (
    BriefBrainstormError,
    export_brief,
    load_session,
    new_session,
    run_turn,
    save_session,
    session_status,
)
from prompt_craft import PromptCraftError

_DEFAULT_SESSION = Path("plans/brainstorm-session.json")


def register_brief_commands(cli_group: click.Group) -> None:
    @cli_group.group("brief")
    def brief_group() -> None:
        """Project brief — load, brainstorm, export."""

    @brief_group.group("brainstorm")
    def brainstorm_group() -> None:
        """Multi-turn requirement refinement (orchestrator-style)."""

    @brainstorm_group.command("start")
    @click.option("--seed", default=None, help="Optional initial idea in one sentence.")
    @click.option(
        "-s",
        "--session",
        "session_path",
        default=str(_DEFAULT_SESSION),
        type=click.Path(path_type=Path),
        help="Session JSON path (default: plans/brainstorm-session.json).",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print JSON for GUI.")
    @click.pass_context
    def start_cmd(ctx: click.Context, seed: str | None, session_path: Path, as_json: bool) -> None:
        """Start or restart a brainstorm session and get the first question."""
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        session = new_session()
        try:
            result = run_turn(session, user_message=seed, config=config)
            save_session(session_path, session)
        except (BriefBrainstormError, PromptCraftError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {
            "session_path": str(session_path.resolve()),
            **result,
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(result["assistant_message"])
            for i, c in enumerate(result.get("choices") or [], 1):
                click.echo(f"  {i}. {c}")

    @brainstorm_group.command("reset")
    @click.option("--seed", default=None, help="Optional initial idea.")
    @click.option(
        "-s",
        "--session",
        "session_path",
        default=str(_DEFAULT_SESSION),
        type=click.Path(path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def reset_cmd(ctx: click.Context, seed: str | None, session_path: Path, as_json: bool) -> None:
        """Discard current session and start fresh."""
        ctx.invoke(start_cmd, seed=seed, session_path=session_path, as_json=as_json)

    @brainstorm_group.command("turn")
    @click.option("--message", "-m", required=True, help="User reply.")
    @click.option(
        "-s",
        "--session",
        "session_path",
        default=str(_DEFAULT_SESSION),
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def turn_cmd(
        ctx: click.Context,
        message: str,
        session_path: Path,
        as_json: bool,
    ) -> None:
        """Send one user message and get the next brainstorm response."""
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        try:
            session = load_session(session_path)
            result = run_turn(session, user_message=message, config=config)
            save_session(session_path, session)
        except (BriefBrainstormError, PromptCraftError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {"session_path": str(session_path.resolve()), **result}
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(result["assistant_message"])
            for i, c in enumerate(result.get("choices") or [], 1):
                click.echo(f"  {i}. {c}")
            if result.get("ready_to_export"):
                click.echo("\n[ready] Brief 可导出 — 使用 brief brainstorm export")

    @brainstorm_group.command("status")
    @click.option(
        "-s",
        "--session",
        "session_path",
        default=str(_DEFAULT_SESSION),
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    def status_cmd(session_path: Path, as_json: bool) -> None:
        """Show brainstorm session summary."""
        try:
            session = load_session(session_path)
            payload = {"session_path": str(session_path.resolve()), **session_status(session)}
        except (BriefBrainstormError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))

    @brainstorm_group.command("export")
    @click.option(
        "-s",
        "--session",
        "session_path",
        default=str(_DEFAULT_SESSION),
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option(
        "-o",
        "--output",
        "output_path",
        required=True,
        type=click.Path(path_type=Path),
        help="Write validated brief JSON.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def export_cmd(session_path: Path, output_path: Path, as_json: bool) -> None:
        """Export draft brief to a brief JSON file."""
        try:
            session = load_session(session_path)
            brief = export_brief(session)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(brief, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except (BriefBrainstormError, ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {"brief_path": str(output_path.resolve()), "brief": brief}
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(str(output_path.resolve()))
