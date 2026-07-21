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
from hermes_pack import hermes_home

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"
_CODEX_AUTH = Path.home() / ".codex" / "auth.json"


def _codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def _codex_config_path() -> Path:
    return _codex_home() / "config.toml"


def _codex_env_path() -> Path:
    return _codex_home() / ".env"


def _hermes_env_path() -> Path:
    return hermes_home() / ".env"


def _hermes_config_path() -> Path:
    return hermes_home() / "config.yaml"

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
    """Backward-compatible helper: OpenRouter key from provider_accounts / host."""
    config = config or _load_config()
    accounts = config.get("provider_accounts")
    if isinstance(accounts, dict):
        or_acc = accounts.get("openrouter")
        if isinstance(or_acc, dict) and _key_usable(or_acc.get("api_key")):
            return str(or_acc["api_key"]).strip()
    host = config.get("host") if isinstance(config.get("host"), dict) else {}
    if str(host.get("provider") or "openrouter").lower() == "openrouter" and _key_usable(host.get("api_key")):
        return str(host["api_key"]).strip()
    return None


# Foundry provider_accounts id → Hermes model.provider + env key name
_HERMES_PROVIDER_MAP: dict[str, tuple[str, str]] = {
    "openrouter": ("openrouter", "OPENROUTER_API_KEY"),
    "openai": ("openai-api", "OPENAI_API_KEY"),
    # OpenAI-compatible → Hermes custom + base_url
    "deepseek": ("custom", "OPENAI_API_KEY"),
    "kimi": ("custom", "OPENAI_API_KEY"),
    "glm": ("custom", "OPENAI_API_KEY"),
    "gemini": ("custom", "OPENAI_API_KEY"),
    "custom": ("custom", "OPENAI_API_KEY"),
}

# Foundry provider_accounts id → default OpenAI-compatible base URL for Codex
_CODEX_DEFAULT_BASE_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "kimi": "https://api.moonshot.cn/v1",
}

# Foundry provider → env var Codex reads via model_providers.*.env_key
_CODEX_ENV_KEYS: dict[str, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "kimi": "OPENAI_API_KEY",
    "glm": "OPENAI_API_KEY",
    "gemini": "OPENAI_API_KEY",
    "custom": "OPENAI_API_KEY",
}

# Codex CLI ≥ 0.30 (2026): custom providers in ~/.codex/config.toml [model_providers.*]
# Reserved built-in IDs: openai, ollama, lmstudio — use foundry_* prefix.
_CODEX_SYNC_DOC = (
    "Writes ~/.codex/config.toml model/model_provider and [model_providers.foundry_*], "
    "plus API key to ~/.codex/.env (env_key). Requires Codex CLI that honors config.toml "
    "custom model_providers (OpenAI Codex config reference, 2026)."
)


def _configured_hermes_provider_id(config: dict[str, Any]) -> str | None:
    """Dedicated Hermes provider pick (independent of GUI 生文 active provider)."""
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    # Prefer top-level agents.hermes_provider
    raw = agents.get("hermes_provider") if isinstance(agents, dict) else None
    if not raw:
        orch = agents.get("orchestrator") if isinstance(agents.get("orchestrator"), dict) else {}
        raw = orch.get("provider") if isinstance(orch, dict) else None
    if not raw:
        return None
    pid = str(raw).strip().lower()
    return pid or None


def resolve_hermes_sync_settings(
    config: dict[str, Any] | None = None,
    *,
    provider_id: str | None = None,
) -> dict[str, Any]:
    """Resolve which Foundry text provider to sync into Hermes.

    Preference:
      1. explicit provider_id (CLI --provider)
      2. config.agents.hermes_provider (GUI Hermes 专用选择)
      3. config.host.provider (生文当前选中，兼容旧配置)
      4. openrouter
    Credentials always from provider_accounts[id] (多家账号库), else host block.
    """
    config = config or _load_config()
    host = config.get("host") if isinstance(config.get("host"), dict) else {}
    accounts = (
        config.get("provider_accounts")
        if isinstance(config.get("provider_accounts"), dict)
        else {}
    )

    foundry_id = str(
        provider_id
        or _configured_hermes_provider_id(config)
        or host.get("provider")
        or "openrouter"
    ).strip().lower()
    if not foundry_id:
        foundry_id = "openrouter"
    if foundry_id not in _HERMES_PROVIDER_MAP:
        foundry_id = "custom"

    hermes_provider, env_key = _HERMES_PROVIDER_MAP[foundry_id]
    acc = accounts.get(foundry_id) if isinstance(accounts.get(foundry_id), dict) else {}
    host_provider = str(host.get("provider") or "").strip().lower()
    host_is_this = host_provider == foundry_id

    api_key = None
    if _key_usable(acc.get("api_key")):
        api_key = str(acc["api_key"]).strip()
    elif host_is_this and _key_usable(host.get("api_key")):
        api_key = str(host["api_key"]).strip()

    api_base = None
    if isinstance(acc.get("api_base"), str) and acc["api_base"].strip():
        api_base = acc["api_base"].strip()
    elif host_is_this and isinstance(host.get("api_base"), str) and str(host["api_base"]).strip():
        api_base = str(host["api_base"]).strip()

    model = None
    if isinstance(acc.get("text_model"), str) and acc["text_model"].strip():
        model = acc["text_model"].strip()
    elif isinstance(acc.get("model"), str) and acc["model"].strip():
        model = acc["model"].strip()
    elif host_is_this and isinstance(host.get("model"), str) and str(host["model"]).strip():
        model = str(host["model"]).strip()

    return {
        "foundry_provider": foundry_id,
        "hermes_provider": hermes_provider,
        "env_key": env_key,
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


def _configured_codex_provider_id(config: dict[str, Any]) -> str | None:
    """Programmer (godot-developer) provider pick from role block."""
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    dev = agents.get("godot-developer") if isinstance(agents.get("godot-developer"), dict) else {}
    raw = dev.get("provider") if isinstance(dev, dict) else None
    if not raw:
        return None
    pid = str(raw).strip().lower()
    return pid or None


def _codex_use_third_party(config: dict[str, Any], instance_id: str | None = None) -> bool:
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    role_block = agents.get("godot-developer") if isinstance(agents.get("godot-developer"), dict) else {}
    instance: dict[str, Any] | None = None
    if instance_id:
        instances = agents.get("instances") if isinstance(agents.get("instances"), dict) else {}
        raw = instances.get(instance_id)
        if isinstance(raw, dict):
            instance = raw
    merged = dict(role_block)
    if instance:
        for key in ("provider", "model", "use_third_party"):
            if key in instance and instance[key] is not None:
                merged[key] = instance[key]
    return bool(merged.get("use_third_party", False))


def _codex_model_provider_id(foundry_id: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", foundry_id.lower()).strip("_")
    return f"foundry_{safe or 'custom'}"


def _codex_env_key_for(foundry_id: str) -> str:
    return _CODEX_ENV_KEYS.get(foundry_id, "OPENAI_API_KEY")


def resolve_codex_sync_settings(
    config: dict[str, Any] | None = None,
    *,
    provider_id: str | None = None,
    instance_id: str | None = None,
) -> dict[str, Any]:
    """Resolve Foundry provider credentials to sync into Codex third-party config.

    Preference:
      1. explicit provider_id (CLI --provider)
      2. agents.instances[instance_id] overlay on godot-developer (when instance_id set)
      3. agents.godot-developer.provider
      4. config.host.provider
      5. openrouter

    ``use_third_party`` comes from instance overlay or godot-developer role block.
    When false, callers must not write Codex config (subscription mode).
    """
    config = config or _load_config()
    host = config.get("host") if isinstance(config.get("host"), dict) else {}
    accounts = (
        config.get("provider_accounts")
        if isinstance(config.get("provider_accounts"), dict)
        else {}
    )
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    role_block = agents.get("godot-developer") if isinstance(agents.get("godot-developer"), dict) else {}

    instance: dict[str, Any] | None = None
    if instance_id:
        instances = agents.get("instances") if isinstance(agents.get("instances"), dict) else {}
        raw = instances.get(instance_id)
        if isinstance(raw, dict):
            instance = raw

    merged = dict(role_block)
    if instance:
        for key in ("provider", "model", "use_third_party"):
            if key in instance and instance[key] is not None:
                merged[key] = instance[key]

    use_third_party = bool(merged.get("use_third_party", False))

    foundry_id = str(
        provider_id
        or merged.get("provider")
        or _configured_codex_provider_id(config)
        or host.get("provider")
        or "openrouter"
    ).strip().lower()
    if not foundry_id:
        foundry_id = "openrouter"

    acc = accounts.get(foundry_id) if isinstance(accounts.get(foundry_id), dict) else {}
    host_provider = str(host.get("provider") or "").strip().lower()
    host_is_this = host_provider == foundry_id

    api_key = None
    if _key_usable(acc.get("api_key")):
        api_key = str(acc["api_key"]).strip()
    elif host_is_this and _key_usable(host.get("api_key")):
        api_key = str(host["api_key"]).strip()

    api_base = None
    if isinstance(acc.get("api_base"), str) and acc["api_base"].strip():
        api_base = acc["api_base"].strip()
    elif host_is_this and isinstance(host.get("api_base"), str) and str(host["api_base"]).strip():
        api_base = str(host["api_base"]).strip()
    elif foundry_id in _CODEX_DEFAULT_BASE_URLS:
        api_base = _CODEX_DEFAULT_BASE_URLS[foundry_id]

    model = None
    if isinstance(merged.get("model"), str) and str(merged["model"]).strip():
        model = str(merged["model"]).strip()
    elif isinstance(acc.get("text_model"), str) and acc["text_model"].strip():
        model = acc["text_model"].strip()
    elif isinstance(acc.get("model"), str) and acc["model"].strip():
        model = acc["model"].strip()
    elif host_is_this and isinstance(host.get("model"), str) and str(host["model"]).strip():
        model = str(host["model"]).strip()

    codex_provider_id = _codex_model_provider_id(foundry_id)
    env_key = _codex_env_key_for(foundry_id)

    return {
        "foundry_provider": foundry_id,
        "codex_provider_id": codex_provider_id,
        "env_key": env_key,
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
        "use_third_party": use_third_party,
        "instance_id": instance_id,
    }


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


def _read_toml_value(text: str, key: str) -> str | None:
    match = re.search(rf'(?m)^{re.escape(key)}\s*=\s*"([^"]*)"', text)
    if match:
        return match.group(1)
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*'([^']*)'", text)
    if match:
        return match.group(1)
    return None


def _set_toml_top_level(text: str, key: str, value: str) -> str:
    line = f'{key} = "{value}"'
    pattern = rf"(?m)^{re.escape(key)}\s*=.*$"
    if re.search(pattern, text):
        return re.sub(pattern, line, text, count=1)
    stripped = text.rstrip()
    if stripped:
        return stripped + "\n" + line + "\n"
    return line + "\n"


def _upsert_toml_table(text: str, table_header: str, body_lines: list[str]) -> str:
    section = table_header.strip()
    body = "\n".join(body_lines).rstrip() + "\n"
    block = section + "\n" + body
    pattern = rf"(?m)^{re.escape(section)}\s*\n(?:[^\[][^\n]*\n)*"
    if re.search(pattern, text):
        return re.sub(pattern, block, text, count=1)
    stripped = text.rstrip()
    if stripped:
        return stripped + "\n\n" + block
    return block


def _codex_third_party_configured(sync: dict[str, Any] | None = None) -> bool:
    sync = sync or resolve_codex_sync_settings()
    if not sync.get("use_third_party"):
        return True
    config_path = _codex_config_path()
    if not config_path.is_file():
        return False
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return False
    expected_provider = sync.get("codex_provider_id")
    if _read_toml_value(text, "model_provider") != expected_provider:
        return False
    env_key = sync.get("env_key")
    if env_key and not _key_usable(_read_env_value(_codex_env_path(), str(env_key))):
        return False
    return True


def _hermes_skills_installed() -> bool:
    from hermes_pack import HERMES_PACKAGES, resolve_hermes_install_dir

    install_dir = resolve_hermes_install_dir()
    for pkg, meta in HERMES_PACKAGES.items():
        if not meta.get("role"):
            continue
        if not (install_dir / pkg / "SKILL.md").is_file():
            return False
    return bool(HERMES_PACKAGES)


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


def _hermes_api_configured() -> bool:
    """True if Hermes has a usable API key for any supported provider."""
    env_path = _hermes_env_path()
    config_path = _hermes_config_path()
    if _key_usable(_read_env_value(env_path, "OPENROUTER_API_KEY")):
        return True
    if _key_usable(_read_env_value(env_path, "OPENAI_API_KEY")):
        return True
    if not config_path.is_file():
        return False
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return False
    # model.api_key inline or provider set with matching env
    if re.search(r"(?m)^\s*api_key:\s*\S+", text):
        return True
    provider_match = re.search(r"(?m)^\s*provider:\s*(\S+)\s*$", text)
    if not provider_match:
        return False
    provider = provider_match.group(1).strip().lower().strip("\"'")
    if provider == "openrouter":
        return _key_usable(_read_env_value(env_path, "OPENROUTER_API_KEY"))
    if provider in ("openai-api", "custom", "openai"):
        return _key_usable(_read_env_value(env_path, "OPENAI_API_KEY"))
    return False


def _hermes_openrouter_configured() -> bool:
    """Deprecated alias."""
    return _hermes_api_configured()


def _step_specs(executor_id: str) -> list[dict[str, Any]]:
    if executor_id == "codex":
        return [
            {"id": "install_cli", "label": "安装 Codex CLI", "hint": "npm install -g @openai/codex"},
            {"id": "login", "label": "浏览器登录 OpenAI", "hint": "将打开浏览器完成 OAuth"},
            {
                "id": "sync_api",
                "label": "同步第三方 Provider API",
                "hint": "启用「用第三方」时，把程序员 Provider 写入 ~/.codex/config.toml",
                "optional": True,
            },
        ]
    if executor_id == "hermes":
        return [
            {"id": "install_cli", "label": "安装 Hermes CLI", "hint": "pip install hermes-agent"},
            {"id": "install_skills", "label": "安装本项目 Skills", "hint": "写入 $HERMES_HOME/skills（或 ~/.hermes/skills）"},
            {
                "id": "configure_api",
                "label": "同步 Provider API",
                "hint": "把设置里当前生文 Provider（Key / base / 模型）写入 Hermes",
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
    if executor_id == "cursor":
        cli = shutil.which("agent") or shutil.which("cursor-agent") or shutil.which("cursor")
    else:
        cli = shutil.which({"codex": "codex", "hermes": "hermes"}[executor_id])
    if executor_id == "codex":
        if step_id == "install_cli":
            return bool(cli)
        if step_id == "login":
            return _codex_logged_in()
        if step_id == "sync_api":
            return _codex_third_party_configured()
    if executor_id == "hermes":
        if step_id == "install_cli":
            return bool(cli)
        if step_id == "install_skills":
            return _hermes_skills_installed()
        if step_id == "configure_api":
            return _hermes_api_configured()
    if executor_id == "cursor":
        if step_id == "open_download":
            return False
        if step_id == "verify_cli":
            return bool(shutil.which("agent") or shutil.which("cursor-agent") or bool(cli))
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
            "description": "独立 AI 助手；可同步设置页当前生文 Provider 与 Skills",
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
    if executor_id == "cursor":
        path = shutil.which("agent") or shutil.which("cursor-agent") or shutil.which("cursor")
    else:
        path = shutil.which(executor_id)
    required_steps = [s for s in steps if not s.get("optional")]
    ready = all(s["done"] for s in required_steps)
    payload: dict[str, Any] = {
        "id": executor_id,
        "label": meta["label"],
        "description": meta["description"],
        "download_url": meta["download_url"],
        "cli_path": path,
        "path": path,
        "steps": steps,
        "ready": ready,
    }
    if executor_id == "hermes":
        sync = resolve_hermes_sync_settings()
        payload["sync_provider"] = sync["foundry_provider"]
        payload["sync_hermes_provider"] = sync["hermes_provider"]
        payload["sync_has_key"] = bool(sync.get("api_key"))
        payload["sync_model"] = sync.get("model")
        for step in steps:
            if step["id"] == "configure_api":
                key_note = "已有 Key" if sync.get("api_key") else "尚未填 Key"
                step["hint"] = (
                    f"同步设置中的生文 Provider「{sync['foundry_provider']}」"
                    f"（{key_note}）→ Hermes {sync['hermes_provider']}"
                )
                break
    if executor_id == "codex":
        sync = resolve_codex_sync_settings()
        payload["sync_provider"] = sync["foundry_provider"]
        payload["sync_codex_provider"] = sync["codex_provider_id"]
        payload["sync_has_key"] = bool(sync.get("api_key"))
        payload["sync_model"] = sync.get("model")
        payload["sync_use_third_party"] = bool(sync.get("use_third_party"))
        for step in steps:
            if step["id"] == "sync_api":
                if not sync.get("use_third_party"):
                    step["hint"] = "未启用第三方（订阅登录），无需同步"
                else:
                    key_note = "已有 Key" if sync.get("api_key") else "尚未填 Key"
                    step["hint"] = (
                        f"同步程序员 Provider「{sync['foundry_provider']}」"
                        f"（{key_note}）→ Codex {sync['codex_provider_id']}"
                    )
                break
    return payload


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
    n = len(written.get("packages") or [])
    mode = "符号链接" if written.get("symlink") else "复制"
    return {
        "ok": True,
        "skills_installed": n,
        "install_dir": written.get("install_dir"),
        "message": f"已安装 {n} 个 Hermes Skills（{mode}）→ {written.get('install_dir')}",
    }


def _configure_hermes_api(
    progress: ProgressCb = None,
    *,
    provider_id: str | None = None,
) -> dict[str, Any]:
    if not shutil.which("hermes"):
        raise RuntimeError("Hermes CLI 未安装，请先完成「安装 Hermes CLI」")
    config = _load_config()
    sync = resolve_hermes_sync_settings(config, provider_id=provider_id)
    api_key = sync.get("api_key")
    foundry = sync["foundry_provider"]
    if not api_key:
        raise RuntimeError(
            f"未找到 Provider「{foundry}」的 API Key。"
            "请先在「设置 → Provider」选好生文平台并填写 Key，保存后再同步。"
        )

    hermes_provider = sync["hermes_provider"]
    env_key = sync["env_key"]
    api_base = sync.get("api_base")
    model = sync.get("model")

    env_path = _hermes_env_path()
    _emit(progress, f"同步 Foundry Provider「{foundry}」→ Hermes「{hermes_provider}」…")
    _emit(progress, f"写入 {env_path} ({env_key}) …")
    _write_env_key(env_path, env_key, str(api_key))

    _emit(progress, f"设置 Hermes model.provider = {hermes_provider} …")
    _run(["hermes", "config", "set", "model.provider", hermes_provider], progress)

    if hermes_provider == "custom":
        if not api_base:
            raise RuntimeError(
                f"Provider「{foundry}」需要 api_base。"
                "请在设置里填写 API Base（或换用 OpenRouter / OpenAI）。"
            )
        _emit(progress, f"设置 model.base_url = {api_base} …")
        _run(["hermes", "config", "set", "model.base_url", str(api_base)], progress)
    elif hermes_provider == "openai-api" and api_base:
        _emit(progress, f"设置 model.base_url = {api_base} …")
        _run(["hermes", "config", "set", "model.base_url", str(api_base)], progress)
    elif hermes_provider == "openrouter":
        # Clear stale custom base_url from a previous sync
        try:
            _run(["hermes", "config", "set", "model.base_url", ""], progress)
        except RuntimeError:
            pass

    if model:
        _emit(progress, f"设置默认模型 {model} …")
        _run(["hermes", "config", "set", "model.default", str(model)], progress)

    return {
        "ok": True,
        "env_path": str(env_path),
        "hermes_home": str(hermes_home()),
        "foundry_provider": foundry,
        "hermes_provider": hermes_provider,
        "model": model,
        "api_base": api_base,
        "message": f"已同步 {foundry} → Hermes ({hermes_provider})"
        + (f" · 模型 {model}" if model else ""),
    }


def configure_codex_api(
    progress: ProgressCb = None,
    *,
    provider_id: str | None = None,
    instance_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sync Foundry provider_accounts into Codex third-party config.

    When ``use_third_party`` is false, returns ``ok=True`` with ``skipped`` and does
    not modify ``~/.codex/config.toml`` (preserves subscription login).

    Write path (Codex CLI config reference, 2026): ``~/.codex/config.toml`` top-level
    ``model`` / ``model_provider`` plus ``[model_providers.foundry_*]`` with
    ``base_url``, ``env_key``, ``wire_api``; API key in ``~/.codex/.env``.

    See module constant ``_CODEX_SYNC_DOC`` for version assumptions.
    """
    config = config if config is not None else _load_config()
    sync = resolve_codex_sync_settings(config, provider_id=provider_id, instance_id=instance_id)
    foundry = sync["foundry_provider"]

    if not sync.get("use_third_party"):
        return {
            "ok": True,
            "skipped": True,
            "use_third_party": False,
            "foundry_provider": foundry,
            "message": "未启用第三方（use_third_party=false），未修改 Codex 订阅配置。",
        }

    if not shutil.which("codex"):
        return {
            "ok": False,
            "error": "cli_missing",
            "message": "Codex CLI 未安装，请先完成「安装 Codex CLI」。",
            "foundry_provider": foundry,
        }

    api_key = sync.get("api_key")
    if not api_key:
        return {
            "ok": False,
            "error": "missing_key",
            "message": (
                f"未找到 Provider「{foundry}」的 API Key。"
                "请先在「设置 → Provider」填写 Key，保存后再同步。"
            ),
            "foundry_provider": foundry,
        }

    api_base = sync.get("api_base")
    if not api_base:
        return {
            "ok": False,
            "error": "missing_base_url",
            "message": (
                f"Provider「{foundry}」需要 api_base。"
                "请在设置里填写 API Base。"
            ),
            "foundry_provider": foundry,
        }

    codex_provider_id = sync["codex_provider_id"]
    env_key = sync["env_key"]
    model = sync.get("model")
    config_path = _codex_config_path()
    env_path = _codex_env_path()

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        existing = ""
        if config_path.is_file():
            existing = config_path.read_text(encoding="utf-8")

        _emit(progress, f"同步 Foundry Provider「{foundry}」→ Codex「{codex_provider_id}」…")
        _emit(progress, f"写入 {config_path} …")

        text = existing
        if model:
            text = _set_toml_top_level(text, "model", str(model))
        text = _set_toml_top_level(text, "model_provider", codex_provider_id)

        provider_name = f"Foundry {foundry}"
        body_lines = [
            f'name = "{provider_name}"',
            f'base_url = "{api_base}"',
            f'env_key = "{env_key}"',
            'wire_api = "responses"',
        ]
        table_header = f"[model_providers.{codex_provider_id}]"
        text = _upsert_toml_table(text, table_header, body_lines)
        config_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")

        _emit(progress, f"写入 {env_path} ({env_key}) …")
        _write_env_key(env_path, env_key, str(api_key))
    except OSError as exc:
        return {
            "ok": False,
            "error": "write_failed",
            "message": f"无法写入 Codex 配置: {exc}",
            "foundry_provider": foundry,
        }

    return {
        "ok": True,
        "config_path": str(config_path),
        "env_path": str(env_path),
        "foundry_provider": foundry,
        "codex_provider_id": codex_provider_id,
        "model": model,
        "api_base": api_base,
        "env_key": env_key,
        "use_third_party": True,
        "message": f"已同步 {foundry} → Codex ({codex_provider_id})"
        + (f" · 模型 {model}" if model else ""),
    }


def _configure_codex_api(
    progress: ProgressCb = None,
    *,
    provider_id: str | None = None,
    instance_id: str | None = None,
) -> dict[str, Any]:
    return configure_codex_api(
        progress,
        provider_id=provider_id,
        instance_id=instance_id,
    )


def _open_cursor_download(progress: ProgressCb = None) -> dict[str, Any]:
    import webbrowser

    _emit(progress, f"打开 {CURSOR_INSTALL_URL}")
    webbrowser.open(CURSOR_INSTALL_URL)
    return {"ok": True, "url": CURSOR_INSTALL_URL}


def _verify_cursor_cli(progress: ProgressCb = None) -> dict[str, Any]:
    path = shutil.which("agent") or shutil.which("cursor-agent") or shutil.which("cursor")
    if path and (shutil.which("agent") or shutil.which("cursor-agent")):
        return {"ok": True, "path": path}
    if path:
        raise RuntimeError(
            f"检测到编辑器命令 `{path}`，但未找到 Cursor Agent CLI（`agent` / `cursor-agent`）。"
            "请安装 Cursor Agent，或把程序员执行器改为 Hermes / Codex。"
        )
    raise RuntimeError(
        "未检测到 Cursor Agent CLI（`agent` / `cursor-agent`）。"
        "请安装 Cursor Agent shell 命令后再试。"
    )


def run_executor_step(
    executor_id: str,
    step_id: str,
    progress: ProgressCb = None,
    *,
    provider_id: str | None = None,
    instance_id: str | None = None,
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
        ("cursor", "open_download"): _open_cursor_download,
        ("cursor", "verify_cli"): _verify_cursor_cli,
    }

    if executor_id == "hermes" and step_id == "configure_api":
        result = _configure_hermes_api(progress, provider_id=provider_id)
    elif executor_id == "codex" and step_id == "sync_api":
        result = _configure_codex_api(
            progress,
            provider_id=provider_id,
            instance_id=instance_id,
        )
    else:
        handler = handlers.get((executor_id, step_id))
        if not handler:
            raise RuntimeError(f"未实现: {executor_id}/{step_id}")
        result = handler(progress)

    result["executor"] = executor_id
    result["step"] = step_id
    result["status"] = executor_status(executor_id)
    return result
