"""Single-asset pipeline repair: reset cascade → optional prompt recraft → run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline_manifest import load_manifest, save_manifest
from pipeline_retry import _pick_reset_task_id, load_manifest_tasks
from pipeline_runner import PipelineRunResult, reset_task_cascade, run_pipeline


def _needs_run_prompts(
    reset_task_id: str,
    tasks: list[dict[str, Any]],
    *,
    recraft_prompt: bool,
) -> bool:
    if recraft_prompt:
        return True
    for task in tasks:
        if str(task.get("id") or "") != reset_task_id:
            continue
        step = str(task.get("step") or "")
        tid = str(task.get("id") or "")
        if step == "prompt.craft" or "prompt.craft" in tid or ".prompt" in tid:
            return True
        break
    return False


def _run_exit_code(result: PipelineRunResult) -> int:
    if result.complete:
        return 0
    if result.paused:
        return 2
    if result.blocked:
        return 1
    return 1


def retry_asset(
    manifest_path: Path,
    *,
    asset: str | None = None,
    task_id: str | None = None,
    recraft_prompt: bool = False,
    jobs: int = 4,
) -> dict[str, Any]:
    """Reset one asset's failed task (cascade) and re-run the pipeline."""
    if not asset and not task_id:
        raise ValueError("Provide --asset or --task-id")

    manifest_path = manifest_path.resolve()
    manifest = load_manifest(manifest_path)
    tasks = load_manifest_tasks(manifest_path)

    reset_task_id = task_id
    if not reset_task_id:
        assert asset is not None
        reset_task_id = _pick_reset_task_id(tasks, asset)
        if not reset_task_id:
            raise ValueError(f"No pipeline task found for asset: {asset}")

    reset_ids = reset_task_cascade(manifest, reset_task_id)
    save_manifest(manifest_path, manifest)

    run_prompts = _needs_run_prompts(reset_task_id, tasks, recraft_prompt=recraft_prompt)
    run_result = run_pipeline(
        manifest_path,
        jobs=jobs,
        run_prompts=run_prompts,
    )

    exit_code = _run_exit_code(run_result)
    resolved_asset = asset
    if not resolved_asset:
        for task in tasks:
            if str(task.get("id") or "") == reset_task_id:
                resolved_asset = str(task.get("asset") or "") or None
                break

    return {
        "ok": run_result.complete,
        "asset": resolved_asset,
        "reset_task_id": reset_task_id,
        "recraft_prompt": recraft_prompt,
        "run_prompts": run_prompts,
        "run_exit_code": exit_code,
        "reset_ids": reset_ids,
        "healed_task_ids": reset_ids,
        "summary": run_result.summary,
        "message": run_result.message,
        "complete": run_result.complete,
        "paused": run_result.paused,
        "blocked": run_result.blocked,
    }
