"""Classify and mechanically heal simple pipeline failures."""

from __future__ import annotations

import re
from typing import Any

from pipeline_manifest import (
    TASK_FAILED,
    load_manifest,
    save_manifest,
    status_summary,
    tasks_list,
)
from pipeline_runner import reset_task_cascade

# stderr / stdout patterns → remediation class
_SIZE_MULTIPLE_RE = re.compile(
    r"divisible by\s+(\d+)|multiple of\s+(\d+)|must be.*?(\d+)\s*px",
    re.I,
)

# kind → (pm_fit, short Chinese tip for GUI)
# pm_fit: yes = 适合项目经理直接改；maybe = 可先分诊；no = 不必找项目经理
_PM_FIT: dict[str, tuple[str, str]] = {
    "config_size": ("yes", "改配置（尺寸倍数）即可，适合项目经理直接处理"),
    "config_proxy": ("yes", "改代理配置即可，适合项目经理直接处理"),
    "validation": ("yes", "图校验/文案问题，适合项目经理复位并重跑文案"),
    "unknown": ("maybe", "原因不清：可先让项目经理分诊；若像内核/玩法 bug 再另处理"),
    "network": ("no", "瞬时网络错误：自动复位后重跑即可，不必找项目经理"),
    "missing_file": ("no", "缺产物文件：自动复位后重跑即可，不必找项目经理"),
}


def _with_pm_fit(item: dict[str, Any]) -> dict[str, Any]:
    kind = str(item.get("kind") or "unknown")
    fit, tip = _PM_FIT.get(kind, ("maybe", "可先让项目经理分诊"))
    out = dict(item)
    out["pm_fit"] = fit
    out["pm_tip"] = tip
    return out


def _aggregate_pm_advice(items: list[dict[str, Any]]) -> dict[str, Any]:
    """User-facing: should they hand this to the project-manager agent?"""
    if not items:
        return {
            "pm_fit": "none",
            "pm_suitable": False,
            "pm_advice": "当前没有 failed 任务。",
            "pm_advice_short": "无失败",
        }
    yes = [i for i in items if i.get("pm_fit") == "yes"]
    maybe = [i for i in items if i.get("pm_fit") == "maybe"]
    no = [i for i in items if i.get("pm_fit") == "no"]
    if yes and not maybe and not no:
        return {
            "pm_fit": "yes",
            "pm_suitable": True,
            "pm_advice": (
                f"适合交给项目经理 Agent 直接处理（{len(yes)} 项：配置/校验/文案）。"
                "点「项目经理处理失败」即可。"
            ),
            "pm_advice_short": "适合项目经理直接处理",
        }
    if yes or maybe:
        parts = []
        if yes:
            parts.append(f"{len(yes)} 项适合项目经理（配置/校验）")
        if maybe:
            parts.append(f"{len(maybe)} 项需先分诊")
        if no:
            parts.append(f"{len(no)} 项只需复位重跑、不必找项目经理")
        return {
            "pm_fit": "mixed",
            "pm_suitable": True,
            "pm_advice": "；".join(parts) + "。建议点「项目经理处理失败」处理适合的部分。",
            "pm_advice_short": "部分适合项目经理处理",
        }
    return {
        "pm_fit": "no",
        "pm_suitable": False,
        "pm_advice": (
            f"不适合/不必找项目经理（{len(no)} 项为网络或缺文件）。"
            "已可自动复位，直接点「运行资产生成」续跑。"
        ),
        "pm_advice_short": "不必找项目经理，直接重跑",
    }


def _blob(task: dict[str, Any]) -> str:
    result = task.get("result") or {}
    if not isinstance(result, dict):
        return ""
    parts = [
        str(result.get("stderr") or ""),
        str(result.get("stdout") or ""),
        str(result.get("stdout_tail") or ""),
        str(result.get("error") or ""),
    ]
    return "\n".join(parts)


def classify_failed_task(task: dict[str, Any]) -> dict[str, Any]:
    """Return diagnosis for one failed task."""
    tid = str(task.get("id") or "")
    step = str(task.get("step") or "")
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    exit_code = result.get("exit_code")
    blob = _blob(task)
    blob_l = blob.lower()

    # Validation gate — needs prompt/plan judgment (Hermes)
    if exit_code == 2 or "prompt_crafter_regenerate" in blob_l:
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "validation",
                "owner": "hermes",
                "remediation": "reset_and_recraft_prompt",
                "summary": "Image validation failed — regenerate plan prompt",
                "cli_hints": [
                    f"pipeline reset --task-id {tid} --cascade",
                    "pipeline run --run-prompts --jobs 4",
                ],
            }
        )

    # API size constraints — fix via config (PM), not kernel logic
    if "divisible" in blob_l or "invalid size" in blob_l or "unsupported size" in blob_l:
        mult = None
        m = _SIZE_MULTIPLE_RE.search(blob)
        if m:
            for g in m.groups():
                if g:
                    mult = int(g)
                    break
        mult = mult or 16
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "config_size",
                "owner": "hermes",
                "remediation": "fix_config",
                "size_multiple": mult,
                "summary": f"API rejected image size — set image.constraints.size_multiple={mult}",
                "cli_hints": [
                    f"config set --key image.constraints.size_multiple --value {mult}",
                    f"pipeline reset --task-id {tid} --cascade",
                    "pipeline run --jobs 4",
                ],
            }
        )

    # Proxy misconfig — PM can patch allowlisted proxy keys
    if "proxy" in blob_l and any(
        k in blob_l for k in ("connection", "refused", "tunnel", "407", "cannot connect")
    ):
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "config_proxy",
                "owner": "hermes",
                "remediation": "fix_config",
                "summary": "Proxy connection failed — check image.proxy / proxy in config",
                "cli_hints": [
                    "config get --key image.proxy",
                    f"pipeline reset --task-id {tid} --cascade",
                ],
            }
        )

    # Network already exhausted retries
    if any(
        k in blob_l
        for k in ("connection", "timeout", "503", "502", "504", "429", "rate limit")
    ):
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "network",
                "owner": "code",
                "remediation": "reset_cascade",
                "summary": "Network/API transient error after retries — reset and re-run",
                "cli_hints": [f"pipeline reset --task-id {tid} --cascade", "pipeline run --jobs 4"],
            }
        )

    # Missing input file often from deleted assets
    if "not found" in blob_l or "no such file" in blob_l or "cannot find" in blob_l:
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "missing_file",
                "owner": "code",
                "remediation": "reset_cascade",
                "summary": "Missing input artifact — reset upstream and regenerate",
                "cli_hints": [f"pipeline reset --task-id {tid} --cascade", "pipeline run --jobs 4"],
            }
        )

    return _with_pm_fit(
        {
            "task_id": tid,
            "step": step,
            "kind": "unknown",
            "owner": "hermes",
            "remediation": "triage",
            "summary": (blob.strip()[:240] or f"exit {exit_code}"),
            "cli_hints": [f"pipeline reset --task-id {tid} --cascade"],
            "stderr_tail": blob[-600:],
        }
    )


def diagnose_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    failed = [t for t in tasks_list(manifest) if t.get("status") == TASK_FAILED]
    items = [classify_failed_task(t) for t in failed]
    advice = _aggregate_pm_advice(items)
    return {
        "failed_count": len(items),
        "items": items,
        "auto_healable": [i for i in items if i.get("owner") == "code"],
        "needs_hermes": [i for i in items if i.get("owner") == "hermes"],
        "summary": status_summary(manifest),
        **advice,
    }

def heal_manifest(manifest: dict[str, Any], *, only_code: bool = True) -> dict[str, Any]:
    """Reset failed tasks that code can safely heal. Returns heal report."""
    report = diagnose_manifest(manifest)
    healed: list[str] = []
    skipped: list[dict[str, Any]] = []
    for item in report["items"]:
        if only_code and item.get("owner") != "code":
            skipped.append(item)
            continue
        if item.get("remediation") not in ("reset_cascade", "reset_and_recraft_prompt"):
            skipped.append(item)
            continue
        tid = item["task_id"]
        reset_task_cascade(manifest, tid)
        healed.append(tid)
    return {
        "healed": healed,
        "skipped": skipped,
        "diagnose": diagnose_manifest(manifest),
    }


def diagnose_and_heal_file(manifest_path: Any, *, apply: bool) -> dict[str, Any]:
    from pathlib import Path

    path = Path(manifest_path)
    manifest = load_manifest(path)
    diagnosis = diagnose_manifest(manifest)
    if not apply:
        return {"applied": False, **diagnosis}
    heal = heal_manifest(manifest, only_code=True)
    save_manifest(path, manifest)
    return {"applied": True, **heal}
