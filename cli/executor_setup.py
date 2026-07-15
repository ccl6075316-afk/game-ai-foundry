"""Step-by-step executor setup (Codex, Hermes, Cursor) for GUI wizard."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from llm_config import resolve_host_api_settings

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"
_CODEX_AUTH = Path.home() / ".codex" / "auth.json"
_HERMES_ENV = Path.home() / ".hermes" / ".env"
_HERMES_CONFIG = Path.home() / ".hermes" / "config.yaml"

ProgressCb = Callable[[str], None] | None

EXECUTOR_IDS = ("codex", "hermes", "cursor")

CODEX_INSTALL_URL = "https://github.com/openai/codex"
CURSOR_INSTALL_URL = "https://cursor.com"
HERMES_INSTALL_URL = "https://github.com/NousResearch/hermes-agent"


def _emit(progress: ProgressCb, message: str) -> None:
    if progress:
        progress(message)


def _load_config() -> dict[str, Any]:
    if not _CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _key_usable(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and "YOUR_" not in text.upper()


def resolve_openrouter_api_key(config: dict[str, Any] | None = None) -> str | None:
    """Read OpenRouter key from provider_accounts or host/prompt fallbacks."""
    config = config or _load_config()
    accounts = config.get("provider_accounts")
    if isinstance(accounts, dict):
        or_acc = accounts.get("openrouter")
        if isinstance(or_acc, dict) and _key_usable(or_acc.get("api_key")):
            return str(or_acc["api_key"]).strip()

    host = config.get("host")
    if isinstance(host, dict) and host.get("provider") == "openrouter":
        if _key_usable(host.get("api_key")):
            return str(host["api_key"]).strip()

    settings = resolve_host_api_settings(config)
    key = settings.get("api_key")
    if _key_usable(key):
        return str(key).strip()
    return None


def _codex_logged_in() -> bool:
    if not _CODEX_AUTH.is_file():
        return False
    try:
        data = json.loads(_CODEX_AUTH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    tokens = data.get("tokens")
    if isinstance(tokens, dict) and tokens:
        return True
    return _key_usable(data.get("OPENAI_API_KEY"))


def _hermes_skills_installed() -> bool:
    from hermes_pack import HERMES_PACKAGES, resolve_hermes_install_dir

    install_dir = resolve_hermes_install_dir()
    for pkg, meta in HERMES_PACKAGES.items():
        if not meta.get("role"):
            continue
        if not (install_dir / pkg / "SKILL.md").is_file() and not (install_dir / pkg).exists():
            return False
    return True


def _read_env_value(env_path: Path, key: str) -> str | None:
    if not env_path.is_file():
        return None
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(f"{key}="):
            val = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            return val if val else None
    return None


def _hermes_openrouter_configured() -> bool:
    key = _read_env_value(_HERMES_ENV, "OPENROUTER_API_KEY")
    if _key_usable(key):
        return True
    if not _HERMES_CONFIG.is_file():
        return False
    try:
        text = _HERMES_CONFIG.read_text(encoding="utf-8")
    except OSError:
        return False
    provider_match = re.search(r"(?m)^\s*provider:\s*(\S+)\s*$", text)
    if provider_match and provider_match.group(1).strip().lower() == "openrouter":
        return _key_usable(_read_env_value(_HERMES_ENV, "OPENROUTER_API_KEY"))
    return False


def _step_specs(executor_id: str) -> list[dict[str, Any]]:
    if executor_id == "codex":
        return [
            {"id": "install_cli", "label": "安装 Codex CLI", "hint": "npm install -g @openai/codex"},
            {"id": "login", "label": "浏览器登录 OpenAI", "hint": "将打开浏览器完成 OAuth"},
        ]
    if executor_id == "hermes":
        return [
            {"id": "install_cli", "label": "安装 Hermes CLI", "hint": "pip install hermes-agent"},
            {"id": "install_skills", "label": "安装本项目 Skills", "hint": "写入 ~/.hermes/skills"},
            {
                "id": "configure_api",
                "label": "同步 OpenRouter API",
                "hint": "从设置页 OpenRouter Key 写入 ~/.hermes/.env",
            },
        ]
    if executor_id == "cursor":
        return [
            {
                "id": "open_download",
                "label": "安装 Cursor IDE",
                "hint": "打开 cursor.com 下载",
                "optional": True,
            },
            {"id": "verify_cli", "label": "检测 Cursor CLI", "hint": "在 Cursor 中安装 shell 命令"},
        ]
    raise ValueError(f"未知执行器: {executor_id}")


def _step_done(executor_id: str, step_id: str) -> bool:
    cli = shutil.which({"codex": "codex", "hermes": "hermes", "cursor": "cursor"}[executor_id])
    if executor_id == "codex":
        if step_id == "install_cli":
            return bool(cli)
        if step_id == "login":
            return _codex_logged_in()
    if executor_id == "hermes":
        if step_id == "install_cli":
            return bool(cli)
        if step_id == "install_skills":
            return _hermes_skills_installed()
        if step_id == "configure_api":
            return _hermes_openrouter_configured()
    if executor_id == "cursor":
        if step_id == "open_download":
            return False
        if step_id == "verify_cli":
            return bool(cli)
    return False


def _executor_meta(executor_id: str) -> dict[str, str]:
    meta = {
        "codex": {
            "label": "Codex CLI",
            "description": "OpenAI 登录式代码执行器；写玩法时用，无需 OpenRouter Key",
            "download_url": CODEX_INSTALL_URL,
        },
        "hermes": {
            "label": "Hermes 助手",
            "description": "独立 AI 助手；可自动同步 OpenRouter Key 与 Skills",
            "download_url": HERMES_INSTALL_URL,
        },
        "cursor": {
            "label": "Cursor CLI",
            "description": "随 Cursor IDE 安装；登录式，GUI 对话仍走 LLM Provider",
            "download_url": CURSOR_INSTALL_URL,
        },
    }
    return meta[executor_id]


def _build_steps(executor_id: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    found_active = False
    for spec in _step_specs(executor_id):
        done = _step_done(executor_id, spec["id"])
        active = not done and not found_active
        if active:
            found_active = True
        steps.append({**spec, "done": done, "active": active})
    return steps


def executor_status(executor_id: str) -> dict[str, Any]:
    if executor_id not in EXECUTOR_IDS:
        raise ValueError(f"未知执行器: {executor_id}")
    meta = _executor_meta(executor_id)
    steps = _build_steps(executor_id)
    cli_name = executor_id
    path = shutil.which(cli_name)
    required_steps = [s for s in steps if not s.get("optional")]
    ready = all(s["done"] for s in required_steps)
    return {
        "id": executor_id,
        "label": meta["label"],
        "description": meta["description"],
        "download_url": meta["download_url"],
        "ready": ready,
        "path": path,
        "steps": steps,
    }


def all_executor_status() -> dict[str, Any]:
    executors = {eid: executor_status(eid) for eid in EXECUTOR_IDS}
    return {"executors": executors}


def _run(cmd: list[str], progress: ProgressCb = None) -> None:
    _emit(progress, f"运行: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout.strip():
        for line in proc.stdout.splitlines():
            _emit(progress, line)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"命令失败 (exit {proc.returncode})")


def _spawn_detached(cmd: list[str]) -> None:
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def _write_env_key(env_path: Path, key: str, value: str) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    replaced = False
    if env_path.is_file():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
    out: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")
    env_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def _install_codex_cli(progress: ProgressCb = None) -> dict[str, Any]:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("未找到 npm，请先安装 Node.js (https://nodejs.org)")
    _emit(progress, "正在安装 @openai/codex…")
    _run([npm, "install", "-g", "@openai/codex"], progress)
    if not shutil.which("codex"):
        raise RuntimeError("安装完成但未在 PATH 中找到 codex，请重启终端或 GUI 后重试")
    return {"ok": True, "path": shutil.which("codex")}


def _login_codex(progress: ProgressCb = None) -> dict[str, Any]:
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("Codex CLI 未安装，请先完成「安装 Codex CLI」")
    if _codex_logged_in():
        return {"ok": True, "already": True}
    _emit(progress, "启动 codex login（将打开浏览器）…")
    _spawn_detached([codex, "login"])
    return {"ok": True, "started": True, "message": "已在后台启动 codex login，请在浏览器完成授权后点击「重新检测」"}


def _install_hermes_cli(progress: ProgressCb = None) -> dict[str, Any]:
    _emit(progress, "正在安装 hermes-agent…")
    _run([sys.executable, "-m", "pip", "install", "-U", "hermes-agent"], progress)
    if not shutil.which("hermes"):
        raise RuntimeError("安装完成但未在 PATH 中找到 hermes，请重启终端或 GUI 后重试")
    return {"ok": True, "path": shutil.which("hermes")}


def _install_hermes_skills(progress: ProgressCb = None) -> dict[str, Any]:
    if not shutil.which("hermes"):
        raise RuntimeError("Hermes CLI 未安装，请先完成「安装 Hermes CLI」")
    _emit(progress, "安装 Hermes skills…")
    from hermes_pack import install_hermes_skills

    written = install_hermes_skills()
    return {"ok": True, "skills_installed": len(written)}


def _configure_hermes_api(progress: ProgressCb = None) -> dict[str, Any]:
    if not shutil.which("hermes"):
        raise RuntimeError("Hermes CLI 未安装，请先完成「安装 Hermes CLI」")
    config = _load_config()
    api_key = resolve_openrouter_api_key(config)
    if not api_key:
        raise RuntimeError(
            "未找到 OpenRouter API Key。请先在「设置 → 生文 Provider」配置 OpenRouter 后再试。"
        )
    _emit(progress, "写入 ~/.hermes/.env …")
    _write_env_key(_HERMES_ENV, "OPENROUTER_API_KEY", api_key)
    _emit(progress, "设置 Hermes model.provider = openrouter …")
    _run(["hermes", "config", "set", "model.provider", "openrouter"], progress)

    host_model = None
    host = config.get("host")
    if isinstance(host, dict) and host.get("model"):
        host_model = str(host["model"]).strip()
    if host_model:
        _emit(progress, f"设置默认模型 {host_model} …")
        _run(["hermes", "config", "set", "model.default", host_model], progress)

    return {"ok": True, "env_path": str(_HERMES_ENV)}


def _open_cursor_download(progress: ProgressCb = None) -> dict[str, Any]:
    import webbrowser

    _emit(progress, f"打开 {CURSOR_INSTALL_URL}")
    webbrowser.open(CURSOR_INSTALL_URL)
    return {"ok": True, "url": CURSOR_INSTALL_URL}


def _verify_cursor_cli(progress: ProgressCb = None) -> dict[str, Any]:
    path = shutil.which("cursor")
    if path:
        return {"ok": True, "path": path}
    raise RuntimeError(
        "未检测到 cursor 命令。请在 Cursor IDE 中打开命令面板，搜索 "
        "「Shell Command: Install 'cursor' command in PATH」并执行。"
    )


def run_executor_step(
    executor_id: str,
    step_id: str,
    progress: ProgressCb = None,
) -> dict[str, Any]:
    if executor_id not in EXECUTOR_IDS:
        raise ValueError(f"未知执行器: {executor_id}")
    valid_ids = {s["id"] for s in _step_specs(executor_id)}
    if step_id not in valid_ids:
        raise ValueError(f"未知步骤: {step_id}")

    handlers: dict[tuple[str, str], Callable[[ProgressCb], dict[str, Any]]] = {
        ("codex", "install_cli"): _install_codex_cli,
        ("codex", "login"): _login_codex,
        ("hermes", "install_cli"): _install_hermes_cli,
        ("hermes", "install_skills"): _install_hermes_skills,
        ("hermes", "configure_api"): _configure_hermes_api,
        ("cursor", "open_download"): _open_cursor_download,
        ("cursor", "verify_cli"): _verify_cursor_cli,
    }
    handler = handlers.get((executor_id, step_id))
    if not handler:
        raise RuntimeError(f"未实现: {executor_id}/{step_id}")

    result = handler(progress)
    result["executor"] = executor_id
    result["step"] = step_id
    result["status"] = executor_status(executor_id)
    return result
