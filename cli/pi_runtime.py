"""Resolve and invoke the embedded Pi coding-agent CLI (subprocess)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Pinned by scripts/prepare_embedded_pi.mjs — keep in sync.
PI_PACKAGE = "@earendil-works/pi-coding-agent"
PI_PIN_VERSION = "0.80.10"
# Match @earendil-works/pi-coding-agent engines.node (undici needs modern Node).
PI_MIN_NODE = (22, 19, 0)
PI_MIN_NODE_LABEL = "22.19.0"

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_RUNTIME = _REPO_ROOT / "gui" / "runtime" / "pi"
_ENTRY_REL = Path("node_modules") / "@earendil-works" / "pi-coding-agent" / "dist" / "cli.js"


def _key_usable(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and "YOUR_" not in text.upper()


def parse_node_version(text: str) -> tuple[int, int, int] | None:
    """Parse ``v22.19.0`` / ``22.19.0`` into a version tuple."""
    raw = (text or "").strip().lstrip("vV")
    if not raw:
        return None
    parts = raw.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int("".join(ch for ch in (parts[2] if len(parts) > 2 else "0") if ch.isdigit()) or "0")
    except (TypeError, ValueError):
        return None
    return major, minor, patch


def probe_node_version(exe: str, extra_env: dict[str, str] | None = None) -> tuple[int, int, int] | None:
    """Return Node version for ``exe``, or None if unusable."""
    if not exe or not Path(exe).exists():
        return None
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(
            [exe, "-p", "process.versions.node"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return parse_node_version((proc.stdout or "").strip().splitlines()[0] if proc.stdout else "")


def format_node_version(ver: tuple[int, int, int] | None) -> str | None:
    if not ver:
        return None
    return f"{ver[0]}.{ver[1]}.{ver[2]}"


def node_meets_pi_min(ver: tuple[int, int, int] | None) -> bool:
    return bool(ver and ver >= PI_MIN_NODE)


def resolve_pi_runtime_root() -> Path | None:
    """Dev: gui/runtime/pi; Release workspace may mirror under resources/pi later."""
    env = (os.environ.get("GAMEFACTORY_PI_ROOT") or "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / _ENTRY_REL).is_file():
            return p
    if (_DEFAULT_RUNTIME / _ENTRY_REL).is_file():
        return _DEFAULT_RUNTIME.resolve()
    # Packaged GUI may copy to resources/pi next to python/
    packaged = Path(sys.executable).resolve().parent
    for cand in (
        packaged / "pi",
        packaged.parent / "pi",
        _REPO_ROOT / "gui" / "resources" / "pi",
    ):
        if (cand / _ENTRY_REL).is_file():
            return cand.resolve()
    return None


def resolve_pi_cli_js(root: Path | None = None) -> Path | None:
    base = root or resolve_pi_runtime_root()
    if not base:
        return None
    entry = base / _ENTRY_REL
    return entry if entry.is_file() else None


def _discover_extra_node_bins() -> list[str]:
    """Find Node installs Electron GUI PATH often misses (nvm / Homebrew)."""
    found: list[str] = []
    home = Path.home()
    nvm_root = Path(os.environ.get("NVM_DIR") or (home / ".nvm")).expanduser()
    versions_dir = nvm_root / "versions" / "node"
    if versions_dir.is_dir():
        try:
            # Prefer newest version directory name (v22.19.0 > v20…).
            names = sorted(
                (p.name for p in versions_dir.iterdir() if p.is_dir()),
                key=lambda n: parse_node_version(n) or (0, 0, 0),
                reverse=True,
            )
        except OSError:
            names = []
        for name in names:
            cand = versions_dir / name / "bin" / "node"
            if cand.is_file():
                found.append(str(cand))
                break  # newest is enough; version gate decides later
    for cand in (
        "/opt/homebrew/opt/node@22/bin/node",
        "/usr/local/opt/node@22/bin/node",
        "/opt/homebrew/bin/node",
        "/usr/local/bin/node",
    ):
        if Path(cand).is_file():
            found.append(cand)
    return found


def _node_candidates() -> list[tuple[str, dict[str, str], str]]:
    """Ordered Node launch candidates: ``(exe, extra_env, source)``."""
    out: list[tuple[str, dict[str, str], str]] = []
    seen: set[str] = set()

    def add(exe: str | None, extra: dict[str, str], source: str) -> None:
        if not exe:
            return
        try:
            key = str(Path(exe).resolve())
        except OSError:
            key = exe
        if key in seen or not Path(exe).exists():
            return
        seen.add(key)
        out.append((exe, dict(extra), source))

    # Explicit override first, then PATH node, then nvm/brew, then Electron-as-Node.
    # Electron 33 ships Node 20 — too old for Pi 0.80 — so PATH/nvm Node 22+ must win.
    add((os.environ.get("GAMEFACTORY_NODE") or "").strip() or None, {}, "GAMEFACTORY_NODE")
    add(shutil.which("node"), {}, "PATH")
    for extra_bin in _discover_extra_node_bins():
        add(extra_bin, {}, "discover")
    electron = (os.environ.get("GAMEFACTORY_ELECTRON_EXECUTABLE") or "").strip()
    if electron:
        add(electron, {"ELECTRON_RUN_AS_NODE": "1"}, "electron")
    return out


def resolve_node_launch() -> tuple[str | None, dict[str, str]]:
    """Return ``(executable, extra_env)`` for running Pi's cli.js.

    Prefer a Node that satisfies ``PI_MIN_NODE`` (``GAMEFACTORY_NODE`` → PATH
    ``node`` → Electron ``GAMEFACTORY_ELECTRON_EXECUTABLE``). If none qualify,
    return the first existing candidate so status can report the too-old version.
    """
    fallback: tuple[str, dict[str, str]] | None = None
    for exe, extra, _source in _node_candidates():
        if fallback is None:
            fallback = (exe, extra)
        if node_meets_pi_min(probe_node_version(exe, extra)):
            return exe, extra
    if fallback:
        return fallback
    return None, {}


def resolve_node_bin() -> str | None:
    exe, _ = resolve_node_launch()
    return exe


def load_embed_manifest(root: Path | None = None) -> dict[str, Any] | None:
    base = root or resolve_pi_runtime_root()
    if not base:
        return None
    path = base / "embed-manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def resolve_pi_api_auth(
    config: dict[str, Any] | None = None,
    *,
    role_kind: str = "brief",
    instance_id: str | None = None,
) -> dict[str, Any]:
    """Pick provider + api key for Pi via instance → role → host chain."""
    from agent_auth_resolve import resolve_agent_auth
    from gamefactory import load_config  # local import avoids cycles at module load

    cfg = config if config is not None else load_config()
    resolved = resolve_agent_auth(cfg, role_kind=role_kind, instance_id=instance_id)
    return {
        "provider": resolved.get("provider"),
        "model": resolved.get("model"),
        "api_key": resolved.get("api_key"),
        "env_key": resolved.get("env_key"),
        "api_base": resolved.get("api_base"),
        "source": resolved.get("source"),
        "error": resolved.get("error"),
    }


def pi_status(
    *,
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
) -> dict[str, Any]:
    root = resolve_pi_runtime_root()
    entry = resolve_pi_cli_js(root) if root else None
    node_exe, node_extra = resolve_node_launch()
    node_ver = probe_node_version(node_exe, node_extra) if node_exe else None
    node_ok = node_meets_pi_min(node_ver)
    manifest = load_embed_manifest(root)
    auth = resolve_pi_api_auth(config, instance_id=instance_id)
    size_mb = None
    if manifest and isinstance(manifest.get("size_bytes"), int):
        size_mb = round(manifest["size_bytes"] / (1024 * 1024), 1)

    ready = bool(entry and node_exe and node_ok and auth.get("api_key"))
    if ready:
        hint = None
    elif not entry:
        hint = "运行: node scripts/prepare_embedded_pi.mjs"
    elif not node_exe:
        hint = f"需要 Node >={PI_MIN_NODE_LABEL}（PATH 中的 node，或设置 GAMEFACTORY_NODE）"
    elif not node_ok:
        got = format_node_version(node_ver) or "?"
        hint = (
            f"Node {got} 过旧：内置 Pi {PI_PIN_VERSION} 需要 >={PI_MIN_NODE_LABEL}。"
            f"请安装 Node {PI_MIN_NODE_LABEL}+，或设置 GAMEFACTORY_NODE 指向该版本"
            "（勿仅依赖 Electron 自带的 Node 20）"
        )
    else:
        hint = auth.get("error")

    return {
        "ok": ready,
        "ready": ready,
        "package": PI_PACKAGE,
        "pin_version": PI_PIN_VERSION,
        "min_node": PI_MIN_NODE_LABEL,
        "runtime_root": str(root) if root else None,
        "cli_js": str(entry) if entry else None,
        "node": node_exe,
        "node_version": format_node_version(node_ver),
        "node_ok": node_ok,
        "manifest": manifest,
        "size_mb": size_mb,
        "auth": {
            "provider": auth.get("provider"),
            "model": auth.get("model"),
            "has_api_key": bool(auth.get("api_key")),
            "source": auth.get("source"),
            "error": auth.get("error"),
        },
        "hint": hint,
    }


def run_pi_smoke(
    *,
    prompt: str = "Reply with exactly the three characters: PONG",
    timeout_sec: float = 90.0,
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
) -> dict[str, Any]:
    """One non-interactive, no-tool, no-session Pi turn (Spike 0)."""
    status = pi_status(config=config, instance_id=instance_id)
    if not status.get("cli_js"):
        return {"ok": False, "error": status.get("hint") or "embedded Pi not found", "status": status}
    if not status.get("node"):
        return {"ok": False, "error": "node binary not found on PATH", "status": status}
    if not status.get("node_ok"):
        return {"ok": False, "error": status.get("hint") or "Node too old for Pi", "status": status}

    auth = resolve_pi_api_auth(config, instance_id=instance_id)
    if not auth.get("api_key"):
        return {"ok": False, "error": auth.get("error") or "missing api key", "status": status}

    env = _pi_subprocess_env(auth, config)
    node_exe, _ = resolve_node_launch()
    if not node_exe:
        return {"ok": False, "error": "node binary not found on PATH", "status": status}

    cmd = [
        str(node_exe),
        str(status["cli_js"]),
        "-p",
        "--offline",
        "--no-tools",
        "--no-session",
        "--mode",
        "text",
        "--provider",
        str(auth["provider"]),
        "--model",
        str(auth["model"]),
        # API key via env only — never argv (TimeoutExpired / process lists leak keys).
        prompt,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            env=env,
            cwd=str(Path(status["runtime_root"])),
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": f"pi smoke timed out after {timeout_sec}s",
            "stdout": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
            "provider": auth["provider"],
            "model": auth["model"],
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc), "provider": auth["provider"], "model": auth["model"]}

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    text_l = stdout.lower()
    ok = proc.returncode == 0 and ("pong" in text_l or len(stdout) > 0)
    # Prefer explicit PONG when model cooperates; still pass if CLI returned text + 0
    if proc.returncode == 0 and "pong" not in text_l and stdout:
        ok = True

    return {
        "ok": ok and proc.returncode == 0,
        "exit_code": proc.returncode,
        "provider": auth["provider"],
        "model": auth["model"],
        "stdout": stdout[-4000:],
        "stderr": stderr[-2000:],
        "saw_pong": "pong" in text_l,
        "error": None if proc.returncode == 0 else (stderr or stdout or f"exit {proc.returncode}"),
    }


class PiRuntimeError(RuntimeError):
    """Embedded Pi invocation failed."""


def resolve_brief_executor(config: dict[str, Any] | None = None) -> str:
    """Which backend runs 策划 turns: ``pi`` (embedded) or ``host`` (OpenAI-compat).

    Order: ``GAMEFACTORY_BRIEF_EXECUTOR`` → ``agents.brief.executor`` → auto
    (Pi when embedded+key ready, else host).
    Env ``pi`` still requires embed ready — otherwise fall back to host.
    """
    env = (os.environ.get("GAMEFACTORY_BRIEF_EXECUTOR") or "").strip().lower()
    from gamefactory import load_config

    cfg = config if config is not None else load_config()
    if env == "host":
        return "host"
    if env == "pi":
        return "pi" if pi_status(config=cfg).get("ready") else "host"

    agents = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    brief = agents.get("brief") if isinstance(agents.get("brief"), dict) else {}
    configured = str(brief.get("executor") or "").strip().lower()
    if configured in ("pi", "host"):
        if configured == "pi" and not pi_status(config=cfg).get("ready"):
            return "host"
        return configured

    if pi_status(config=cfg).get("ready"):
        return "pi"
    return "host"


def resolve_pi_auth_for_brief(
    config: dict[str, Any] | None = None,
    *,
    instance_id: str | None = None,
) -> dict[str, Any]:
    """Auth for brief turns: Pi providers + prefer host.model when set."""
    from gamefactory import load_config
    from llm_config import resolve_host_api_settings

    cfg = config if config is not None else load_config()
    auth = resolve_pi_api_auth(cfg, role_kind="brief", instance_id=instance_id)
    host_cfg = cfg.get("host") if isinstance(cfg.get("host"), dict) else {}
    host_model = str(host_cfg.get("model") or "").strip()
    if auth.get("api_key") and host_model and auth.get("source") not in ("instance", "role"):
        auth = {**auth, "model": host_model}
        return auth

    if auth.get("api_key"):
        return auth

    # Last resort: host flat key with provider hint
    api = resolve_host_api_settings(cfg)
    if not api.get("api_key"):
        return auth
    provider = str(host_cfg.get("provider") or "openrouter").strip().lower()
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    if provider not in env_map:
        provider = "openrouter"
    return {
        "provider": provider,
        "model": host_model or str(api.get("model") or "openai/gpt-4o-mini"),
        "api_key": str(api["api_key"]).strip(),
        "env_key": env_map[provider],
        "source": "host.fallback",
    }


def _pi_subprocess_env(auth: dict[str, Any], config: dict[str, Any] | None) -> dict[str, str]:
    env = os.environ.copy()
    env[str(auth["env_key"])] = str(auth["api_key"])
    env["PI_TELEMETRY"] = "0"
    env["PI_OFFLINE"] = "1"
    env["CI"] = "1"
    _, node_extra = resolve_node_launch()
    env.update(node_extra)
    try:
        from gamefactory import load_config
        from proxy_utils import resolve_config_proxy

        proxy = resolve_config_proxy(config if config is not None else load_config())
    except Exception:
        proxy = None
    if proxy:
        env["HTTP_PROXY"] = proxy
        env["HTTPS_PROXY"] = proxy
        env["http_proxy"] = proxy
        env["https_proxy"] = proxy
    return env


def run_pi_text_completion(
    *,
    system_prompt: str,
    user_text: str,
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
    timeout_sec: float = 180.0,
    response_mode: str = "json",
) -> str:
    """One-shot Pi ``-p`` completion (no built-in tools).

    ``response_mode``: ``json`` (brief) or ``text`` (IT / free-form).
    Long system/user bodies go through temp files to stay under Windows argv limits.
    """
    import tempfile

    status = pi_status(config=config, instance_id=instance_id)
    if not status.get("cli_js") or not status.get("node") or not status.get("node_ok"):
        raise PiRuntimeError(status.get("hint") or "embedded Pi not ready")

    auth = resolve_pi_auth_for_brief(config, instance_id=instance_id)
    if not auth.get("api_key"):
        raise PiRuntimeError(auth.get("error") or "missing API key for Pi brief turn")

    env = _pi_subprocess_env(auth, config)
    runtime = Path(str(status["runtime_root"]))
    node_exe, _ = resolve_node_launch()
    if not node_exe:
        raise PiRuntimeError("node binary not found")
    tmp_dir = runtime / "_brief_turns"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if response_mode == "json":
        short_system = (
            "You are the Game AI Foundry brief assistant. "
            "Respond with ONLY valid JSON. No markdown fences."
        )
        closing = "Return the JSON object now."
    else:
        short_system = (
            "You are a Game AI Foundry colleague. Follow the system prompt. "
            "Reply in Chinese unless asked otherwise."
        )
        closing = "Respond to the user now."

    with tempfile.TemporaryDirectory(dir=str(tmp_dir)) as td:
        tdp = Path(td)
        sys_path = tdp / "system.md"
        user_path = tdp / "user.txt"
        sys_path.write_text(system_prompt, encoding="utf-8")
        user_path.write_text(user_text, encoding="utf-8")

        cmd = [
            str(node_exe),
            str(status["cli_js"]),
            "-p",
            "--offline",
            "--no-tools",
            "--no-session",
            "--mode",
            "text",
            "--provider",
            str(auth["provider"]),
            "--model",
            str(auth["model"]),
            "--system-prompt",
            short_system,
            "--append-system-prompt",
            str(sys_path),
            f"@{user_path}",
            closing,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
                env=env,
                cwd=str(runtime),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            raise PiRuntimeError(f"Pi brief turn timed out after {timeout_sec}s") from exc
        except OSError as exc:
            raise PiRuntimeError(str(exc)) from exc

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise PiRuntimeError(err[-2000:] or f"pi exited {proc.returncode}")

    text = (proc.stdout or "").strip()
    if not text:
        raise PiRuntimeError("Pi returned empty stdout")
    return text


def run_pi_agent_turn(
    *,
    system_prompt: str,
    user_text: str,
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
    max_tool_rounds: int = 4,
    timeout_sec: float = 180.0,
    tool_profile: str = "it",
    allow_export: bool = False,
) -> dict[str, Any]:
    """Pi turn with Foundry tool-fence loop (for IT / optional agent roles)."""
    from pi_foundry_tools import run_tool_round, tool_protocol_instructions

    system = f"{system_prompt.rstrip()}\n\n{tool_protocol_instructions(profile=tool_profile)}"
    conversation = user_text
    tool_trace: list[dict[str, Any]] = []
    final_text = ""

    for _ in range(max(1, max_tool_rounds + 1)):
        raw = run_pi_text_completion(
            system_prompt=system,
            user_text=conversation,
            config=config,
            instance_id=instance_id,
            timeout_sec=timeout_sec,
            response_mode="text" if tool_profile != "brief" else "json",
        )
        results, visible = run_tool_round(
            raw, allow_export=allow_export, profile=tool_profile
        )
        final_text = visible or raw
        if not results:
            break
        tool_trace.extend(results)
        if tool_profile == "brief":
            conversation = (
                f"{user_text}\n\n## Tool results (JSON)\n"
                f"{json.dumps(results, ensure_ascii=False, indent=2)}\n\n"
                "Continue. If you need another allow-listed tool, emit FOUNDRY_TOOL; "
                "otherwise respond with ONLY the skill JSON object (no markdown)."
            )
        else:
            conversation = (
                f"{user_text}\n\n## Previous assistant output\n{visible}\n\n"
                f"## Tool results (JSON)\n{json.dumps(results, ensure_ascii=False, indent=2)}\n\n"
                "Continue. If you need another allow-listed command, emit FOUNDRY_TOOL again; "
                "otherwise answer the user in Chinese without a tool fence."
            )

    return {
        "ok": True,
        "assistant_message": final_text.strip(),
        "tool_trace": tool_trace,
        "tool_rounds": len(tool_trace),
    }


def run_pi_brief_turn_with_tools(
    *,
    system_prompt: str,
    user_text: str,
    session_id: str,
    config: dict[str, Any] | None = None,
    instance_id: str | None = None,
    allow_export: bool = False,
    max_tool_rounds: int = 3,
    timeout_sec: float = 240.0,
) -> str:
    """Brief Pi turn: optional FOUNDRY_TOOL loop, final text must be skill JSON."""
    hint = (
        f"\n\nCurrent host-chat session_id is `{session_id}`. "
        "Use this exact id in brief chat status/export tools.\n"
    )
    if allow_export:
        hint += "Export is **allowed** this turn if the user asked to 落实/导出 and draft is ready.\n"
    else:
        hint += "Export is **forbidden** this turn — do not emit brief chat export.\n"

    result = run_pi_agent_turn(
        system_prompt=system_prompt + hint,
        user_text=user_text,
        config=config,
        instance_id=instance_id,
        max_tool_rounds=max_tool_rounds,
        timeout_sec=timeout_sec,
        tool_profile="brief",
        allow_export=allow_export,
    )
    text = str(result.get("assistant_message") or "").strip()
    if not text:
        raise PiRuntimeError("Pi brief turn returned empty text")
    return text
