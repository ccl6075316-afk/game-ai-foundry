"""Image-first, reviewed 3D fish production commands."""
from __future__ import annotations

from pathlib import Path
import click

from volume_fish import VolumeError, accept_volume, plan_volume, run_builder, validate_volume
from volume_motion import build_motion, plan_motion, validate_motion
from workflow.contract import build_response, emit_response, make_failure


def _execute(command: str, inputs: dict, action, as_json: bool) -> None:
    try:
        data, summary = action()
        payload = build_response(command=command, ok=True, stage="assets" if command != "validate" else "validate",
                                 status="pending" if command == "plan" else "done",
                                 next_action="run" if command == "plan" else ("none" if summary.get("style_visual_review") == "accepted" else "human_review"),
                                 inputs=inputs, outputs=[inputs["output"]] if command == "plan" else [inputs["handoff"], data["outputs"]["glb"], data["outputs"]["validation_report"]] + ([data["outputs"]["render_report"]] if command == "render" else []), summary=summary)
    except Exception as exc:
        payload = build_response(command=command, ok=False, stage="assets" if command != "validate" else "validate",
                                 status=exc.status if isinstance(exc, VolumeError) else "blocked", next_action="fix_input",
                                 inputs=inputs, failures=[make_failure(exc.code if isinstance(exc, VolumeError) else "manifest_invalid", str(exc))])
    emit_response(payload, as_json=as_json)
    if not payload["ok"]:
        raise click.exceptions.Exit(1)


@click.group("volume")
def volume_group() -> None:
    """Reviewed image → textured, skinned 3D fish; visual approval stays human."""


@volume_group.command("sop-init")
@click.option("--species", required=True)
@click.option("--output", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def sop_init_cmd(species: str, output: Path, as_json: bool) -> None:
    """Create an unapproved complete fish production evidence checklist."""
    from volume_sop import initialize
    try:
        data=initialize(species,output)
        payload=build_response(command="volume.sop-init",ok=True,stage="validate",status="pending",next_action="human_review",
            inputs={"species":species},outputs=[str(output.resolve())],summary={"stages":list(data['stages']),"accepted":False})
    except Exception as exc:
        payload=build_response(command="volume.sop-init",ok=False,stage="validate",status="blocked",next_action="fix_input",failures=[make_failure("manifest_invalid",str(exc))])
    emit_response(payload,as_json=as_json)
    if not payload['ok']:raise click.exceptions.Exit(1)


@volume_group.command("sop-check")
@click.option("--review", required=True, type=click.Path(exists=True,path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def sop_check_cmd(review: Path, output: Path, as_json: bool) -> None:
    """Reject missing/stale evidence; does not run gates or approve visuals."""
    from volume_sop import check
    try:
        report=check(review,output)
        payload=build_response(command="volume.sop-check",ok=report['ok'],stage="validate",status=report['status'],next_action=report['next_action'],
            inputs={"review":str(review.resolve())},outputs=[str(output.resolve())],summary={k:report[k] for k in ['species','stages','evidence_count','scope']},
            failures=[make_failure("manifest_invalid",f['message'],check_code=f['code']) for f in report['failures']])
    except Exception as exc:
        payload=build_response(command="volume.sop-check",ok=False,stage="validate",status="blocked",next_action="fix_input",failures=[make_failure("manifest_invalid",str(exc))])
    emit_response(payload,as_json=as_json)
    if not payload['ok']:raise click.exceptions.Exit(1)


@volume_group.command("replan")
@click.option("--archive-inputs", required=True, type=click.Path(path_type=Path))
@click.option("--profile", required=True, type=click.Path(path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def replan_cmd(archive_inputs: Path, profile: Path, output: Path, as_json: bool) -> None:
    """Reuse hash-verified accepted archive pixels; create new pending outputs."""
    from volume_archive import plan_archive
    def action():
        data = plan_archive(archive_inputs, profile, output)
        return data, {"accepted_archive": data["accepted_archive"], "style_visual_review": "pending"}
    _execute("plan", {"archive_inputs": str(archive_inputs.resolve()), "profile": str(profile.resolve()), "output": str(output.resolve())}, action, as_json)


@volume_group.command("plan")
@click.option("--brief", required=True, type=click.Path(path_type=Path))
@click.option("--assets-manifest", required=True, type=click.Path(path_type=Path))
@click.option("--asset", required=True)
@click.option("--profile", required=True, type=click.Path(path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
@click.option("--front-assets-manifest", type=click.Path(path_type=Path))
@click.option("--front-asset")
@click.option("--top-assets-manifest", type=click.Path(path_type=Path))
@click.option("--top-asset")
@click.option("--bottom-assets-manifest", type=click.Path(path_type=Path))
@click.option("--bottom-asset")
@click.option("--json", "as_json", is_flag=True)
def plan_cmd(brief: Path, assets_manifest: Path, asset: str, profile: Path, output: Path,
             front_assets_manifest: Path | None, front_asset: str | None,
             top_assets_manifest: Path | None, top_asset: str | None,
             bottom_assets_manifest: Path | None, bottom_asset: str | None, as_json: bool) -> None:
    """Freeze accepted Foundry still, calibrated geometry and pixel-art style."""
    inputs = {"brief": str(brief.resolve()), "assets_manifest": str(assets_manifest.resolve()),
              "asset": asset, "profile": str(profile.resolve()), "output": str(output.resolve())}

    def action():
        data = plan_volume(brief, assets_manifest, asset, profile, output, front_assets_manifest, front_asset,
                           top_assets_manifest, top_asset, bottom_assets_manifest, bottom_asset)
        return data, {"handoff": str(output.resolve()), "source": data["source"], "style_visual_review": "pending"}
    _execute("plan", inputs, action, as_json)


@volume_group.command("build")
@click.option("--handoff", required=True, type=click.Path(path_type=Path))
@click.option("--blender", type=click.Path(path_type=Path), help="Temporary executable override; otherwise use Blender on PATH.")
@click.option("--json", "as_json", is_flag=True)
def build_cmd(handoff: Path, blender: Path | None, as_json: bool) -> None:
    """Build using the bundled Blender script after rechecking source hashes."""
    _execute("build", {"handoff": str(handoff.resolve()), "blender": str(blender) if blender else None},
             lambda: run_builder(handoff, blender), as_json)


@volume_group.command("validate")
@click.option("--handoff", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def validate_cmd(handoff: Path, as_json: bool) -> None:
    """Read-only mechanical GLB/source checks; never approves visual style."""
    _execute("validate", {"handoff": str(handoff.resolve())}, lambda: validate_volume(handoff), as_json)


@volume_group.command("render")
@click.option("--handoff", required=True, type=click.Path(path_type=Path))
@click.option("--blender", type=click.Path(path_type=Path), help="Temporary Blender executable override.")
@click.option("--json", "as_json", is_flag=True)
def render_cmd(handoff: Path, blender: Path | None, as_json: bool) -> None:
    """Render side/front/oblique and source/style comparison for human review."""
    _execute("render", {"handoff": str(handoff.resolve()), "blender": str(blender) if blender else None},
             lambda: run_builder(handoff, blender, render_only=True), as_json)


@volume_group.command("accept")
@click.option("--handoff", required=True, type=click.Path(path_type=Path))
@click.option("--note", required=True, help="Operator's visual review findings, after inspecting all review images.")
@click.option("--json", "as_json", is_flag=True)
def accept_cmd(handoff: Path, note: str, as_json: bool) -> None:
    """Record the command operator's visual review after all freshness gates."""
    _execute("accept", {"handoff": str(handoff.resolve())}, lambda: accept_volume(handoff, note), as_json)


def _motion_execute(command: str, inputs: dict, action, as_json: bool) -> None:
    try:
        data,summary = action()
        planned = command == "motion-plan"
        payload = build_response(command=command,ok=True,stage="validate" if command == "motion-validate" else "assets",
                                 status="pending" if planned else "done",next_action="run" if planned else "human_review",
                                 inputs=inputs,outputs=[inputs["output"]] if planned else [inputs["handoff"],*data["outputs"].values()],summary=summary)
    except Exception as exc:
        payload = build_response(command=command,ok=False,stage="validate" if command == "motion-validate" else "assets",
                                 status=exc.status if isinstance(exc,VolumeError) else "blocked",next_action="fix_input",inputs=inputs,
                                 failures=[make_failure(exc.code if isinstance(exc,VolumeError) else "manifest_invalid",str(exc))])
    emit_response(payload,as_json=as_json)
    if not payload["ok"]:
        raise click.exceptions.Exit(1)


@volume_group.command("motion-plan")
@click.option("--profile", "profiles", required=True, multiple=True, type=click.Path(path_type=Path), help="Repeat once for each species in the complete exhibit.")
@click.option("--models-dir", required=True, type=click.Path(path_type=Path))
@click.option("--reviews-dir", required=True, type=click.Path(path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def motion_plan_cmd(profiles: tuple[Path,...], models_dir: Path, reviews_dir: Path, output: Path, as_json: bool) -> None:
    """Pin a complete reviewed exhibit, bounded motion profiles and fixed helper."""
    inputs = {"profiles":[str(p.resolve()) for p in profiles],"models_dir":str(models_dir.resolve()),
              "reviews_dir":str(reviews_dir.resolve()),"output":str(output.resolve())}
    _motion_execute("motion-plan",inputs,lambda:plan_motion(profiles,models_dir,reviews_dir,output),as_json)


@volume_group.command("motion-build")
@click.option("--handoff", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def motion_build_cmd(handoff: Path, as_json: bool) -> None:
    """Emit fixed Godot helper and motion JSON; keep visual review pending."""
    _motion_execute("motion-build",{"handoff":str(handoff.resolve())},lambda:build_motion(handoff),as_json)


@volume_group.command("motion-validate")
@click.option("--handoff", required=True, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def motion_validate_cmd(handoff: Path, as_json: bool) -> None:
    """Read-only checks for motion inputs, reuse provenance and fresh artifacts."""
    _motion_execute("motion-validate",{"handoff":str(handoff.resolve())},lambda:validate_motion(handoff),as_json)
