"""CLI commands for the prompt-crafter agent only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from asset_pipeline import (
    AssetType,
    build_animation_pipeline,
    build_prompt,
    build_prompt_scaffold,
    find_asset,
    load_brief,
)
from plan_io import build_handoff, build_video_handoff, save_handoff
from prompt_craft import PromptCraftError
from shared_context import build_role_context


def register_prompt_commands(prompt_group: click.Group, resolve_prompt_api_settings) -> None:
    """Attach prompt-crafter commands to the CLI group."""

    @prompt_group.command("scaffold")
    @click.option("--brief", "brief_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option("--asset", default=None, help="Single asset (default: all).")
    @click.option("--animation", is_flag=True, help="Animation pipeline metadata.")
    @click.pass_context
    def scaffold_cmd(ctx: click.Context, brief_path: Path, asset: str | None, animation: bool) -> None:
        """Pipeline/validation metadata only — no LLM, no prompt text."""
        config = ctx.obj.get("config", {}) if ctx.obj else {}
        try:
            project, assets = load_brief(brief_path)
            if asset:
                spec = find_asset(assets, asset)
                if animation or (spec.action and spec.type == AssetType.CHARACTER):
                    payload = build_animation_pipeline(
                        project, spec, assets, craft=False, config=config
                    ).to_dict()
                else:
                    payload = build_prompt_scaffold(project, spec).to_dict()
                click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                payloads = []
                for spec in assets:
                    if spec.action and spec.type == AssetType.CHARACTER:
                        payloads.append(
                            build_animation_pipeline(
                                project, spec, assets, craft=False, config=config
                            ).to_dict()
                        )
                    else:
                        payloads.append(build_prompt_scaffold(project, spec).to_dict())
                click.echo(json.dumps(payloads, indent=2, ensure_ascii=False))
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    @prompt_group.command("craft")
    @click.option("--brief", "brief_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option("--asset", required=True, help="Asset name from brief.")
    @click.option(
        "--item",
        "kit_item",
        default=None,
        help="icon_kit item label — craft a single-object prompt for that item.",
    )
    @click.option("--animation", is_flag=True, help="Craft animation/video prompt plan.")
    @click.option(
        "-o",
        "--output",
        "output_path",
        default=None,
        type=click.Path(path_type=Path),
        help="Save handoff JSON for image-generator or video-generator agent.",
    )
    @click.option("--prompt-model", default=None)
    @click.option("--api-key", default=None)
    @click.option("--api-base", default=None)
    @click.option("--proxy", default=None)
    @click.pass_context
    def craft_cmd(
        ctx: click.Context,
        brief_path: Path,
        asset: str,
        kit_item: str | None,
        animation: bool,
        output_path: Path | None,
        prompt_model: str | None,
        api_key: str | None,
        api_base: str | None,
        proxy: str | None,
    ) -> None:
        """prompt-crafter agent: LLM writes prompt → handoff file for image-generator."""
        from brief import slugify_item_label

        config = ctx.obj["config"]
        prompt_api = resolve_prompt_api_settings(
            config,
            prompt_model=prompt_model,
            api_key=api_key,
            api_base=api_base,
            proxy=proxy,
        )
        if not prompt_api["api_key"]:
            click.echo(
                "Error: prompt-crafter requires API key (config.host, config.prompt, or config.image).",
                err=True,
            )
            sys.exit(1)

        craft_kwargs = {
            "craft": True,
            "prompt_model": str(prompt_api["prompt_model"]),
            "api_key": prompt_api["api_key"],
            "api_base": prompt_api["api_base"],
            "proxy": prompt_api["proxy"],
            "config": config,
        }

        try:
            project, assets = load_brief(brief_path)
            spec = find_asset(assets, asset)
            item_label = (kit_item or "").strip() or None
            item_slug = slugify_item_label(item_label) if item_label else None
            if item_label and spec.type != AssetType.ICON_KIT:
                raise ValueError("--item is only valid for icon_kit assets")
            if item_label and item_label not in [str(x) for x in spec.items]:
                raise ValueError(
                    f"--item {item_label!r} not in icon_kit items for '{spec.name}'"
                )
            context = build_role_context(
                project,
                spec,
                kit_item=item_label,
                kit_item_slug=item_slug,
            )

            is_animation = animation or (
                spec.action and spec.type == AssetType.CHARACTER
            )
            if is_animation:
                if item_label:
                    raise ValueError("--item cannot be combined with animation craft")
                plan = build_animation_pipeline(project, spec, assets, **craft_kwargs)
            else:
                plan = build_prompt(
                    project,
                    spec,
                    craft=craft_kwargs["craft"],
                    prompt_model=craft_kwargs["prompt_model"],
                    api_key=craft_kwargs["api_key"],
                    api_base=craft_kwargs["api_base"],
                    proxy=craft_kwargs["proxy"],
                    kit_item=item_label,
                    kit_item_slug=item_slug,
                )

            if is_animation:
                if not plan.video_prompt:
                    click.echo("Error: LLM did not produce video_prompt.", err=True)
                    sys.exit(1)
                handoff = build_video_handoff(plan.to_dict(), context=context)
            else:
                if not plan.prompt:
                    click.echo("Error: LLM did not produce a prompt.", err=True)
                    sys.exit(1)
                handoff = build_handoff(plan.to_dict(), context=context)

            if output_path:
                save_handoff(output_path, handoff)
                click.echo(str(output_path.resolve()))
            else:
                click.echo(json.dumps(handoff, ensure_ascii=False, indent=2))
        except (ValueError, json.JSONDecodeError, OSError, PromptCraftError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    @prompt_group.command("craft-visual-target")
    @click.option("--brief", "brief_path", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option(
        "--variant",
        required=True,
        type=click.Choice(["a", "b", "c", "d"]),
        help="Composition variant id.",
    )
    @click.option(
        "-o",
        "--output",
        "output_path",
        default=None,
        type=click.Path(path_type=Path),
        help="Save handoff JSON for image-generator.",
    )
    @click.option("--no-craft", is_flag=True, help="Rule-based scaffold only (no LLM).")
    @click.option("--prompt-model", default=None)
    @click.option("--api-key", default=None)
    @click.option("--api-base", default=None)
    @click.option("--proxy", default=None)
    @click.pass_context
    def craft_visual_target_cmd(
        ctx: click.Context,
        brief_path: Path,
        variant: str,
        output_path: Path | None,
        no_craft: bool,
        prompt_model: str | None,
        api_key: str | None,
        api_base: str | None,
        proxy: str | None,
    ) -> None:
        """prompt-crafter: craft one Visual Target handoff for image-generator."""
        from visual_target import VisualTargetError, _load_project, build_visual_target_plan, get_variant

        config = ctx.obj.get("config", {}) if ctx.obj else {}
        try:
            var = get_variant(variant)
            plan = build_visual_target_plan(
                brief_path,
                var,
                craft=not no_craft,
                config=config,
                proxy=proxy or (ctx.obj.get("proxy") if ctx.obj else None),
            )
            from shared_context import build_visual_target_context

            context = build_visual_target_context(_load_project(brief_path), var)
            handoff = build_handoff(plan, context=context)
        except (VisualTargetError, PromptCraftError, ValueError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if output_path:
            save_handoff(output_path, handoff)
            click.echo(str(output_path.resolve()))
        else:
            click.echo(json.dumps(handoff, ensure_ascii=False, indent=2))
