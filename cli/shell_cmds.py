"""CLI: shell run — IT trusted shell (requires --i-confirm)."""

from __future__ import annotations

import json

import click

from shell_ops import DEFAULT_TIMEOUT_SEC, ShellError, run_shell


@click.group("shell")
def shell_group() -> None:
    """Run shell commands (IT / home-ops; requires --i-confirm)."""


@shell_group.command("run")
@click.option("--command", "command", required=True, help="Shell command string")
@click.option("--cwd", default=None, help="Working directory (repo or ~/.gamefactory)")
@click.option("--timeout", default=DEFAULT_TIMEOUT_SEC, show_default=True, type=float)
@click.option(
    "--i-confirm",
    "i_confirm",
    is_flag=True,
    help="Required confirmation for shell execution",
)
@click.option("--json", "as_json", is_flag=True)
def shell_run_cmd(
    command: str,
    cwd: str | None,
    timeout: float,
    i_confirm: bool,
    as_json: bool,
) -> None:
    if not i_confirm:
        click.echo("Error: shell run requires --i-confirm", err=True)
        raise SystemExit(1)
    try:
        result = run_shell(command, cwd=cwd, timeout_sec=timeout)
    except ShellError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"$ ({result['cwd']}) {result['command']}")
        if result.get("stdout"):
            click.echo(result["stdout"], nl=False)
            if not str(result["stdout"]).endswith("\n"):
                click.echo()
        if result.get("stderr"):
            click.echo(result["stderr"], err=True, nl=False)
            if not str(result["stderr"]).endswith("\n"):
                click.echo(err=True)
        if result.get("exit_code") not in (0, None):
            raise SystemExit(int(result["exit_code"] or 1))
        if not result.get("ok"):
            raise SystemExit(1)


def register_shell_commands(cli: click.Group) -> None:
    cli.add_command(shell_group)
