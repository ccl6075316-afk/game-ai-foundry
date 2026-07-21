"""CLI commands for brief brainstorming."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from brief import load_brief, load_brief_document, parse_animation_graphs, validate_brief_for_export
from brief_brainstorm import (
    BriefBrainstormError,
    export_brief,
    load_session,
    new_session,
    run_turn,
    save_session,
    session_status,
)
from host_chat import (
    DEFAULT_AUTOFIX_MAX_ROUNDS,
    HostChatError,
    export_brief as host_export_brief,
    list_sessions as host_list_sessions,
    load_session as host_load_session,
    new_session as host_new_session,
    run_autofix as host_run_autofix,
    run_turn as host_run_turn,
    save_session as host_save_session,
    session_path_for_id,
    session_status as host_session_status,
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

    @brief_group.group("chat")
    def chat_group() -> None:
        """Brief Tab host-chat (default chat; 落实 → commit-brief)."""

    def _chat_session_path(session_id: str | None, session_path: Path | None) -> Path:
        if session_path is not None:
            return session_path
        if not session_id:
            raise click.UsageError("Pass --session-id or -s/--session.")
        return session_path_for_id(session_id)

    @chat_group.command("start")
    @click.option("--seed", default=None, help="Optional first user message.")
    @click.option("--session-id", default=None, help="Session id (file under plans/conversations/brief/).")
    @click.option(
        "-s",
        "--session",
        "session_path",
        default=None,
        type=click.Path(path_type=Path),
        help="Explicit session JSON path (overrides --session-id).",
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def chat_start_cmd(
        ctx: click.Context,
        seed: str | None,
        session_id: str | None,
        session_path: Path | None,
        as_json: bool,
    ) -> None:
        """Start or restart a host-chat session."""
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        if session_path is not None:
            path = session_path
            sid = session_id or path.stem
        elif session_id:
            path = session_path_for_id(session_id)
            sid = session_id
        else:
            session = host_new_session()
            sid = str(session["id"])
            path = session_path_for_id(sid)
            try:
                result = host_run_turn(session, user_message=seed, config=config)
                host_save_session(path, session)
            except (HostChatError, PromptCraftError) as exc:
                click.echo(f"Error: {exc}", err=True)
                sys.exit(1)
            payload = {
                "session_id": session.get("id"),
                "session_path": str(path.resolve()),
                **result,
            }
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(result["assistant_message"])
                for i, c in enumerate(result.get("choices") or [], 1):
                    click.echo(f"  {i}. {c}")
            return

        session = host_new_session(sid)
        try:
            result = host_run_turn(session, user_message=seed, config=config)
            host_save_session(path, session)
        except (HostChatError, PromptCraftError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {
            "session_id": session.get("id"),
            "session_path": str(path.resolve()),
            **result,
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(result["assistant_message"])
            for i, c in enumerate(result.get("choices") or [], 1):
                click.echo(f"  {i}. {c}")

    @chat_group.command("reset")
    @click.option("--seed", default=None)
    @click.option("--session-id", default=None)
    @click.option("-s", "--session", "session_path", default=None, type=click.Path(path_type=Path))
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def chat_reset_cmd(
        ctx: click.Context,
        seed: str | None,
        session_id: str | None,
        session_path: Path | None,
        as_json: bool,
    ) -> None:
        """Discard and restart a host-chat session."""
        ctx.invoke(
            chat_start_cmd,
            seed=seed,
            session_id=session_id,
            session_path=session_path,
            as_json=as_json,
        )

    @chat_group.command("turn")
    @click.option("--message", "-m", required=True, help="User reply.")
    @click.option("--session-id", default=None)
    @click.option(
        "-s",
        "--session",
        "session_path",
        default=None,
        type=click.Path(path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--instance-id",
        default=None,
        help="GUI colleague instance id (per-instance Provider/model for Pi).",
    )
    @click.pass_context
    def chat_turn_cmd(
        ctx: click.Context,
        message: str,
        session_id: str | None,
        session_path: Path | None,
        as_json: bool,
        instance_id: str | None,
    ) -> None:
        """Send one user message in host-chat."""
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        path = _chat_session_path(session_id, session_path)
        try:
            session = host_load_session(path)
            result = host_run_turn(
                session,
                user_message=message,
                config=config,
                instance_id=instance_id,
            )
            host_save_session(path, session)
        except (HostChatError, PromptCraftError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {
            "session_id": session.get("id"),
            "session_path": str(path.resolve()),
            **result,
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(result["assistant_message"])
            for i, c in enumerate(result.get("choices") or [], 1):
                click.echo(f"  {i}. {c}")
            if result.get("ready_to_export"):
                click.echo("\n[ready] Brief 可导出 — 使用 brief chat export")

    @chat_group.command("status")
    @click.option("--session-id", default=None)
    @click.option("-s", "--session", "session_path", default=None, type=click.Path(path_type=Path))
    @click.option("--json", "as_json", is_flag=True)
    def chat_status_cmd(session_id: str | None, session_path: Path | None, as_json: bool) -> None:
        """Show host-chat session summary."""
        try:
            path = _chat_session_path(session_id, session_path)
            if not path.is_file():
                payload = {"exists": False, "session_id": session_id or path.stem, "session_path": str(path)}
            else:
                session = host_load_session(path)
                payload = {
                    "session_path": str(path.resolve()),
                    **host_session_status(session),
                }
        except (HostChatError, click.UsageError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))

    @chat_group.command("list")
    @click.option("--json", "as_json", is_flag=True)
    def chat_list_cmd(as_json: bool) -> None:
        """List Brief Tab host-chat sessions on disk."""
        items = host_list_sessions()
        payload = {"sessions": items, "count": len(items)}
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            if not items:
                click.echo("(no sessions)")
                return
            for item in items:
                click.echo(f"{item['id']}\t{item['message_count']} msgs\t{item['title']}")

    @chat_group.command("autofix")
    @click.option("--session-id", default=None)
    @click.option("-s", "--session", "session_path", default=None, type=click.Path(path_type=Path))
    @click.option(
        "--max-rounds",
        default=DEFAULT_AUTOFIX_MAX_ROUNDS,
        show_default=True,
        type=int,
        help="Stop after this many LLM fix turns (or sooner if clean / stuck).",
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def chat_autofix_cmd(
        ctx: click.Context,
        session_id: str | None,
        session_path: Path | None,
        max_rounds: int,
        as_json: bool,
    ) -> None:
        """Read validator gaps and ask the host LLM to fix the draft until clean."""
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        try:
            path = _chat_session_path(session_id, session_path)
            session = host_load_session(path)
            result = host_run_autofix(session, config=config, max_rounds=max_rounds)
            host_save_session(path, session)
        except (HostChatError, PromptCraftError, click.UsageError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {
            "session_id": session.get("id"),
            "session_path": str(path.resolve()),
            **result,
            **{k: v for k, v in host_session_status(session).items() if k not in result},
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(result.get("assistant_message") or result.get("reason"))
            click.echo(f"ok={result.get('ok')} rounds={result.get('rounds_run')} gaps={len(result.get('gaps') or [])}")
            for g in result.get("gaps") or []:
                click.echo(f"  - {g}")
        if not result.get("ok"):
            sys.exit(2)

    @chat_group.command("export")
    @click.option("--session-id", default=None)
    @click.option("-s", "--session", "session_path", default=None, type=click.Path(path_type=Path))
    @click.option(
        "-o",
        "--output",
        "output_path",
        required=True,
        type=click.Path(path_type=Path),
        help="Write validated brief JSON.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def chat_export_cmd(
        session_id: str | None,
        session_path: Path | None,
        output_path: Path,
        as_json: bool,
    ) -> None:
        """Export draft brief from a host-chat session."""
        try:
            path = _chat_session_path(session_id, session_path)
            session = host_load_session(path)
            brief = host_export_brief(session)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(brief, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except (HostChatError, ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        payload = {
            "session_id": session.get("id"),
            "brief_path": str(output_path.resolve()),
            "brief": brief,
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(str(output_path.resolve()))

    @brief_group.command("validate")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Brief JSON to validate (export/plan gate).",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print audit result as JSON.")
    def validate_cmd(brief_path: Path, as_json: bool) -> None:
        """Check that a brief is complete — the frozen contract for all downstream steps."""
        from brief import audit_brief_for_export

        try:
            project, assets = load_brief(brief_path)
            data = load_brief_document(brief_path)
            graphs = parse_animation_graphs(data)
            gaps = audit_brief_for_export(project, assets, animation_graphs=graphs)
            if gaps:
                if as_json:
                    click.echo(json.dumps({"ok": False, "gaps": gaps}, ensure_ascii=False, indent=2))
                else:
                    click.echo("Brief incomplete:", err=True)
                    for gap in gaps:
                        click.echo(f"  - {gap}", err=True)
                sys.exit(1)
            validate_brief_for_export(project, assets, animation_graphs=graphs)
            data = json.loads(brief_path.read_text(encoding="utf-8"))
            meta = data.get("brief_meta") if isinstance(data.get("brief_meta"), dict) else None
            payload = {"ok": True, "brief": str(brief_path.resolve()), "brief_meta": meta}
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(f"OK — {brief_path.resolve()}")
                if meta:
                    click.echo(f"  frozen_at: {meta.get('frozen_at', '?')}")
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

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

    @brief_group.group("visual-target")
    def visual_target_group() -> None:
        """Predicted in-game frames (godogen Visual Target) — generate, pick, list."""

    @visual_target_group.command("generate")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option(
        "--candidates",
        default=3,
        show_default=True,
        type=click.IntRange(1, 4),
        help="Number of composition variants (max 4).",
    )
    @click.option(
        "--output-dir",
        "output_dir",
        default=None,
        type=click.Path(path_type=Path),
        help="Output folder (default: ../output/<slug>/visual-target).",
    )
    @click.option("--dry-run", is_flag=True, help="Write handoffs + manifest only; no image API.")
    @click.option(
        "--no-craft",
        is_flag=True,
        help="Rule-based prompts only (skip prompt-crafter LLM).",
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def visual_target_generate_cmd(
        ctx: click.Context,
        brief_path: Path,
        candidates: int,
        output_dir: Path | None,
        dry_run: bool,
        no_craft: bool,
        as_json: bool,
    ) -> None:
        """Generate 1–4 predicted gameplay screenshots (prompt-crafter → image-generator)."""
        from visual_target import VisualTargetError, default_output_dir, generate_visual_targets

        config = ctx.obj.get("config", {}) if ctx.obj else {}
        proxy = ctx.obj.get("proxy") if ctx.obj else None
        out = output_dir or default_output_dir(brief_path)
        try:
            manifest = generate_visual_targets(
                brief_path,
                out,
                count=candidates,
                config=config,
                proxy=proxy,
                dry_run=dry_run,
                craft=not no_craft,
            )
        except (VisualTargetError, RuntimeError, ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(manifest, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Manifest: {manifest['manifest_path']}")
            for c in manifest["candidates"]:
                click.echo(f"  [{c['id']}] {c['label']} → {c['path']}")
            if dry_run:
                click.echo("(dry-run — handoffs written, no images generated)")
            elif no_craft:
                click.echo("(no-craft — rule-based prompts)")

    @visual_target_group.command("list")
    @click.option(
        "--manifest",
        "manifest_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option(
        "--brief",
        "brief_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
        help="Resolve default manifest from brief slug.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def visual_target_list_cmd(
        manifest_path: Path | None,
        brief_path: Path | None,
        as_json: bool,
    ) -> None:
        """List visual-target candidates from manifest."""
        from visual_target import VisualTargetError, default_output_dir, load_visual_target_manifest

        if manifest_path is None:
            if brief_path is None:
                click.echo("Error: pass --manifest or --brief.", err=True)
                sys.exit(1)
            manifest_path = default_output_dir(brief_path) / "manifest.json"
        try:
            manifest = load_visual_target_manifest(manifest_path)
        except (VisualTargetError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(manifest, ensure_ascii=False, indent=2))
        else:
            sel = manifest.get("selected_id") or "(none)"
            click.echo(f"Selected: {sel}")
            for c in manifest.get("candidates", []):
                if isinstance(c, dict):
                    click.echo(f"  [{c.get('id')}] {c.get('label')} — {c.get('path')}")

    @visual_target_group.command("pick")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--id", "candidate_id", required=True, help="Candidate id (a, b, c, d).")
    @click.option(
        "--manifest",
        "manifest_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    def visual_target_pick_cmd(
        brief_path: Path,
        candidate_id: str,
        manifest_path: Path | None,
        as_json: bool,
    ) -> None:
        """Select a candidate and write project.visual_reference on the brief."""
        from visual_target import VisualTargetError, apply_visual_target_pick, find_manifest_for_brief

        try:
            manifest = find_manifest_for_brief(brief_path, manifest_path)
            result = apply_visual_target_pick(brief_path, candidate_id, manifest)
        except (VisualTargetError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            click.echo(f"visual_reference → {result['visual_reference']}")
            click.echo(f"Brief updated: {result['brief_path']}")
