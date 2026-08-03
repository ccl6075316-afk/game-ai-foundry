"""CLI: inspect list|read — IT broad read under allowlisted roots."""

from __future__ import annotations

import json
from pathlib import Path

import click

from inspect_ops import InspectError, list_dir, read_file


@click.group("inspect")
def inspect_group() -> None:
    """Read-only filesystem inspect (IT / ops)."""


@inspect_group.command("list")
@click.option("--path", "path", required=True, help="Directory under repo or ~/.gamefactory")
@click.option("--limit", default=200, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True)
def inspect_list_cmd(path: str, limit: int, as_json: bool) -> None:
    try:
        result = list_dir(path, limit=limit)
    except InspectError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(result["path"])
        for e in result["entries"]:
            mark = "d" if e["type"] == "dir" else "f"
            size = e["size"] if e["size"] is not None else "-"
            click.echo(f"  [{mark}] {e['name']}\t{size}")


@inspect_group.command("read")
@click.option("--path", "path", required=True, help="File under repo or ~/.gamefactory")
@click.option("--max-bytes", default=200_000, show_default=True, type=int)
@click.option("--offset", default=0, type=int)
@click.option("--json", "as_json", is_flag=True)
def inspect_read_cmd(path: str, max_bytes: int, offset: int, as_json: bool) -> None:
    try:
        result = read_file(path, max_bytes=max_bytes, offset=offset)
    except InspectError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if result.get("json") is not None:
        click.echo(json.dumps(result["json"], ensure_ascii=False, indent=2))
    elif result.get("content") is not None:
        click.echo(result["content"])
    else:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))


def register_inspect_commands(cli: click.Group) -> None:
    cli.add_command(inspect_group)
