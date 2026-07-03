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

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"

ProgressCb = Callable[[str], None] | None

# Godot: portable zip — user downloads manually, then points engine_path in settings.
GODOT_DOWNLOAD_URL = "https://godotengine.org/download"
GODOT_DOWNLOAD_HINT = (
    "下载 Godot 4 **.NET / Mono** 版（zip 解压即用，无需安装）。"
    " macOS 选 .app 内可执行文件或 *_console 二进制；Windows 选 *_console.exe。"
)

DOTNET_DOWNLOAD_URL = "https://dotnet.microsoft.com/download"

_FFMPEG_RELEASE = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"


def _platform_key() -> str:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        if machine in ("arm64", "aarch64"):
            return "macos_arm64"
        return "macos_x64"
    if sys.platform == "win32":
        return "win64"
    return "linux64"


_FFMPEG_ARTIFACTS: dict[str, tuple[str, str]] = {
    "macos_arm64": (f"{_FFMPEG_RELEASE}/ffmpeg-master-latest-macosaarch64-gpl.zip", "zip"),
    "macos_x64": (f"{_FFMPEG_RELEASE}/ffmpeg-master-latest-macos64-gpl.zip", "zip"),
    "win64": (f"{_FFMPEG_RELEASE}/ffmpeg-master-latest-win64-gpl.zip", "zip"),
    "linux64": (f"{_FFMPEG_RELEASE}/ffmpeg-master-latest-linux64-gpl.tar.xz", "tar.xz"),
}


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


def _install_ffmpeg(progress: ProgressCb = None) -> dict[str, Any]:
    key = _platform_key()
    artifact = _FFMPEG_ARTIFACTS.get(key)
    if not artifact:
        raise RuntimeError(f"当前平台暂不支持自动安装 FFmpeg: {sys.platform}/{platform.machine()}")

    url, kind = artifact
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / f"ffmpeg.{kind}"
        _download(url, archive, progress)

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        _emit(progress, "解压 FFmpeg…")
        if kind == "zip":
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(archive, "r:xz") as tf:
                tf.extractall(extract_dir)

        ffmpeg_src, ffprobe_src = _find_ffmpeg_bins(extract_dir)
        if not ffmpeg_src:
            raise RuntimeError("解压包中未找到 ffmpeg 可执行文件")

        ffmpeg_dst = BIN_DIR / ffmpeg_src.name
        shutil.copy2(ffmpeg_src, ffmpeg_dst)
        if sys.platform != "win32":
            ffmpeg_dst.chmod(0o755)

        ffprobe_dst: Path | None = None
        if ffprobe_src:
            ffprobe_dst = BIN_DIR / ffprobe_src.name
            shutil.copy2(ffprobe_src, ffprobe_dst)
            if sys.platform != "win32":
                ffprobe_dst.chmod(0o755)

    _save_config({"toolchain": {"bin_dir": str(BIN_DIR)}})
    return {
        "ok": True,
        "id": "ffmpeg",
        "ffmpeg": str(ffmpeg_dst),
        "ffprobe": str(ffprobe_dst) if ffprobe_dst else None,
        "bin_dir": str(BIN_DIR),
    }


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


def install_component(component_id: str, progress: ProgressCb = None) -> dict[str, Any]:
    if component_id == "ffmpeg":
        return _install_ffmpeg(progress)
    if component_id == "rembg":
        return _install_rembg(progress)
    if component_id in ("godot", "dotnet"):
        spec = next(s for s in _component_specs() if s["id"] == component_id)
        raise RuntimeError(
            f"{spec['label']} 需手动下载安装，请打开 {spec.get('download_url', '')}"
        )
    raise RuntimeError(f"未知组件: {component_id}")
