"""Startup toolchain checks and optional auto-install (ffmpeg, rembg)."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable

from toolchain_paths import BIN_DIR, TOOLCHAIN_ROOT, resolve_binary, resolve_ffmpeg
from ffmpeg_sources import ffmpeg_download_sources, platform_key

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"

ProgressCb = Callable[[str], None] | None

# Godot: portable zip — user downloads manually, then points engine_path in settings.
GODOT_DOWNLOAD_URL = "https://godotengine.org/download"
GODOT_DOWNLOAD_HINT = (
    "下载 Godot 4 **.NET / Mono** 版（zip 解压即用，无需安装）。"
    " macOS 选 .app 内可执行文件或 *_console 二进制；Windows 选 *_console.exe。"
)

DOTNET_DOWNLOAD_URL = "https://dotnet.microsoft.com/download"

HERMES_INSTALL_URL = "https://github.com/NousResearch/hermes-agent"
CODEX_INSTALL_URL = "https://github.com/openai/codex"
CURSOR_INSTALL_URL = "https://cursor.com"


def _load_config() -> dict[str, Any]:
    if not _CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(patch: dict[str, Any]) -> None:
    cfg = _load_config()
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            cfg[key] = {**cfg[key], **value}
        else:
            cfg[key] = value
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _godot_path_from_config(config: dict[str, Any]) -> str | None:
    godot_cfg = config.get("godot", {}) if isinstance(config.get("godot"), dict) else {}
    path = godot_cfg.get("engine_path")
    if path and Path(path).exists():
        return str(path)
    return None


def _rembg_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("rembg") is not None
    except (ImportError, ValueError):
        return False


def _executor_cli(name: str) -> bool:
    return bool(shutil.which(name))


def _hermes_skills_installed() -> bool:
    from hermes_pack import resolve_hermes_install_dir, HERMES_PACKAGES

    install_dir = resolve_hermes_install_dir()
    for pkg, meta in HERMES_PACKAGES.items():
        if not meta.get("role"):
            continue
        if not (install_dir / pkg / "SKILL.md").is_file() and not (install_dir / pkg).exists():
            return False
    return True


def _component_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "ffmpeg",
            "label": "FFmpeg",
            "description": "视频拆帧、剪辑与探针（ffprobe）",
            "required": True,
            "action": "auto",
        },
        {
            "id": "godot",
            "label": "Godot .NET",
            "description": GODOT_DOWNLOAD_HINT,
            "required": True,
            "action": "download_link",
            "download_url": GODOT_DOWNLOAD_URL,
        },
        {
            "id": "dotnet",
            "label": ".NET SDK",
            "description": "Godot C# 玩法开发需要本机 .NET SDK",
            "required": False,
            "action": "download_link",
            "download_url": DOTNET_DOWNLOAD_URL,
        },
        {
            "id": "rembg",
            "label": "rembg（AI 抠图）",
            "description": "可选：视频 AI 抠图引擎；静态图仍可用色键",
            "required": False,
            "action": "pip",
        },
        {
            "id": "hermes",
            "label": "Hermes CLI + Skills",
            "description": "独立 AI 助手执行器；LLM 需在 Hermes 自身配置，不会自动读取本应用 API Key",
            "required": False,
            "action": "install_guide",
            "download_url": HERMES_INSTALL_URL,
            "install_cmd": "pip install hermes-agent && cd cli && python gamefactory.py hermes install",
        },
        {
            "id": "codex",
            "label": "Codex CLI",
            "description": "OpenAI 登录式代码执行器；写玩法时用，无需 OpenRouter Key",
            "required": False,
            "action": "install_guide",
            "download_url": CODEX_INSTALL_URL,
            "install_cmd": "npm install -g @openai/codex && codex login",
        },
        {
            "id": "cursor",
            "label": "Cursor CLI",
            "description": "随 Cursor IDE 安装；登录式，GUI 对话仍走上方 LLM Provider",
            "required": False,
            "action": "download_link",
            "download_url": CURSOR_INSTALL_URL,
        },
    ]


def _is_available(component_id: str, config: dict[str, Any]) -> bool:
    if component_id == "ffmpeg":
        return bool(resolve_ffmpeg(config))
    if component_id == "godot":
        return bool(_godot_path_from_config(config))
    if component_id == "dotnet":
        return bool(shutil.which("dotnet"))
    if component_id == "rembg":
        return _rembg_available()
    if component_id == "hermes":
        return _executor_cli("hermes") and _hermes_skills_installed()
    if component_id == "codex":
        return _executor_cli("codex")
    if component_id == "cursor":
        return _executor_cli("cursor")
    return False


def check_toolchain(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or _load_config()
    components: list[dict[str, Any]] = []
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for spec in _component_specs():
        available = _is_available(spec["id"], config)
        entry = {
            **spec,
            "available": available,
            "path": None,
        }
        if spec["id"] == "ffmpeg" and available:
            entry["path"] = resolve_ffmpeg(config)
        elif spec["id"] == "godot" and available:
            entry["path"] = _godot_path_from_config(config)
        elif spec["id"] == "dotnet" and available:
            entry["path"] = shutil.which("dotnet")
        elif spec["id"] in ("hermes", "codex", "cursor") and available:
            entry["path"] = shutil.which(spec["id"])

        components.append(entry)
        if not available:
            bucket = missing_required if spec["required"] else missing_optional
            bucket.append(spec["id"])

    return {
        "toolchain_root": str(TOOLCHAIN_ROOT),
        "bin_dir": str(BIN_DIR),
        "components": components,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "needs_attention": bool(missing_required or missing_optional),
    }


def _emit(progress: ProgressCb, message: str) -> None:
    if progress:
        progress(message)


def _download(url: str, dest: Path, progress: ProgressCb = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _emit(progress, f"下载 {url}")

    def _reporthook(block: int, block_size: int, total: int) -> None:
        if total <= 0 or not progress:
            return
        done = min(block * block_size, total)
        pct = int(done * 100 / total)
        if pct % 10 == 0:
            _emit(progress, f"下载进度 {pct}%")

    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)


def _find_ffmpeg_bins(root: Path) -> tuple[Path | None, Path | None]:
    ffmpeg_bin: Path | None = None
    ffprobe_bin: Path | None = None
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if name in ("ffmpeg", "ffmpeg.exe") and ffmpeg_bin is None:
            ffmpeg_bin = path
        elif name in ("ffprobe", "ffprobe.exe") and ffprobe_bin is None:
            ffprobe_bin = path
        if ffmpeg_bin and ffprobe_bin:
            break
    return ffmpeg_bin, ffprobe_bin


def _extract_archive(archive: Path, extract_dir: Path, kind: str) -> None:
    if kind == "zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract_dir)
    else:
        with tarfile.open(archive, "r:xz") as tf:
            tf.extractall(extract_dir)


def _copy_bin(src: Path, dest: Path) -> None:
    shutil.copy2(src, dest)
    if sys.platform != "win32":
        dest.chmod(0o755)


def _install_ffmpeg(progress: ProgressCb = None) -> dict[str, Any]:
    key = platform_key()
    sources = ffmpeg_download_sources(key)
    if not sources:
        raise RuntimeError(f"当前平台暂不支持自动安装 FFmpeg: {sys.platform}/{platform.machine()}")

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    bundle_sources = [s for s in sources if not s.get("label", "").startswith("evermeet")]
    for src in bundle_sources:
        url = src["url"]
        kind = src["kind"]
        label = src.get("label", url)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                archive = tmp_path / f"bundle.{kind.replace('.', '_')}"
                _emit(progress, f"尝试 {label}…")
                _download(url, archive, progress)

                extract_dir = tmp_path / "extract"
                extract_dir.mkdir()
                _emit(progress, "解压 FFmpeg…")
                _extract_archive(archive, extract_dir, kind)

                ffmpeg_src, ffprobe_src = _find_ffmpeg_bins(extract_dir)
                if not ffmpeg_src:
                    errors.append(f"{label}: 未找到 ffmpeg")
                    continue

                ffmpeg_dst = BIN_DIR / ffmpeg_src.name
                _copy_bin(ffmpeg_src, ffmpeg_dst)

                ffprobe_dst: Path | None = None
                if ffprobe_src:
                    ffprobe_dst = BIN_DIR / ffprobe_src.name
                    _copy_bin(ffprobe_src, ffprobe_dst)

                _save_config({"toolchain": {"bin_dir": str(BIN_DIR)}})
                return {
                    "ok": True,
                    "id": "ffmpeg",
                    "source": label,
                    "ffmpeg": str(ffmpeg_dst),
                    "ffprobe": str(ffprobe_dst) if ffprobe_dst else None,
                    "bin_dir": str(BIN_DIR),
                }
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            _emit(progress, f"{label} 失败，尝试下一源…")

    if key.startswith("macos"):
        try:
            _emit(progress, "尝试 evermeet 单文件包…")
            ffmpeg_dst: Path | None = None
            ffprobe_dst: Path | None = None
            for tool in ("ffmpeg", "ffprobe"):
                url = f"https://evermeet.cx/{tool}/getrelease/zip"
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    archive = tmp_path / f"{tool}.zip"
                    _download(url, archive, progress)
                    extract_dir = tmp_path / "extract"
                    extract_dir.mkdir()
                    _extract_archive(archive, extract_dir, "zip")
                    found, probe = _find_ffmpeg_bins(extract_dir)
                    bin_path = found or probe
                    if not bin_path:
                        single = extract_dir / tool
                        if single.is_file():
                            bin_path = single
                    if not bin_path:
                        errors.append(f"evermeet-{tool}: 未找到二进制")
                        continue
                    dest = BIN_DIR / bin_path.name
                    _copy_bin(bin_path, dest)
                    if tool == "ffmpeg":
                        ffmpeg_dst = dest
                    else:
                        ffprobe_dst = dest

            if ffmpeg_dst:
                _save_config({"toolchain": {"bin_dir": str(BIN_DIR)}})
                return {
                    "ok": True,
                    "id": "ffmpeg",
                    "source": "evermeet",
                    "ffmpeg": str(ffmpeg_dst),
                    "ffprobe": str(ffprobe_dst) if ffprobe_dst else None,
                    "bin_dir": str(BIN_DIR),
                }
        except Exception as exc:
            errors.append(f"evermeet: {exc}")

    detail = "; ".join(errors[-5:]) if errors else "无可用下载源"
    raise RuntimeError(f"FFmpeg 自动安装失败（已尝试 {len(sources)} 个源）: {detail}")


def _install_rembg(progress: ProgressCb = None) -> dict[str, Any]:
    _emit(progress, "pip install rembg[cpu]…")
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "rembg[cpu]"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-500:]
        raise RuntimeError(f"pip install rembg 失败: {tail}")
    return {"ok": True, "id": "rembg"}


def _install_hermes_skills(progress: ProgressCb = None) -> dict[str, Any]:
    _emit(progress, "安装 Hermes skills…")
    from hermes_pack import install_hermes_skills

    written = install_hermes_skills()
    return {"ok": True, "id": "hermes", "skills_installed": len(written)}


def install_component(component_id: str, progress: ProgressCb = None) -> dict[str, Any]:
    if component_id == "ffmpeg":
        return _install_ffmpeg(progress)
    if component_id == "rembg":
        return _install_rembg(progress)
    if component_id == "hermes":
        return _install_hermes_skills(progress)
    if component_id in ("godot", "dotnet", "codex", "cursor"):
        spec = next(s for s in _component_specs() if s["id"] == component_id)
        cmd = spec.get("install_cmd") or spec.get("download_url") or ""
        raise RuntimeError(f"{spec['label']} 需手动安装。{cmd}")
    raise RuntimeError(f"未知组件: {component_id}")
