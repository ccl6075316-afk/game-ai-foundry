"""CLI: inspect list|read — IT broad read under allowlisted roots."""

from __future__ import annotations

import json
from pathlib import Path

import click

from inspect_ops import InspectError, grep_files, list_dir, read_file, tree_dir


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


@inspect_group.command("tree")
@click.option("--path", "path", required=True, help="Directory under repo or ~/.gamefactory")
@click.option("--max-depth", default=3, show_default=True, type=int)
@click.option("--limit", default=400, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True)
def inspect_tree_cmd(path: str, max_depth: int, limit: int, as_json: bool) -> None:
    try:
        result = tree_dir(path, max_depth=max_depth, limit=limit)
    except InspectError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    click.echo(result["path"])
    for e in result["entries"]:
        indent = "  " * int(e.get("depth") or 1)
        mark = "d" if e["type"] == "dir" else "f"
        click.echo(f"{indent}[{mark}] {e['path']}")


@inspect_group.command("grep")
@click.option("--path", "path", required=True, help="File or directory under repo or ~/.gamefactory")
@click.option("--pattern", required=True, help="Python regex to search")
@click.option("--max-matches", default=80, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True)
def inspect_grep_cmd(path: str, pattern: str, max_matches: int, as_json: bool) -> None:
    try:
        result = grep_files(path, pattern, max_matches=max_matches)
    except InspectError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    click.echo(f"{result['path']}  pattern={result['pattern']}  hits={result['count']}")
    for m in result["matches"]:
        click.echo(f"  {m['path']}:{m['line']}: {m['text']}")


def register_inspect_commands(cli: click.Group) -> None:
    cli.add_command(inspect_group)
