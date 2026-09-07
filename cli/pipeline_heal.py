"""Classify and mechanically heal simple pipeline failures."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
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
    "stale_plan": ("yes", "Plan 角色不匹配：复位 prompt.craft 后重跑文案即可"),
    "billing": ("no", "API 余额不足：请给 OpenRouter/Provider 充值后续跑，不必找项目经理"),
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
    billing = [i for i in items if i.get("kind") == "billing"]
    if billing and len(billing) == len(items):
        return {
            "pm_fit": "no",
            "pm_suitable": False,
            "pm_advice": (
                f"API 余额不足（{len(billing)} 项，HTTP 402）。"
                "请给 OpenRouter/Provider 充值后点「运行资产生成」续跑，不必找项目经理。"
            ),
            "pm_advice_short": "API 余额不足，请充值",
        }
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
    if no:
        kinds = {str(i.get("kind") or "unknown") for i in no}
        if kinds == {"network"}:
            detail = f"{len(no)} 项为瞬时网络错误"
        elif kinds == {"missing_file"}:
            detail = f"{len(no)} 项为缺产物文件"
        elif kinds == {"billing"}:
            detail = f"{len(no)} 项为 API 余额不足"
        else:
            detail = f"{len(no)} 项可自动复位重跑"
        return {
            "pm_fit": "no",
            "pm_suitable": False,
            "pm_advice": f"不必找项目经理（{detail}）。已可自动复位，直接点「运行资产生成」续跑。",
            "pm_advice_short": "不必找项目经理，直接重跑",
        }
    return {
        "pm_fit": "no",
        "pm_suitable": False,
        "pm_advice": "不必找项目经理。直接点「运行资产生成」续跑。",
        "pm_advice_short": "不必找项目经理，直接重跑",
    }


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_EXC_LINE_RE = re.compile(r"(?m)^(\w*Error|Exception):\s*(.+)$")
_HTTP_STATUS_RE = re.compile(r"HTTP\s*(\d{3})", re.I)


def _exc_summary_from_blob(blob: str) -> str:
    for match in _EXC_LINE_RE.finditer(blob):
        return match.group(0).strip()
    plain = blob.strip()
    for line in reversed(plain.splitlines()):
        s = line.strip()
        if s and not s.startswith("File ") and "site-packages/click" not in s:
            return s
    return ""


def _network_error_summary(blob: str, exc_summary: str, default: str) -> str:
    if exc_summary:
        return exc_summary[:240]
    blob_l = blob.lower()
    m = _HTTP_STATUS_RE.search(blob)
    if m:
        code = m.group(1)
        if code in ("522", "521", "520", "502", "503", "504", "429"):
            return f"供应商 CDN/网关返回 HTTP {code}，图片下载失败（通常可稍后重试）"
    if "failed to download" in blob_l:
        return "供应商返回的图片 URL 下载失败（CDN/网关超时或不可用，通常可重试）"
    return default


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text or "")


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
    return _strip_ansi("\n".join(parts))


def classify_failed_task(task: dict[str, Any]) -> dict[str, Any]:
    """Return diagnosis for one failed task."""
    tid = str(task.get("id") or "")
    step = str(task.get("step") or "")
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    exit_code = result.get("exit_code")
    blob = _blob(task)
    blob_l = blob.lower()

    # Validation gate — image/prompt only (exit 2 is also used by unrelated CLIs)
    step_l = step.lower()
    tid_l = tid.lower()
    is_godotish = "godot" in step_l or "godot" in tid_l or "assemble" in step_l
    is_videoish = step_l.startswith("video.") or ".video." in tid_l
    if "prompt_crafter_regenerate" in blob_l or (
        not is_godotish
        and not is_videoish
        and (
            exit_code == 2
            or "image validation" in blob_l
            or (
                "validation failed" in blob_l
                and ("prompt" in blob_l or step_l.startswith("image."))
            )
        )
    ):
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

    # API billing / credits — recharge provider; not PM / not auto-heal loop
    if (
        "insufficient credits" in blob_l
        or "http 402" in blob_l
        or "payment required" in blob_l
        or ("402" in blob and "credit" in blob_l)
    ):
        billing_summary = ""
        for match in _EXC_LINE_RE.finditer(blob):
            billing_summary = match.group(0).strip()
            break
        if not billing_summary:
            billing_summary = (
                blob.strip().splitlines()[0][:240] if blob.strip() else "HTTP 402 insufficient credits"
            )
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "billing",
                "owner": "user",
                "remediation": "add_credits",
                "summary": billing_summary[:240],
                "cli_hints": [],
            }
        )

    # Network / CDN download failures (including HTTP 522 from provider file hosts)
    if any(
        k in blob_l
        for k in (
            "connection",
            "timeout",
            "503",
            "502",
            "504",
            "521",
            "522",
            "520",
            "429",
            "rate limit",
            "failed to download",
            "http 5",
            "ended prematurely",
            "incomplete read",
            "chunkedencoding",
            "protocolerror",
            "craft_fail_kind=network",
        )
    ):
        exc_summary = _exc_summary_from_blob(blob)
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "network",
                "owner": "code",
                "remediation": "reset_cascade",
                "summary": _network_error_summary(
                    blob,
                    exc_summary,
                    "Network/API transient error after retries — reset and re-run",
                ),
                "cli_hints": [f"pipeline reset --task-id {tid} --cascade", "pipeline run --jobs 4"],
            }
        )

    # Missing input file / unreadable frames (matte often fails this way)
    if (
        "not found" in blob_l
        or "no such file" in blob_l
        or "does not exist" in blob_l
        or "cannot find" in blob_l
        or "cannot read" in blob_l
        or "can't open/read" in blob_l
        or "batch matting had failures" in blob_l
        or "invalid value for '--input-dir'" in blob_l
        or "invalid value for '--input'" in blob_l
    ):
        # Prefer the nearest upstream producer — do NOT jump to prompt.craft for
        # matte/split missing files (that purges good plans + mp4 and restarts craft).
        reset_id = tid
        run_prompts = False
        if tid.endswith(".video.matte-frames"):
            # Rebuild frames from mp4 (keeps plan + video).
            reset_id = tid[: -len(".video.matte-frames")] + ".video.split-frames"
        elif tid.endswith(".video.split-frames"):
            # Rebuild mp4 (keeps plan).
            reset_id = tid[: -len(".video.split-frames")] + ".video.generate"
        elif tid.endswith(".video.generate"):
            # Missing plan / reference — must recraft + regenerate.
            reset_id = tid[: -len(".video.generate")] + ".prompt.craft"
            run_prompts = True
        hints = [f"pipeline reset --task-id {reset_id} --cascade"]
        if run_prompts:
            hints.append("pipeline run --run-prompts --jobs 4")
        else:
            hints.append("pipeline run --jobs 4")
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "missing_file",
                "owner": "code",
                "remediation": "reset_cascade",
                "reset_task_id": reset_id,
                "summary": "Missing input artifact — reset upstream and regenerate",
                "cli_hints": hints,
            }
        )

    # Prompt craft CJK guard — needs English field regeneration (Hermes)
    if (
        "chinese brief text cannot be used" in blob_l
        or "secondary-generate english" in blob_l
    ):
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "validation",
                "owner": "hermes",
                "remediation": "reset_and_recraft_prompt",
                "summary": (
                    "Brief 含中文描述，不能直接进入出图 prompt；"
                    "需用 LLM 重新 craft 生成英文 prompt 字段"
                ),
                "cli_hints": [
                    f"pipeline reset --task-id {tid} --cascade",
                    "pipeline run --run-prompts --jobs 4",
                ],
            }
        )

    # Plan handoff written for the wrong generator (stale image plan under video task)
    if "is not for video-generator" in blob_l or "is not for image-generator" in blob_l:
        asset = str(task.get("asset_id") or task.get("asset") or "").strip()
        deps = task.get("depends_on") if isinstance(task.get("depends_on"), list) else []
        craft_id = next(
            (str(d) for d in deps if str(d).endswith(".prompt.craft")),
            f"{asset}.prompt.craft" if asset else tid,
        )
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "stale_plan",
                "owner": "hermes",
                "remediation": "reset_and_recraft_prompt",
                "summary": "Plan handoff consumer_role mismatch — recraft for this generator",
                "cli_hints": [
                    f"pipeline reset --task-id {craft_id} --cascade",
                    "pipeline run --run-prompts --jobs 4",
                ],
            }
        )

    # Prefer the real exception line over Click traceback noise.
    exc_summary = _exc_summary_from_blob(blob)
    if "unexpected keyword argument" in blob_l or (
        "typeerror" in blob_l and "promptplan" in blob_l
    ):
        return _with_pm_fit(
            {
                "task_id": tid,
                "step": step,
                "kind": "unknown",
                "owner": "hermes",
                "remediation": "triage",
                "summary": exc_summary[:240]
                or "PromptPlan/dataclass TypeError — code bug, not config",
                "cli_hints": [f"pipeline reset --task-id {tid} --cascade"],
                "stderr_tail": blob[-600:],
            }
        )

    return _with_pm_fit(
        {
            "task_id": tid,
            "step": step,
            "kind": "unknown",
            "owner": "hermes",
            "remediation": "triage",
            "summary": (exc_summary[:240] or blob.strip()[:240] or f"exit {exit_code}"),
            "cli_hints": [f"pipeline reset --task-id {tid} --cascade"],
            "stderr_tail": blob[-600:],
        }
    )


def _manifest_cli_rel(manifest_path: Any) -> str:
    """Path for --manifest when CLI cwd is cli/ (matches GUI cliArgForRel)."""
    from pathlib import Path

    path = Path(manifest_path).resolve()
    cli_dir = Path(__file__).resolve().parent
    repo_root = cli_dir.parent
    try:
        rel = path.relative_to(repo_root)
        return f"../{rel.as_posix()}"
    except ValueError:
        try:
            return path.relative_to(cli_dir).as_posix()
        except ValueError:
            return path.as_posix()


def _ensure_manifest_in_hint(hint: str, manifest_cli_rel: str) -> str:
    from safe_cli import SafeCliError, parse_gamefactory_argv

    line = (hint or "").strip()
    if not line:
        return ""
    try:
        argv = parse_gamefactory_argv(line)
    except SafeCliError:
        return line
    if not argv or argv[0] != "pipeline":
        return line
    if any(tok == "--manifest" for tok in argv):
        return line
    if len(argv) < 2:
        return line
    sub, rest = argv[1], argv[2:]
    return " ".join(["pipeline", sub, "--manifest", manifest_cli_rel, *rest])


def build_fix_command_chain(manifest_cli_rel: str, diagnosis: dict[str, Any]) -> list[str]:
    """Ordered whitelisted CLI lines for PM-suitable pipeline failures (GUI auto-run)."""
    from safe_cli import filter_runnable_actions, normalize_action

    manifest_cli_rel = (manifest_cli_rel or "").strip().replace("\\", "/")
    items = diagnosis.get("needs_hermes") or []
    if not items:
        items = [
            i
            for i in (diagnosis.get("items") or [])
            if i.get("pm_fit") == "yes" and i.get("kind") not in ("network", "missing_file")
        ]

    config_lines: list[str] = []
    reset_lines: list[str] = []
    seen: set[str] = set()
    touched = False

    has_validation = any(
        i.get("kind") in ("validation", "stale_plan", "missing_file") for i in items
    )

    def _add(bucket: list[str], line: str) -> None:
        norm = line.strip()
        if not norm or norm in seen:
            return
        seen.add(norm)
        bucket.append(norm)

    def _is_cmd(argv: list[str], a: str, b: str) -> bool:
        return len(argv) >= 2 and argv[0] == a and argv[1] == b

    for item in items:
        kind = str(item.get("kind") or "")
        if kind in ("config_proxy", "unknown"):
            continue
        touched = True
        for raw in item.get("cli_hints") or []:
            line = _ensure_manifest_in_hint(str(raw), manifest_cli_rel)
            info = normalize_action(line)
            if not info["ok"]:
                continue
            argv = info["argv"]
            if _is_cmd(argv, "pipeline", "status") or _is_cmd(argv, "config", "get"):
                continue
            if _is_cmd(argv, "config", "set"):
                _add(config_lines, line)
            elif _is_cmd(argv, "pipeline", "reset"):
                _add(reset_lines, line)
            # Ignore per-item pipeline run hints — synthesize one final run below.

    chain = config_lines + reset_lines
    if touched and chain:
        run_line = (
            f"pipeline run --manifest {manifest_cli_rel} --jobs 4"
            + (" --run-prompts" if has_validation else "")
        )
        _add(chain, run_line)
    runnable = filter_runnable_actions(chain)
    return [str(i["raw"]) for i in runnable]


def can_auto_fix_without_agent(diagnosis: dict[str, Any]) -> bool:
    """True when diagnose fix chain is fully deterministic (no LLM triage needed)."""
    hermes = diagnosis.get("needs_hermes") or []
    code = diagnosis.get("auto_healable") or []
    if not hermes:
        # network / missing_file etc. — heal_manifest resets without Agent
        return bool(code)
    if not build_fix_command_chain(diagnosis.get("manifest_cli_rel") or "", diagnosis):
        return False
    return all(
        str(i.get("kind") or "")
        in ("validation", "stale_plan", "config_size", "missing_file", "network")
        for i in hermes
    )


def diagnose_manifest(
    manifest: dict[str, Any],
    *,
    manifest_cli_rel: str = "",
) -> dict[str, Any]:
    failed = [t for t in tasks_list(manifest) if t.get("status") == TASK_FAILED]
    items = [classify_failed_task(t) for t in failed]
    advice = _aggregate_pm_advice(items)
    out: dict[str, Any] = {
        "failed_count": len(items),
        "items": items,
        "auto_healable": [i for i in items if i.get("owner") == "code"],
        "needs_hermes": [i for i in items if i.get("owner") == "hermes"],
        "summary": status_summary(manifest),
        **advice,
    }
    if manifest_cli_rel:
        out["manifest_cli_rel"] = manifest_cli_rel
        out["fix_commands"] = build_fix_command_chain(manifest_cli_rel, out)
        out["auto_fix_without_agent"] = can_auto_fix_without_agent(out)
    return out

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
        tid = str(item.get("reset_task_id") or item["task_id"])
        reset_task_cascade(manifest, tid)
        healed.append(tid)
    return {
        "healed": healed,
        "skipped": skipped,
        "diagnose": diagnose_manifest(manifest),
    }


def failure_log_path(manifest_path: Any) -> Path:
    """JSONL beside the manifest — survives heal reset of failed→pending."""
    return Path(manifest_path).resolve().parent / "failure-log.jsonl"


def _compact_failure_item(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "task_id": item.get("task_id"),
        "kind": item.get("kind"),
        "owner": item.get("owner"),
        "remediation": item.get("remediation"),
        "summary": item.get("summary"),
        "pm_fit": item.get("pm_fit"),
        "pm_tip": item.get("pm_tip"),
    }
    stderr = str(item.get("stderr") or "").strip()
    if not stderr:
        # classify_failed_task may only put text in summary; keep raw if present
        for key in ("stderr", "stdout_tail", "error"):
            if item.get(key):
                stderr = str(item.get(key)).strip()
                break
    if stderr:
        out["stderr"] = stderr[:4000]
    return {k: v for k, v in out.items() if v is not None and v != ""}


def append_failure_log(
    manifest_path: Any,
    *,
    event: str,
    diagnosis: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> Path | None:
    """Append one JSONL row with failed-task diagnosis before heal clears it."""
    items_src = []
    if isinstance(diagnosis, dict):
        items_src = list(diagnosis.get("items") or [])
        if not items_src:
            items_src = list(diagnosis.get("needs_hermes") or []) + list(
                diagnosis.get("auto_healable") or []
            )
    if not items_src and not extra:
        return None
    try:
        path = failure_log_path(manifest_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "manifest": str(Path(manifest_path).resolve()),
            "failed_count": (
                int(diagnosis.get("failed_count") or len(items_src))
                if isinstance(diagnosis, dict)
                else len(items_src)
            ),
            "items": [_compact_failure_item(i) for i in items_src if isinstance(i, dict)],
        }
        if isinstance(diagnosis, dict):
            for key in ("pm_advice_short", "pm_advice", "pm_fit"):
                if diagnosis.get(key) is not None:
                    record[key] = diagnosis.get(key)
        if extra:
            record.update(extra)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path
    except OSError:
        return None


def diagnose_and_heal_file(manifest_path: Any, *, apply: bool) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = load_manifest(path)
    manifest_cli_rel = _manifest_cli_rel(path)
    diagnosis = diagnose_manifest(manifest, manifest_cli_rel=manifest_cli_rel)
    # Enrich items with raw stderr from tasks so the log stays useful after reset.
    by_id = {str(t.get("id")): t for t in tasks_list(manifest)}
    for item in diagnosis.get("items") or []:
        tid = str(item.get("task_id") or "")
        task = by_id.get(tid) or {}
        result = task.get("result") if isinstance(task.get("result"), dict) else {}
        if result.get("stderr") and not item.get("stderr"):
            item["stderr"] = str(result.get("stderr"))[:4000]
    log_path: Path | None = None
    if int(diagnosis.get("failed_count") or 0) > 0:
        log_path = append_failure_log(
            path,
            event="pre_heal" if apply else "diagnose",
            diagnosis=diagnosis,
        )
    if not apply:
        out = {"applied": False, "pre_diagnose": diagnosis, **diagnosis}
        if log_path is not None:
            out["failure_log"] = str(log_path)
        return out
    heal = heal_manifest(manifest, only_code=True)
    save_manifest(path, manifest)
    post = diagnose_manifest(manifest, manifest_cli_rel=manifest_cli_rel)
    out = {
        "applied": True,
        **heal,
        "pre_diagnose": diagnosis,
        "diagnose": post,
        "manifest_cli_rel": manifest_cli_rel,
        "fix_commands": post.get("fix_commands") or diagnosis.get("fix_commands") or [],
        "auto_fix_without_agent": post.get("auto_fix_without_agent"),
    }
    if log_path is not None:
        out["failure_log"] = str(log_path)
    return out
