"""GUI Agent turn — spawn executor CLI (hermes/codex/cursor-agent), not desktop apps.

Sessions: plans/conversations/{product_host|programmer}/<session_id>.json
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_auth_resolve import resolve_agent_auth
from agent_routing import resolve_agent

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONV_ROOT = _REPO_ROOT / "plans" / "conversations"
_PRODUCT_HOST_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "product-host.md"
_PROGRAMMER_SKILL = _REPO_ROOT / "resources" / "skills" / "godot-developer" / "implement.md"
_IT_SKILL = _REPO_ROOT / "resources" / "skills" / "it" / "diagnose.md"

ROLE_KINDS = frozenset({"product_host", "programmer", "it"})

# Map GUI colleague role → config.agents role key
_ROLE_TO_AGENT: dict[str, str] = {
    "product_host": "orchestrator",
    "programmer": "godot-developer",
    "it": "it",
}

_HERMES_SKILL: dict[str, str] = {
    "product_host": "game-factory-orchestrator",
    "programmer": "game-factory-godot-developer",
    # IT defaults to Pi; Hermes fallback has no dedicated package yet.
}

_DEFAULT_TIMEOUT = 600
_VALID_EXECUTORS = frozenset({"hermes", "codex", "cursor", "pi"})


class AgentTurnError(RuntimeError):
    """Raised when executor CLI is missing or the turn fails."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sanitize_session_id(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise AgentTurnError("session_id is required.")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", s).strip("-")
    if not cleaned or cleaned in {".", ".."}:
        raise AgentTurnError(f"Invalid session_id: {raw!r}")
    return cleaned[:80]


def conversations_dir(role_kind: str) -> Path:
    if role_kind not in ROLE_KINDS:
        raise AgentTurnError(f"Unsupported role_kind: {role_kind}")
    return _CONV_ROOT / role_kind


def session_path_for(role_kind: str, session_id: str) -> Path:
    return conversations_dir(role_kind) / f"{sanitize_session_id(session_id)}.json"


def new_session(role_kind: str, session_id: str | None = None, *, executor: str | None = None) -> dict[str, Any]:
    if role_kind not in ROLE_KINDS:
        raise AgentTurnError(f"Unsupported role_kind: {role_kind}")
    sid = sanitize_session_id(session_id) if session_id else uuid.uuid4().hex[:12]
    now = _utc_now()
    return {
        "id": sid,
        "role": role_kind,
        "executor": executor,
        "executor_session_id": None,
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "summary": "",
    }


def load_session(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AgentTurnError(f"Session not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AgentTurnError("Session file must be a JSON object.")
    return data


def save_session(path: Path, session: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = _utc_now()
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_executor(value: Any) -> str | None:
    if value is None:
        return None
    ex = str(value).strip().lower()
    return ex if ex in _VALID_EXECUTORS else None


def _auth_failure_hint(auth: dict[str, Any]) -> str:
    err = str(auth.get("error") or "鉴权失败").strip()
    provider = auth.get("provider")
    source = auth.get("source")
    bits = [err]
    if provider:
        bits.append(f"provider={provider}")
    if source:
        bits.append(f"source={source}")
    bits.append("请在「设置 → 角色页」为当前实例配置 Provider 并填写 Key。")
    return " · ".join(bits)


def _hermes_invoke_env(resolved_auth: dict[str, Any] | None) -> dict[str, str] | None:
    if not resolved_auth:
        return None
    api_key = resolved_auth.get("api_key")
    env_key = resolved_auth.get("env_key")
    if not api_key or not env_key:
        return None
    return {str(env_key): str(api_key)}


def _hermes_cli_provider(config: dict[str, Any], foundry_provider: str | None) -> str | None:
    if not foundry_provider:
        return None
    from executor_setup import resolve_hermes_sync_settings

    sync = resolve_hermes_sync_settings(config, provider_id=str(foundry_provider).strip().lower())
    return sync.get("hermes_provider")


def resolve_executor_for_role(
    role_kind: str,
    config: dict[str, Any],
    override: str | None = None,
    *,
    instance_id: str | None = None,
) -> str:
    normalized = _normalize_executor(override)
    if normalized:
        return normalized

    auth = resolve_agent_auth(config, role_kind=role_kind, instance_id=instance_id)
    from_auth = _normalize_executor(auth.get("executor"))
    if from_auth:
        return from_auth

    if role_kind == "it":
        agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
        it_cfg = agents.get("it") if isinstance(agents.get("it"), dict) else {}
        ex = str(it_cfg.get("executor") or "pi").strip().lower()
        return ex if ex in ("pi", "hermes", "codex", "cursor") else "pi"

    agent_role = _ROLE_TO_AGENT.get(role_kind, "orchestrator")
    resolved = resolve_agent(agent_role, config)
    executor = str(resolved.get("executor") or "hermes")
    if executor == "pipeline":
        executor = "hermes"
    if executor not in ("hermes", "codex", "cursor", "pi"):
        executor = "hermes"
    return executor


def _load_skill_text(role_kind: str, limit: int = 12_000) -> str:
    if role_kind == "it":
        path = _IT_SKILL
    elif role_kind == "product_host":
        path = _PRODUCT_HOST_SKILL
    else:
        path = _PROGRAMMER_SKILL
    if path.is_file():
        return path.read_text(encoding="utf-8")[:limit]
    return "Follow Foundry project conventions. Reply in Chinese."


def _snippet(path: Path | None, limit: int = 4000) -> str:
    if not path or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except OSError:
        return ""


def _find_default_progress(brief_path: Path | None = None) -> Path | None:
    from project_paths import find_default_progress

    return find_default_progress(brief_path=brief_path)


def _find_default_brief() -> Path | None:
    from project_paths import find_default_brief

    return find_default_brief()


def build_prompt(
    *,
    role_kind: str,
    user_message: str,
    session: dict[str, Any],
    brief_path: Path | None = None,
    progress_path: Path | None = None,
    programmer_roster: list[dict[str, str]] | None = None,
    default_target_instance_id: str | None = None,
    instance_id: str | None = None,
) -> str:
    if role_kind == "it":
        title = "IT / 运维"
    elif role_kind == "product_host":
        title = "项目经理"
    else:
        title = "程序员"
    skill = _load_skill_text(role_kind)
    brief = brief_path or _find_default_brief()
    progress = progress_path or _find_default_progress(brief_path=brief)

    recent = list(session.get("messages") or [])[-12:]
    history_lines: list[str] = []
    for m in recent:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "")
        content = str(m.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    parts = [
        f"你是 Game AI Foundry GUI 里的「{title}」同事（role={role_kind}）。",
        "用中文回复用户。权威信息以仓库本地文件为准，不要编造已写入磁盘的状态。",
        f"仓库根目录：{_REPO_ROOT}",
        "",
        "## 角色规范",
        skill,
        "",
        "## 项目文件（可读；需要细节请用工具打开完整文件）",
    ]
    if brief:
        parts.append(f"- brief: {brief}")
        snip = _snippet(brief, 2500)
        if snip:
            parts.append("```json")
            parts.append(snip)
            parts.append("```")
    else:
        parts.append("- brief: （未找到）")
    if progress:
        parts.append(f"- progress: {progress}")
        snip = _snippet(progress, 2500)
        if snip:
            parts.append("```json")
            parts.append(snip)
            parts.append("```")
    else:
        parts.append("- progress: （未找到；可用 `python gamefactory.py project progress show`）")

    summary = str(session.get("summary") or "").strip()
    if summary:
        parts.extend(["", "## 较早对话摘要", summary])

    if history_lines:
        parts.extend(["", "## 近部对话", *history_lines])

    parts.extend(["", "## 用户本轮消息", user_message.strip(), ""])
    if role_kind == "product_host":
        roster = programmer_roster or []
        if roster:
            parts.append("## 可派工的程序员实例（必须从下列 id 中选 target_instance_id）")
            for row in roster:
                rid = str(row.get("id") or "").strip()
                name = str(row.get("display_name") or rid).strip()
                if rid:
                    parts.append(f"- `{rid}` — {name}")
            if default_target_instance_id:
                parts.append(f"默认优先派给：`{default_target_instance_id}`（用户未指定时用此 id）")
            parts.append("")
        open_hos = []
        try:
            from handoff import list_handoffs

            open_hos = list_handoffs(status="open", target_role="programmer")[:5]
        except Exception:
            open_hos = []
        if open_hos:
            parts.append("## 当前未完成 handoff（勿重复开同题单，除非用户要求）")
            for h in open_hos:
                tid = h.get("target_instance_id") or "（未指定/广播）"
                parts.append(
                    f"- [{h.get('id')}] {h.get('title')} triage={h.get('triage')} → {tid}"
                )
            parts.append("")
        parts.append(
            "## GUI 与首跑硬约束（必读）\n"
            "- 本机 config.json / API Key / proxy：默认不要动；"
            "**仅当用户明确要求改配置时**才可改；勿在「下一步」里自行改配置或刷 review diff。\n"
            "- 用户说「下一步/按你的推荐/开干」且 brief 已冻结：默认先跑资产流水线，"
            "引导用户点 GUI 按钮「生成流水线」→「运行资产生成（含文案）」，不要只丢 bash 墙。\n"
            "- 已有 progress 但未 pipeline plan/run：triage=asset，dispatch.to=pipeline，"
            "gui_hints 含上述两个按钮文案。\n"
            "- 不要再空问 A/B/C；短结论 + 点按钮。\n\n"
            "请分诊（bug / 资产 / 不符 brief / 改需求），给出下一步。"
            "回复末尾必须附加一个 JSON 代码块（便于宿主落盘），格式：\n"
            "```json\n"
            '{"triage":"bug|asset|brief_mismatch|design_change|unknown",'
            '"dispatch":{"to":"programmer|pipeline|brief_tab|none","task_id":null,'
            '"target_instance_id":null,"asset_names":[],"cli_hints":[]},'
            '"progress_note":"一句话写入 progress.memory",'
            '"gui_hints":["生成流水线","运行资产生成（含文案）"]}\n'
            "```\n"
            "派给程序员时 dispatch.to 必须为 programmer，并填写 target_instance_id（上表 id）。\n"
            "资产/首跑用 dispatch.to=pipeline，并填写 gui_hints。"
        )
    else:
        try:
            from handoff import open_handoffs_for_prompt

            hos = open_handoffs_for_prompt(limit=5, target_instance_id=instance_id)
        except Exception:
            hos = []
        if hos:
            parts.append("## 待处理 handoff（文件总线；优先处理；仅本实例或未指定目标）")
            for doc in hos:
                meta = doc.get("handoff_meta") if isinstance(doc.get("handoff_meta"), dict) else {}
                parts.append(
                    json.dumps(
                        {
                            "path": doc.get("_path"),
                            "id": meta.get("id"),
                            "target_instance_id": meta.get("target_instance_id"),
                            "triage": doc.get("triage"),
                            "title": doc.get("title"),
                            "summary": doc.get("summary"),
                            "task_id": doc.get("task_id"),
                            "cli_hints": doc.get("cli_hints"),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            parts.append("")
        parts.append(
            "按任务改 Godot C# / 验收；改完说明改了什么，并建议 validate/test 命令。"
            "若完成某个 handoff，在回复末尾附加：\n"
            '```json\n{"handoff_done":"<handoff_id>","progress_note":"可选"}\n```'
        )
    return "\n".join(parts)


def _which_executor_bin(executor: str) -> str | None:
    if executor == "hermes":
        return shutil.which("hermes")
    if executor == "codex":
        return shutil.which("codex")
    if executor == "cursor":
        return shutil.which("agent") or shutil.which("cursor-agent")
    return None


def _run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = {**os.environ, **(env or {})}
    # Force UTF-8: Windows default (GBK) breaks Cursor/Hermes agent stdout.
    run_env.setdefault("PYTHONIOENCODING", "utf-8")
    run_env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        argv,
        cwd=str(cwd),
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=run_env,
        check=False,
    )


def _extract_hermes_session_id(stdout: str, stderr: str) -> str | None:
    blob = f"{stdout}\n{stderr}"
    m = re.search(r"session[_ ]?id[:\s]+([a-zA-Z0-9_-]{6,})", blob, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b", blob, re.I)
    return m.group(1) if m else None


def _clean_assistant_text(text: str) -> str:
    t = (text or "").strip()
    # Drop common CLI noise tails
    t = re.sub(r"\n+Session ID:.*$", "", t, flags=re.I | re.S)
    return t.strip()


def _looks_like_executor_error(text: str) -> bool:
    """Hermes/Codex sometimes exit 0 but print a fatal one-liner."""
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    patterns = (
        "unknown skill",
        "error: unknown",
        "skill not found",
        "no such skill",
        "authentication failed",
        "unauthorized",
        "invalid api key",
        "api key not found",
    )
    if any(p in low for p in patterns):
        return True
    # Short Error: ... one-liners
    if re.match(r"(?is)^error:\s*\S+", t) and len(t) < 400:
        return True
    return False


def run_hermes_turn(
    prompt: str,
    *,
    role_kind: str,
    executor_session_id: str | None,
    timeout: int,
    config: dict[str, Any] | None = None,
    resolved_auth: dict[str, Any] | None = None,
    instance_id: str | None = None,
) -> tuple[str, str | None, str]:
    hermes = _which_executor_bin("hermes")
    if not hermes:
        raise AgentTurnError("未找到 hermes CLI。请在环境面板安装 Hermes，或改选其他执行器。")
    if role_kind not in _HERMES_SKILL:
        raise AgentTurnError(
            f"角色 {role_kind} 未配置 Hermes skill（IT 请用内置 Pi：executor=pi）。"
        )
    if not resolve_hermes_yolo(config, instance_id=instance_id):
        raise AgentTurnError(
            "当前 Hermes YOLO 已关闭（agents.executors.hermes.yolo 或该实例 instances.<id>.yolo 设为 false）。"
            "未接入 Hermes ACP 前，GUI/CLI 不可关闭 YOLO（去掉 --yolo 会在无 TTY 下挂起）。"
            "请在「设置 → Agent → Hermes」打开 YOLO，或在实例配置中打开 YOLO，或等待 ACP 集成后再关。"
        )
    skill = _HERMES_SKILL[role_kind]
    argv = [
        hermes,
        "chat",
        "-q",
        prompt,
        "-Q",
        "-s",
        skill,
        "--yolo",
        "--source",
        "tool",
        "--accept-hooks",
    ]
    if executor_session_id:
        argv.extend(["--resume", executor_session_id])
    if resolved_auth:
        model = resolved_auth.get("model")
        if model:
            argv.extend(["-m", str(model)])
        provider = resolved_auth.get("provider")
        if provider and config is not None:
            hermes_provider = _hermes_cli_provider(config, str(provider))
            if hermes_provider:
                argv.extend(["--provider", str(hermes_provider)])
    hermes_env = _hermes_invoke_env(resolved_auth)
    proc = _run_cmd(argv, cwd=_REPO_ROOT, timeout=timeout, env=hermes_env)
    out = _clean_assistant_text(proc.stdout or "")
    err = (proc.stderr or "").strip()
    combined = out or err
    if proc.returncode != 0 and not out:
        raise AgentTurnError(f"hermes 退出码 {proc.returncode}: {err or '(no stderr)'}")
    if _looks_like_executor_error(combined):
        hint = ""
        if "unknown skill" in combined.lower() or "skill" in combined.lower():
            hint = (
                "\n\n请到「环境 → Hermes」重新执行「安装本项目 Skills」"
                "（会装到 $HERMES_HOME/skills，当前机可能不是 ~/.hermes）。"
            )
        raise AgentTurnError(f"{combined}{hint}")
    if not out:
        out = err or "（Hermes 无输出）"
    sid = _extract_hermes_session_id(proc.stdout or "", proc.stderr or "") or executor_session_id
    return out, sid, err


# Must stay in sync with gui/src/settings/executorModels.ts tiers.mid
_CODEX_MID_TIER_MODEL = "gpt-5.3"
_CURSOR_MID_TIER_MODEL = "auto"

_CODEX_SANDBOXES = frozenset({"read-only", "workspace-write", "danger-full-access"})
_CURSOR_PERMISSION_MODES = frozenset({"force", "auto_review", "plan", "ask"})
_DEFAULT_CODEX_SANDBOX = "workspace-write"
_DEFAULT_CURSOR_PERMISSION_MODE = "force"


def _executors_block(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return {}
    executors = agents.get("executors")
    return executors if isinstance(executors, dict) else {}


def _executor_preset(config: dict[str, Any] | None, executor_id: str) -> dict[str, Any]:
    block = _executors_block(config).get(executor_id)
    return block if isinstance(block, dict) else {}


def _instance_record(config: dict[str, Any] | None, instance_id: str | None) -> dict[str, Any]:
    if not instance_id or not isinstance(config, dict):
        return {}
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return {}
    instances = agents.get("instances")
    if not isinstance(instances, dict):
        return {}
    record = instances.get(instance_id)
    return record if isinstance(record, dict) else {}


def resolve_codex_sandbox(config: dict[str, Any] | None = None, instance_id: str | None = None) -> str:
    inst = _instance_record(config, instance_id)
    raw = str(inst.get("sandbox") or "").strip()
    if raw in _CODEX_SANDBOXES:
        return raw
    raw = str(_executor_preset(config, "codex").get("sandbox") or "").strip()
    if raw in _CODEX_SANDBOXES:
        return raw
    return _DEFAULT_CODEX_SANDBOX


def resolve_cursor_permission_mode(
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
) -> str:
    inst = _instance_record(config, instance_id)
    raw = str(inst.get("permission_mode") or "").strip()
    if raw in _CURSOR_PERMISSION_MODES:
        return raw
    raw = str(_executor_preset(config, "cursor").get("permission_mode") or "").strip()
    if raw in _CURSOR_PERMISSION_MODES:
        return raw
    return _DEFAULT_CURSOR_PERMISSION_MODE


def _cursor_cli_non_force_error() -> str:
    return (
        "Cursor 执行器在非 force 权限模式下需通过 Foundry GUI 进行 ACP 中途审批。"
        "请使用 GUI 对话，或在「设置 → Agent → Cursor」/实例配置中将 permission_mode 设为 force。"
    )


def _require_cursor_force_for_cli(
    config: dict[str, Any] | None,
    *,
    instance_id: str | None,
) -> None:
    if resolve_cursor_permission_mode(config, instance_id=instance_id) != "force":
        raise AgentTurnError(_cursor_cli_non_force_error())


def resolve_hermes_yolo(config: dict[str, Any] | None = None, instance_id: str | None = None) -> bool:
    inst = _instance_record(config, instance_id)
    if "yolo" in inst:
        return bool(inst.get("yolo"))
    preset = _executor_preset(config, "hermes")
    if "yolo" not in preset:
        return True
    return bool(preset.get("yolo"))


def _resolve_native_model(executor: str, model: str | None) -> str:
    model_id = (model or "").strip()
    if model_id:
        return model_id
    if executor == "codex":
        return _CODEX_MID_TIER_MODEL
    if executor == "cursor":
        return _CURSOR_MID_TIER_MODEL
    return model_id


def run_codex_turn(
    prompt: str,
    *,
    executor_session_id: str | None,
    timeout: int,
    sandbox: str = "workspace-write",
    model: str | None = None,
) -> tuple[str, str | None, str]:
    codex = _which_executor_bin("codex")
    if not codex:
        raise AgentTurnError("未找到 codex CLI。请在环境面板安装 Codex 并完成登录。")

    model_id = _resolve_native_model("codex", model)

    with tempfile.TemporaryDirectory(prefix="gaf-codex-") as tmp:
        out_file = Path(tmp) / "last_message.txt"
        if executor_session_id:
            argv = [
                codex,
                "exec",
                "resume",
                executor_session_id,
            ]
            argv.extend(["-m", model_id])
            argv.extend([
                "--sandbox",
                sandbox,
                "-o",
                str(out_file),
                "-",
            ])
        else:
            argv = [
                codex,
                "exec",
            ]
            argv.extend(["-m", model_id])
            argv.extend([
                "--sandbox",
                sandbox,
                "-C",
                str(_REPO_ROOT),
                "-o",
                str(out_file),
                "-",
            ])
        proc = _run_cmd(argv, cwd=_REPO_ROOT, timeout=timeout, stdin_text=prompt)
        err = (proc.stderr or "").strip()
        out = ""
        if out_file.is_file():
            out = out_file.read_text(encoding="utf-8").strip()
        if not out:
            out = _clean_assistant_text(proc.stdout or "")
        if proc.returncode != 0 and not out:
            raise AgentTurnError(f"codex 退出码 {proc.returncode}: {err or '(no stderr)'}")
        if not out:
            out = err or "（Codex 无输出）"
        # Codex may print session id in stderr; best-effort keep previous
        sid = executor_session_id
        m = re.search(r"session[_ ]?id[:\s]+([a-zA-Z0-9_-]{6,})", err, re.I)
        if m:
            sid = m.group(1)
        return out, sid, err


def run_cursor_turn(
    prompt: str,
    *,
    executor_session_id: str | None,
    timeout: int,
    model: str | None = None,
    permission_mode: str | None = None,
) -> tuple[str, str | None, str]:
    agent = _which_executor_bin("cursor")
    if not agent:
        raise AgentTurnError(
            "未找到 Cursor Agent CLI（`agent` / `cursor-agent`）。"
            "请安装 Cursor Agent shell 命令，或改用 Hermes / Codex。"
        )
    mode = (permission_mode or "").strip()
    if mode not in _CURSOR_PERMISSION_MODES:
        mode = _DEFAULT_CURSOR_PERMISSION_MODE
    argv = [agent, "-p", "--output-format", "text", "--workspace", str(_REPO_ROOT)]
    if mode == "force":
        argv.append("--force")
    elif mode == "auto_review":
        argv.append("--auto-review")
    else:
        argv.extend(["--mode", mode])
    model_id = _resolve_native_model("cursor", model)
    argv.extend(["--model", model_id])
    if executor_session_id:
        argv.extend(["--resume", executor_session_id])
    argv.append(prompt)
    proc = _run_cmd(argv, cwd=_REPO_ROOT, timeout=timeout)
    out = _clean_assistant_text(proc.stdout or "")
    err = (proc.stderr or "").strip()
    if proc.returncode != 0 and not out:
        raise AgentTurnError(f"cursor agent 退出码 {proc.returncode}: {err or '(no stderr)'}")
    if not out:
        # json format fallback parse
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            try:
                data = json.loads(raw)
                out = str(data.get("result") or data.get("message") or data.get("text") or raw)
            except json.JSONDecodeError:
                out = raw
        else:
            out = err or "（Cursor Agent 无输出）"
    if _looks_like_executor_error(out) or out.strip() in (
        "（Cursor Agent 无输出）",
        "(Cursor Agent 无输出)",
    ):
        detail = err or out
        raise AgentTurnError(
            f"Cursor Agent 无有效回复：{detail}\n\n"
            "请确认已安装 Cursor Agent CLI（`agent` / `cursor-agent`，不是 `cursor` 编辑器命令），"
            "并已登录；或把程序员执行器改为 Hermes / Codex。"
        )
    sid = executor_session_id
    m = re.search(r"chatId[\"'\s:]+([a-zA-Z0-9_-]+)", f"{proc.stdout}\n{err}")
    if m:
        sid = m.group(1)
    return out, sid, err


def run_pi_executor_turn(
    prompt: str,
    *,
    role_kind: str,
    timeout: int = _DEFAULT_TIMEOUT,
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
    session_id: str | None = None,
) -> tuple[str, str | None, str]:
    from pi_runtime import PiRuntimeError, run_pi_agent_turn

    system = _load_skill_text(role_kind)
    try:
        result = run_pi_agent_turn(
            system_prompt=system,
            user_text=prompt,
            config=config,
            instance_id=instance_id,
            role_kind=role_kind,
            session_id=session_id,
            max_tool_rounds=4 if role_kind == "it" else 2,
            timeout_sec=float(min(timeout, 240)),
            tool_profile="it",
            allow_export=False,
        )
    except PiRuntimeError as exc:
        raise AgentTurnError(f"内置 Pi 失败：{exc}") from exc

    text = str(result.get("assistant_message") or "").strip()
    if not text:
        raise AgentTurnError("内置 Pi 无输出")
    trace = result.get("tool_trace") or []
    if trace:
        bits = []
        for item in trace[:6]:
            argv = " ".join(str(x) for x in (item.get("argv") or []))
            mark = "ok" if item.get("ok") else "fail"
            bits.append(f"`{argv}` → {mark}")
        text = text + "\n\n—— 工具：" + "；".join(bits)
    return text, None, ""


def run_executor_turn(
    executor: str,
    prompt: str,
    *,
    role_kind: str,
    executor_session_id: str | None,
    timeout: int = _DEFAULT_TIMEOUT,
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
    resolved_auth: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> tuple[str, str | None, str]:
    if executor == "pi":
        return run_pi_executor_turn(
            prompt,
            role_kind=role_kind,
            timeout=timeout,
            config=config,
            instance_id=instance_id,
            session_id=session_id,
        )
    if executor == "hermes":
        return run_hermes_turn(
            prompt,
            role_kind=role_kind,
            executor_session_id=executor_session_id,
            timeout=timeout,
            config=config,
            resolved_auth=resolved_auth,
            instance_id=instance_id,
        )
    if executor == "codex":
        return run_codex_turn(
            prompt,
            executor_session_id=executor_session_id,
            timeout=timeout,
            sandbox=resolve_codex_sandbox(config, instance_id=instance_id),
            model=(resolved_auth or {}).get("model"),
        )
    if executor == "cursor":
        _require_cursor_force_for_cli(config, instance_id=instance_id)
        return run_cursor_turn(
            prompt,
            executor_session_id=executor_session_id,
            timeout=timeout,
            model=(resolved_auth or {}).get("model"),
            permission_mode="force",
        )
    raise AgentTurnError(f"Unsupported executor: {executor}")


def record_turn_exchange(
    *,
    role_kind: str,
    session_id: str,
    user_message: str,
    assistant_message: str,
    executor: str | None = None,
) -> dict[str, Any]:
    """Append user+assistant to session without calling executor CLI (GUI ACP path)."""
    if role_kind not in ROLE_KINDS:
        raise AgentTurnError(f"Unsupported role_kind: {role_kind}")
    if not user_message or not str(user_message).strip():
        raise AgentTurnError("message is required.")
    if not assistant_message or not str(assistant_message).strip():
        raise AgentTurnError("assistant_message is required.")

    path = session_path_for(role_kind, session_id)
    if path.is_file():
        session = load_session(path)
    else:
        session = new_session(role_kind, session_id)

    chosen = _normalize_executor(executor)
    if chosen:
        session["executor"] = chosen

    user_text = user_message.strip()
    display_message = assistant_message.strip()
    messages = list(session.get("messages") or [])
    messages.append({"role": "user", "content": user_text, "ts": _utc_now()})
    messages.append({"role": "assistant", "content": display_message, "ts": _utc_now()})
    session["messages"] = messages
    save_session(path, session)

    return {
        "ok": True,
        "status": "ok",
        "role_kind": role_kind,
        "session_id": session.get("id"),
        "session_path": str(path.resolve()),
        "executor": session.get("executor") or chosen,
        "assistant_message": display_message,
        "message_count": len(messages),
    }


def run_turn(
    *,
    role_kind: str,
    session_id: str,
    message: str,
    config: dict[str, Any],
    executor: str | None = None,
    brief_path: Path | None = None,
    progress_path: Path | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
    instance_id: str | None = None,
    programmer_roster: list[dict[str, str]] | None = None,
    default_target_instance_id: str | None = None,
) -> dict[str, Any]:
    """Append user message, call executor CLI, persist, return GUI payload."""
    if role_kind not in ROLE_KINDS:
        raise AgentTurnError(f"Unsupported role_kind: {role_kind}")
    if not message or not str(message).strip():
        raise AgentTurnError("message is required.")

    path = session_path_for(role_kind, session_id)
    if path.is_file():
        session = load_session(path)
    else:
        session = new_session(role_kind, session_id)

    resolved_auth = resolve_agent_auth(config, role_kind=role_kind, instance_id=instance_id)
    chosen = resolve_executor_for_role(role_kind, config, executor, instance_id=instance_id)
    session["executor"] = chosen

    if chosen == "pi" and resolved_auth.get("error"):
        raise AgentTurnError(_auth_failure_hint(resolved_auth))

    user_text = message.strip()
    messages = list(session.get("messages") or [])
    messages.append({"role": "user", "content": user_text, "ts": _utc_now()})
    session["messages"] = messages

    prompt = build_prompt(
        role_kind=role_kind,
        user_message=user_text,
        session=session,
        brief_path=brief_path,
        progress_path=progress_path,
        programmer_roster=programmer_roster,
        default_target_instance_id=default_target_instance_id,
        instance_id=instance_id,
    )

    assistant, exec_sid, stderr_tail = run_executor_turn(
        chosen,
        prompt,
        role_kind=role_kind,
        executor_session_id=session.get("executor_session_id"),
        timeout=timeout,
        config=config,
        instance_id=instance_id,
        resolved_auth=resolved_auth,
        session_id=session_id,
    )
    if exec_sid:
        session["executor_session_id"] = exec_sid

    brief = brief_path or _find_default_brief()
    progress = progress_path or _find_default_progress()
    dispatch_result: dict[str, Any] | None = None
    display_message = assistant

    try:
        from handoff import (
            apply_product_host_dispatch,
            apply_programmer_done,
            extract_dispatch_payload,
            strip_dispatch_fence,
        )

        payload = extract_dispatch_payload(assistant)
        if role_kind == "product_host" and payload:
            display_message = strip_dispatch_fence(assistant)
            dispatch_result = apply_product_host_dispatch(
                payload,
                assistant_message=display_message,
                progress_path=progress,
                brief_path=brief,
                from_session_id=str(session.get("id") or session_id),
                default_target_instance_id=default_target_instance_id,
            )
            bits: list[str] = []
            if dispatch_result.get("handoff_path"):
                tid = dispatch_result.get("target_instance_id")
                bits.append(
                    f"已写 handoff：`{dispatch_result['handoff_path']}`"
                    + (f"（目标实例 `{tid}`）" if tid else "")
                )
            if dispatch_result.get("progress_note_written") and progress and progress.is_file():
                bits.append(f"已记 progress：`{progress}`")
            if dispatch_result.get("task_updated"):
                bits.append(f"task `{dispatch_result['task_updated']}` → in_progress")
            if dispatch_result.get("dispatch_to") == "pipeline":
                bits.append("分诊为资产/pipeline：请按下方建议命令定点重跑")
            actions = dispatch_result.get("next_actions") or []
            if actions:
                bits.append("建议命令：\n- " + "\n- ".join(str(a) for a in actions[:6]))
            if bits:
                display_message = display_message + "\n\n—— " + "；".join(bits)
        elif role_kind == "programmer" and payload:
            display_message = strip_dispatch_fence(assistant)
            done_id = payload.get("handoff_done")
            if done_id:
                try:
                    done = apply_programmer_done(
                        str(done_id),
                        progress_path=progress,
                        progress_note=str(payload.get("progress_note") or "").strip() or None,
                    )
                    dispatch_result = done
                    display_message += f"\n\n—— handoff `{done_id}` 已标为 done"
                    if done.get("task_done"):
                        display_message += f"；task `{done['task_done']}` → done"
                except Exception as exc:  # noqa: BLE001
                    dispatch_result = {"handoff_done": done_id, "error": str(exc)}
                    display_message += f"\n\n—— 关单失败：{exc}"
            else:
                dispatch_result = {"payload": payload}
    except Exception as exc:  # noqa: BLE001 — never fail the chat on handoff IO
        dispatch_result = {"error": str(exc)}

    messages.append({"role": "assistant", "content": display_message, "ts": _utc_now()})
    session["messages"] = messages
    save_session(path, session)

    out: dict[str, Any] = {
        "ok": True,
        "status": "ok",
        "role_kind": role_kind,
        "session_id": session.get("id"),
        "session_path": str(path.resolve()),
        "executor": chosen,
        "executor_session_id": session.get("executor_session_id"),
        "assistant_message": display_message,
        "message_count": len(messages),
        "stderr_tail": (stderr_tail or "")[-2000:],
    }
    if dispatch_result:
        out["dispatch"] = dispatch_result
    return out


def session_status(role_kind: str, session_id: str) -> dict[str, Any]:
    path = session_path_for(role_kind, session_id)
    if not path.is_file():
        return {"exists": False, "session_id": sanitize_session_id(session_id), "role_kind": role_kind}
    session = load_session(path)
    return {
        "exists": True,
        "session_id": session.get("id"),
        "role_kind": session.get("role") or role_kind,
        "executor": session.get("executor"),
        "executor_session_id": session.get("executor_session_id"),
        "message_count": len(session.get("messages") or []),
        "session_path": str(path.resolve()),
    }
