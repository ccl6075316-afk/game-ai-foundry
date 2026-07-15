"""Startup toolchain checks and auto-install (ffmpeg, godot, dotnet). rembg ships with embedded Python."""

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

from toolchain_paths import (
    BIN_DIR,
    DOTNET_DIR,
    GODOT_DIR,
    TOOLCHAIN_ROOT,
    resolve_dotnet,
    resolve_ffmpeg,
    resolve_godot,
    _find_godot_binary,
)
from ffmpeg_sources import ffmpeg_download_sources, platform_key
from godot_sources import godot_download_source
from dotnet_install import install_dotnet_sdk

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"

ProgressCb = Callable[[str], None] | None

# Godot: portable zip — user downloads manually, then points engine_path in settings.
GODOT_DOWNLOAD_URL = "https://godotengine.org/download"
GODOT_DOWNLOAD_HINT = (
    "Godot 4 **.NET / Mono** 便携版；缺失时可自动下载到 ~/.gamefactory/toolchain/godot。"
)

DOTNET_DOWNLOAD_URL = "https://dotnet.microsoft.com/download"


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
    return resolve_godot(config)


def _dotnet_path(config: dict[str, Any]) -> str | None:
    return resolve_dotnet(config)


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
            "action": "auto",
        },
        {
            "id": "dotnet",
            "label": ".NET SDK",
            "description": "Godot C# 玩法开发需要 .NET SDK；缺失时可自动安装到 ~/.gamefactory/toolchain/dotnet",
            "required": True,
            "action": "auto",
        },
    ]


def _is_available(component_id: str, config: dict[str, Any]) -> bool:
    if component_id == "ffmpeg":
        return bool(resolve_ffmpeg(config))
    if component_id == "godot":
        return bool(_godot_path_from_config(config))
    if component_id == "dotnet":
        return bool(_dotnet_path(config))
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
            entry["path"] = _dotnet_path(config)
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


def _clear_macos_quarantine(path: Path) -> None:
    if sys.platform != "darwin" or not path.exists():
        return
    subprocess.run(["xattr", "-cr", str(path)], check=False, capture_output=True)


def _install_godot(progress: ProgressCb = None) -> dict[str, Any]:
    key = platform_key()
    if key not in ("macos_arm64", "macos_x64", "win64"):
        raise RuntimeError(f"当前平台暂不支持自动安装 Godot: {sys.platform}/{platform.machine()}")

    source = godot_download_source(key)
    if not source:
        raise RuntimeError("无法解析 Godot .NET 下载地址（GitHub API）")

    GODOT_DIR.mkdir(parents=True, exist_ok=True)
    if GODOT_DIR.exists():
        for child in GODOT_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / "godot.zip"
        _emit(progress, f"下载 {source['label']}…")
        _download(source["url"], archive, progress)

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        _emit(progress, "解压 Godot…")
        _extract_archive(archive, extract_dir, "zip")

        _emit(progress, "安装到工具链目录…")
        for item in extract_dir.iterdir():
            dest = GODOT_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    godot_bin = _find_godot_binary(GODOT_DIR)
    if not godot_bin:
        raise RuntimeError("Godot 解压完成但未找到可执行文件")

    if sys.platform == "darwin":
        app_root = godot_bin
        while app_root.suffix != ".app" and app_root.parent != app_root:
            if app_root.suffix == ".app":
                break
            app_root = app_root.parent
        if app_root.suffix == ".app":
            _clear_macos_quarantine(app_root)
        _clear_macos_quarantine(godot_bin)
    elif sys.platform == "win32":
        godot_bin.chmod(0o755)

    engine_path = str(godot_bin.resolve())
    _save_config(
        {
            "godot": {"engine_path": engine_path},
            "toolchain": {"godot_dir": str(GODOT_DIR), "godot_version": source.get("tag")},
        }
    )
    return {
        "ok": True,
        "id": "godot",
        "source": source["label"],
        "engine_path": engine_path,
        "godot_dir": str(GODOT_DIR),
    }


def _install_dotnet(progress: ProgressCb = None) -> dict[str, Any]:
    if platform_key() not in ("macos_arm64", "macos_x64", "win64"):
        raise RuntimeError(f"当前平台暂不支持自动安装 .NET SDK: {sys.platform}/{platform.machine()}")

    dotnet_bin = install_dotnet_sdk(DOTNET_DIR, progress=progress)
    _save_config({"toolchain": {"dotnet_dir": str(DOTNET_DIR)}})
    return {
        "ok": True,
        "id": "dotnet",
        "dotnet": str(dotnet_bin),
        "dotnet_dir": str(DOTNET_DIR),
    }


def ensure_components(component_ids: list[str] | None = None, progress: ProgressCb = None) -> dict[str, Any]:
    """Detect missing toolchain pieces and auto-install those with action=auto."""
    config = _load_config()
    report = check_toolchain(config)
    auto_ids = {c["id"] for c in report["components"] if c["action"] == "auto"}
    wanted = [cid for cid in (component_ids or sorted(auto_ids)) if cid in auto_ids]
    installed: list[str] = []
    skipped: list[str] = []
    errors: dict[str, str] = {}

    for cid in wanted:
        if _is_available(cid, _load_config()):
            skipped.append(cid)
            continue
        try:
            install_component(cid, progress=progress)
            installed.append(cid)
        except Exception as exc:
            errors[cid] = str(exc)

    return {
        "ok": not errors,
        "installed": installed,
        "skipped": skipped,
        "errors": errors,
        "report": check_toolchain(_load_config()),
    }


def install_component(component_id: str, progress: ProgressCb = None) -> dict[str, Any]:
    if component_id == "ffmpeg":
        return _install_ffmpeg(progress)
    if component_id == "godot":
        return _install_godot(progress)
    if component_id == "dotnet":
        return _install_dotnet(progress)
    raise RuntimeError(f"未知组件: {component_id}")
