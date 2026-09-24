"""Deterministic CLI commands for project briefs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import click

from brief import (
    load_brief,
    load_brief_document,
    parse_animation_graphs,
    validate_brief_for_export,
)




def register_brief_commands(cli_group: click.Group) -> None:
    @cli_group.group("brief")
    def brief_group() -> None:
        """Project brief — validate, freeze, inspect, and maintain catalog shards."""

    @brief_group.command("freeze")
    @click.option(
        "--input",
        "input_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Draft brief JSON to validate and freeze.",
    )
    @click.option(
        "-o",
        "--output",
        "output_path",
        required=True,
        type=click.Path(path_type=Path),
        help="Canonical brief JSON to write.",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print one JSON result object.")
    def freeze_cmd(input_path: Path, output_path: Path, as_json: bool) -> None:
        """Freeze a draft JSON into a canonical brief with brief_meta."""
        from brief import audit_brief_for_export, finalize_brief_export

        input_abs = str(input_path.resolve())
        output_abs = str(output_path.resolve())

        def fail(gaps: list[str]) -> None:
            if as_json:
                click.echo(json.dumps({
                    "ok": False,
                    "input": input_abs,
                    "output": output_abs,
                    "brief_meta": None,
                    "gaps": gaps,
                }, ensure_ascii=False, indent=2))
            else:
                click.echo("Brief freeze failed:", err=True)
                for gap in gaps:
                    click.echo(f"  - {gap}", err=True)
            sys.exit(1)

        try:
            data = load_brief_document(input_path)
            if not isinstance(data, dict):
                raise ValueError("--input must contain a JSON object.")
            project, assets = load_brief(input_path)
            graphs = parse_animation_graphs(data)
            gaps = audit_brief_for_export(
                project,
                assets,
                animation_graphs=graphs,
                brief_path=input_path,
            )
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            fail([str(exc)])

        if gaps:
            fail(gaps)

        try:
            brief = finalize_brief_export(data, source="manual")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(brief, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            fail([str(exc)])

        payload = {
            "ok": True,
            "input": input_abs,
            "output": output_abs,
            "brief_meta": brief["brief_meta"],
            "gaps": [],
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(output_abs)

    @brief_group.command("localize")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Brief JSON whose project intro + catalog shards to rewrite to Chinese.",
    )
    @click.option(
        "--i-confirm",
        "i_confirm",
        is_flag=True,
        help="Required confirmation for rewriting brief/shards on disk.",
    )
    @click.option(
        "--offline-map",
        "offline_map",
        type=click.Choice(["fishing"], case_sensitive=False),
        default=None,
        help=(
            "Allow fishing EN→ZH offline dictionary when host LLM is unavailable "
            "(or prefer it for fishing leftovers). Default: LLM only; fishing "
            "projects auto-enable this map when detected."
        ),
    )
    @click.option("--json", "as_json", is_flag=True, help="Print localization report as JSON.")
    @click.pass_context
    def localize_cmd(
        ctx: click.Context,
        brief_path: Path,
        i_confirm: bool,
        offline_map: str | None,
        as_json: bool,
    ) -> None:
        """One-shot rewrite of narrative fields to Chinese (host LLM; fishing offline gated)."""
        from brief_localize import (
            fishing_offline_translator,
            is_fishing_project,
            localize_brief_narratives,
            make_llm_translator,
            register_fishing_disk_summaries,
        )
        from brief_shards import project_root_for_brief_path

        if not i_confirm:
            click.echo("Error: brief localize requires --i-confirm", err=True)
            sys.exit(2)

        config = ctx.obj.get("config", {}) if ctx.obj else {}
        root = project_root_for_brief_path(brief_path)
        llm = make_llm_translator(config)
        fishing_gated = (offline_map or "").lower() == "fishing" or is_fishing_project(
            brief_path
        )

        if llm is None and not fishing_gated:
            msg = (
                "brief localize needs host LLM credentials, or an explicit "
                "--offline-map fishing (or a fishing-2d project path/title)."
            )
            if as_json:
                click.echo(
                    json.dumps(
                        {"ok": False, "error": msg, "translator": None},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                click.echo(f"Error: {msg}", err=True)
            sys.exit(2)

        if fishing_gated:
            register_fishing_disk_summaries(root)

        if llm is not None and fishing_gated:
            mode = "llm+offline_map"

            def translator(field_name: str, text: str) -> str:
                offline = fishing_offline_translator(field_name, text)
                if not str(offline).startswith("（待全文润色）"):
                    return offline
                return llm(field_name, text)

        elif llm is not None:
            mode = "llm"

            def translator(field_name: str, text: str) -> str:
                return llm(field_name, text)

        else:
            mode = "offline_map"

            def translator(field_name: str, text: str) -> str:
                return fishing_offline_translator(field_name, text)

        try:
            report = localize_brief_narratives(
                brief_path,
                translator=translator,
                i_confirm=True,
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        report = {**report, "translator": mode}
        if mode == "offline_map":
            report["note"] = (
                "Used fishing offline EN→ZH map/patterns; re-run with host LLM "
                "configured for a full prose pass."
            )
        elif mode == "llm+offline_map":
            report["note"] = (
                "Preferred fishing offline map for known strings; LLM filled leftovers."
            )

        if as_json:
            click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            click.echo(f"ok={report.get('ok')} translator={mode}")
            for p in report.get("changed_paths") or []:
                click.echo(f"  changed: {p}")
            for s in report.get("skipped") or []:
                click.echo(f"  skipped: {s}")
            if report.get("note"):
                click.echo(report["note"])
        if not report.get("ok"):
            sys.exit(2)

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
        from brief_shards import audit_intro_budgets
        from asset_sizing import audit_brief_size_warnings

        try:
            data = load_brief_document(brief_path)
            warnings = audit_intro_budgets(data)
            project, assets = load_brief(brief_path)
            graphs = parse_animation_graphs(data)
            warnings.extend(audit_brief_size_warnings(project, assets))
            gaps = audit_brief_for_export(
                project,
                assets,
                animation_graphs=graphs,
                brief_path=brief_path,
            )
            if gaps:
                if as_json:
                    click.echo(
                        json.dumps(
                            {"ok": False, "gaps": gaps, "warnings": warnings},
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                else:
                    click.echo("Brief incomplete:", err=True)
                    for gap in gaps:
                        click.echo(f"  - {gap}", err=True)
                    for w in warnings:
                        click.echo(f"  ! {w}", err=True)
                sys.exit(1)
            validate_brief_for_export(project, assets, animation_graphs=graphs)
            meta = data.get("brief_meta") if isinstance(data.get("brief_meta"), dict) else None
            payload = {
                "ok": True,
                "brief": str(brief_path.resolve()),
                "brief_meta": meta,
                "warnings": warnings,
            }
            if as_json:
                click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                click.echo(f"OK — {brief_path.resolve()}")
                for w in warnings:
                    click.echo(f"  ! {w}", err=True)
                if meta:
                    click.echo(f"  frozen_at: {meta.get('frozen_at', '?')}")
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    @brief_group.group("shard")
    def shard_group() -> None:
        """Catalog shard maintenance (migrate thick brief → thin index + shard files)."""

    @shard_group.command("migrate")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Brief JSON to migrate to catalog + on-disk shards.",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print migration report as JSON.")
    def shard_migrate_cmd(brief_path: Path, as_json: bool) -> None:
        """Extract embedded scene/system/asset bodies into shard files; leave catalog refs in brief."""
        from brief_shards import migrate_brief_to_shards

        try:
            report = migrate_brief_to_shards(brief_path, backup=True)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Migrated: {report.get('brief_path')}")
            if report.get("backup_path"):
                click.echo(f"Backup: {report['backup_path']}")
            for key in ("scenes_written", "systems_written", "assets_written"):
                items = report.get(key) or []
                if items:
                    click.echo(f"  {key}: {', '.join(items)}")

    @shard_group.command("load")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Brief JSON containing catalog refs.",
    )
    @click.option(
        "--kind",
        "kind",
        required=True,
        type=click.Choice(["scene", "system", "asset"], case_sensitive=False),
    )
    @click.option("--id", "entry_id", required=True, help="Catalog entry id.")
    @click.option("--json", "as_json", is_flag=True, help="Print shard JSON.")
    def shard_load_cmd(brief_path: Path, kind: str, entry_id: str, as_json: bool) -> None:
        """Load one shard body by catalog kind + id."""
        from brief_shards import load_shard, project_root_for_brief_path

        try:
            data = load_brief_document(brief_path)
            root = project_root_for_brief_path(brief_path)
            shard = load_shard(root, kind, entry_id, data)  # type: ignore[arg-type]
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(shard, ensure_ascii=False, indent=2))
        else:
            click.echo(json.dumps(shard, ensure_ascii=False, indent=2))

    @brief_group.command("search")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Brief JSON (catalog or legacy).",
    )
    @click.option("--q", "query", required=True, help="Search query (substring).")
    @click.option(
        "--kind",
        "kind",
        default=None,
        type=click.Choice(["scene", "system", "asset"], case_sensitive=False),
        help="Optional filter by shard kind.",
    )
    @click.option("--limit", default=20, show_default=True, type=int)
    @click.option("--json", "as_json", is_flag=True, help="Print hits as JSON.")
    def brief_search_cmd(
        brief_path: Path,
        query: str,
        kind: str | None,
        limit: int,
        as_json: bool,
    ) -> None:
        """Structured substring search over catalog labels and shard files."""
        from brief_shards import project_root_for_brief_path, search_shards

        try:
            data = load_brief_document(brief_path)
            root = project_root_for_brief_path(brief_path)
            kinds = (kind,) if kind else None
            hits = search_shards(root, data, query, kinds=kinds, limit=limit)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps({"ok": True, "hits": hits}, ensure_ascii=False, indent=2))
        else:
            if not hits:
                click.echo("No hits.")
            for hit in hits:
                click.echo(
                    f"{hit['kind']}:{hit['id']} score={hit['score']} — {hit.get('snippet') or ''}"
                )

    @brief_group.command("related")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Brief JSON (catalog or legacy).",
    )
    @click.option(
        "--kind",
        required=True,
        type=click.Choice(["scene", "system", "asset"], case_sensitive=False),
    )
    @click.option("--id", "entry_id", required=True)
    @click.option("--limit", default=12, show_default=True, type=int)
    @click.option("--json", "as_json", is_flag=True)
    def brief_related_cmd(
        brief_path: Path,
        kind: str,
        entry_id: str,
        limit: int,
        as_json: bool,
    ) -> None:
        """Related catalog entries for one focus (declared refs + id mentions)."""
        from brief_shards import project_root_for_brief_path, related_shards

        try:
            data = load_brief_document(brief_path)
            root = project_root_for_brief_path(brief_path)
            related = related_shards(root, data, kind, entry_id, limit=limit)  # type: ignore[arg-type]
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps({"ok": True, "related": related}, ensure_ascii=False, indent=2))
        else:
            if not related:
                click.echo("No related entries.")
            for item in related:
                via = ",".join(item.get("via") or [])
                click.echo(
                    f"{item['kind']}:{item['id']} via={via} — {item.get('title') or ''}"
                )

    @brief_group.command("ui-wireframe")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(path_type=Path),
        help="brief.json, brief.draft.json, or directory containing them.",
    )
    @click.option(
        "--draft",
        "prefer_draft",
        is_flag=True,
        help="Read brief.draft.json beside --brief (not exported brief.json).",
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def ui_wireframe_cmd(
        ctx: click.Context,
        brief_path: Path,
        prefer_draft: bool,
        as_json: bool,
    ) -> None:
        """Write ui-wireframe.md from on-disk brief/draft ui_panels."""
        from ui_wireframe import (
            generate_ui_wireframe,
            load_brief_for_wireframe,
            project_dir_for_brief_path,
        )

        config = ctx.obj.get("config", {}) if ctx.obj else {}
        try:
            draft = load_brief_for_wireframe(brief_path, prefer_draft=prefer_draft)
            project_dir = project_dir_for_brief_path(brief_path)
            result = generate_ui_wireframe(draft, project_dir, config=config)
        except (OSError, json.JSONDecodeError, ValueError, FileNotFoundError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result.get("ok"):
                click.echo(result["path"])
                click.echo(f"panels: {result.get('panel_count', 0)}")
            else:
                click.echo(result.get("error") or "ui-wireframe failed", err=True)
        if not result.get("ok"):
            sys.exit(1)

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
        "--scene",
        "scene_id",
        default=None,
        help="Optional project.scenes[].id — generate a north-star for that screen.",
    )
    @click.option(
        "--output-dir",
        "output_dir",
        default=None,
        type=click.Path(path_type=Path),
        help="Output folder (default: ../output/<slug>/visual-target[/<scene>]).",
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
        scene_id: str | None,
        output_dir: Path | None,
        dry_run: bool,
        no_craft: bool,
        as_json: bool,
    ) -> None:
        """Generate 1–4 predicted gameplay screenshots (prompt-crafter → image-generator)."""
        from visual_target import VisualTargetError, default_output_dir, generate_visual_targets

        config = ctx.obj.get("config", {}) if ctx.obj else {}
        proxy = ctx.obj.get("proxy") if ctx.obj else None
        sid = (scene_id or "").strip() or None
        out = output_dir or default_output_dir(brief_path, scene_id=sid)
        try:
            manifest = generate_visual_targets(
                brief_path,
                out,
                count=candidates,
                config=config,
                proxy=proxy,
                dry_run=dry_run,
                craft=not no_craft,
                scene_id=sid,
            )
        except (VisualTargetError, RuntimeError, ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(manifest, ensure_ascii=False, indent=2))
        else:
            if sid:
                click.echo(f"Scene: {sid}")
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
    @click.option(
        "--scene",
        "scene_id",
        default=None,
        help="Optional scene id (reads visual-target/<scene>/manifest.json).",
    )
    @click.option("--json", "as_json", is_flag=True)
    def visual_target_list_cmd(
        manifest_path: Path | None,
        brief_path: Path | None,
        scene_id: str | None,
        as_json: bool,
    ) -> None:
        """List visual-target candidates from manifest."""
        from visual_target import (
            VisualTargetError,
            find_manifest_for_brief,
            load_visual_target_manifest,
        )

        sid = (scene_id or "").strip() or None
        try:
            if manifest_path is None:
                if brief_path is None:
                    click.echo("Error: pass --manifest or --brief.", err=True)
                    sys.exit(1)
                # Same resolution as pick (global when --scene omitted).
                manifest_path = find_manifest_for_brief(
                    brief_path, None, scene_id=sid
                )
            manifest = load_visual_target_manifest(manifest_path)
        except (VisualTargetError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            # Surface which file was chosen so the CLI sees the list/pick target.
            payload = dict(manifest)
            payload["manifest_path"] = str(Path(manifest_path).resolve())
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Manifest: {Path(manifest_path).resolve()}")
            sel = manifest.get("selected_id") or "(none)"
            click.echo(f"Selected: {sel}")
            if manifest.get("scene_id"):
                click.echo(f"Scene: {manifest.get('scene_id')}")
            for c in manifest.get("candidates", []):
                if isinstance(c, dict):
                    click.echo(f"  [{c.get('id')}] {c.get('label')} — {c.get('path')}")

    @visual_target_group.command("status")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--json", "as_json", is_flag=True)
    def visual_target_status_cmd(brief_path: Path, as_json: bool) -> None:
        """Show global + per-scene north-star readiness on the brief."""
        from visual_target import VisualTargetError, visual_target_brief_status

        try:
            st = visual_target_brief_status(brief_path)
        except (VisualTargetError, json.JSONDecodeError, OSError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        if as_json:
            click.echo(json.dumps(st, ensure_ascii=False, indent=2))
        else:
            click.echo(
                f"ready={st.get('ready')} global={st.get('global_ready')} "
                f"ref={st.get('visual_reference') or '(none)'}"
            )
            for sc in st.get("scenes") or []:
                mark = "ok" if sc.get("ready") else "—"
                click.echo(
                    f"  [{mark}] {sc.get('id')} {sc.get('title') or ''} "
                    f"→ {sc.get('visual_reference') or '(none)'}"
                )

    @visual_target_group.command("pick")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option("--id", "candidate_id", required=True, help="Candidate id (a, b, c, d).")
    @click.option(
        "--scene",
        "scene_ids",
        multiple=True,
        help="Scene id(s) to write the same visual_reference (repeatable).",
    )
    @click.option(
        "--manifest",
        "manifest_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option(
        "--auto-match/--no-auto-match",
        default=True,
        show_default=True,
        help="Also assign empty scenes whose description matches the candidate prompt.",
    )
    @click.option("--json", "as_json", is_flag=True)
    @click.pass_context
    def visual_target_pick_cmd(
        ctx: click.Context,
        brief_path: Path,
        candidate_id: str,
        scene_ids: tuple[str, ...],
        manifest_path: Path | None,
        auto_match: bool,
        as_json: bool,
    ) -> None:
        """Select a candidate; optional --scene may be repeated to share one north star."""
        from visual_target import VisualTargetError, apply_visual_target_pick, find_manifest_for_brief

        sids = [s.strip() for s in scene_ids if str(s).strip()]
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        proxy = ctx.obj.get("proxy") if ctx.obj else None
        try:
            manifest = find_manifest_for_brief(
                brief_path,
                manifest_path,
                scene_ids=sids or None,
            )
            result = apply_visual_target_pick(
                brief_path,
                candidate_id,
                manifest,
                scene_ids=sids or None,
                auto_match_scenes=auto_match,
                config=config,
                proxy=proxy,
            )
        except (VisualTargetError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            applied = result.get("scene_ids") or []
            if applied:
                click.echo(
                    f"scenes[{', '.join(applied)}].visual_reference → {result['visual_reference']}"
                )
            else:
                click.echo(f"visual_reference → {result['visual_reference']}")
            auto = result.get("auto_matched_scene_ids") or []
            if auto:
                click.echo(
                    f"auto-matched ({result.get('auto_match_method') or '?'}): {', '.join(auto)}"
                )
            click.echo(f"Brief updated: {result['brief_path']}")

    @visual_target_group.command("assign")
    @click.option(
        "--brief",
        "brief_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
    )
    @click.option(
        "--scene",
        "scene_ids",
        multiple=True,
        required=True,
        help="Target scene id(s) that should share the north star (repeatable).",
    )
    @click.option(
        "--from-scene",
        "from_scene",
        default=None,
        help="Copy visual_reference path from this scene (no file copy).",
    )
    @click.option(
        "--from-global",
        is_flag=True,
        help="Copy path from project.visual_reference.",
    )
    @click.option(
        "--ref",
        "ref_path",
        default=None,
        help="Explicit image path to write onto the target scenes.",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="Overwrite scenes that already have a different visual_reference.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def visual_target_assign_cmd(
        brief_path: Path,
        scene_ids: tuple[str, ...],
        from_scene: str | None,
        from_global: bool,
        ref_path: str | None,
        force: bool,
        as_json: bool,
    ) -> None:
        """Share one existing north-star path across multiple scenes."""
        from visual_target import VisualTargetError, assign_visual_reference_to_scenes

        sids = [s.strip() for s in scene_ids if str(s).strip()]
        try:
            result = assign_visual_reference_to_scenes(
                brief_path,
                scene_ids=sids,
                from_scene=(from_scene or "").strip() or None,
                from_global=from_global,
                ref=(ref_path or "").strip() or None,
                overwrite=force,
            )
        except (VisualTargetError, json.JSONDecodeError, OSError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            click.echo(
                f"assigned scenes[{', '.join(result['scene_ids'])}] "
                f"← {result['source']} → {result['visual_reference']}"
            )
            skipped = result.get("skipped_scene_ids") or []
            if skipped:
                click.echo(f"skipped (already set; use --force): {', '.join(skipped)}")
            click.echo(f"Brief updated: {result['brief_path']}")
