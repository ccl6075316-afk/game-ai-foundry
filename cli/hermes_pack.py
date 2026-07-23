"""Hermes Agent / Codex skill packaging for Game AI Foundry."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from roles import (
    GODOT_ASSEMBLER_ROLE,
    GODOT_DEVELOPER_ROLE,
    IMAGE_GENERATOR_ROLE,
    ORCHESTRATOR_ROLE,
    PROMPT_CRAFTER_ROLE,
    TESTER_ROLE,
    VIDEO_GENERATOR_ROLE,
)
from skill_loader import ROLE_SKILLS, load_role_skill, skills_root

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLI_DIR = _REPO_ROOT / "cli"
_HERMES_SOURCE = _REPO_ROOT / "resources" / "hermes"


def hermes_home() -> Path:
    """Directory Hermes actually uses ($HERMES_HOME, else ~/.hermes)."""
    env = os.environ.get("HERMES_HOME") or os.environ.get("HERMES_AGENT_HOME")
    if env and str(env).strip():
        return Path(env).expanduser().resolve()
    return (Path.home() / ".hermes").resolve()


DEFAULT_HERMES_SKILLS_DIR = hermes_home() / "skills"

HERMES_PACKAGES: dict[str, dict[str, Any]] = {
    "game-factory-orchestrator": {
        "role": ORCHESTRATOR_ROLE,
        "description": "Orchestrate Game AI Foundry: brief → seven agents → gamefactory CLI.",
        "tags": ["Game-Dev", "Assets", "Pipeline", "Orchestrator", "Godot"],
        "related": [
            "game-factory-prompt-crafter",
            "game-factory-image-generator",
            "game-factory-video-generator",
            "game-factory-godot-assembler",
            "game-factory-godot-developer",
            "game-factory-tester",
        ],
    },
    "game-factory-prompt-crafter": {
        "role": PROMPT_CRAFTER_ROLE,
        "description": "Write image/video prompts and handoff JSON for Game AI Foundry.",
        "tags": ["Game-Dev", "Prompts", "LLM"],
        "related": ["game-factory-orchestrator", "game-factory-image-generator"],
    },
    "game-factory-image-generator": {
        "role": IMAGE_GENERATOR_ROLE,
        "description": "Call OpenRouter image API via gamefactory (plan-file only).",
        "tags": ["Game-Dev", "Image-Gen", "OpenRouter"],
        "related": ["game-factory-prompt-crafter", "game-factory-orchestrator"],
    },
    "game-factory-video-generator": {
        "role": VIDEO_GENERATOR_ROLE,
        "description": "Call Seedance video API via gamefactory (plan-file + raw reference still).",
        "tags": ["Game-Dev", "Video", "Seedance", "Animation"],
        "related": ["game-factory-orchestrator", "game-factory-prompt-crafter", "game-factory-godot-assembler"],
    },
    "game-factory-godot-assembler": {
        "role": GODOT_ASSEMBLER_ROLE,
        "description": "Assemble Godot 4 .NET projects from PNG/SpriteFrames (assemble handoff).",
        "tags": ["Game-Dev", "Godot", "CSharp", "Assembly"],
        "related": ["game-factory-orchestrator", "game-factory-video-generator", "game-factory-godot-developer"],
    },
    "game-factory-godot-developer": {
        "role": GODOT_DEVELOPER_ROLE,
        "description": "Implement Godot 4 C# game logic from product brief + dev handoff.",
        "tags": ["Game-Dev", "Godot", "CSharp", "Codex"],
        "related": ["game-factory-orchestrator", "game-factory-godot-assembler", "game-factory-codex"],
    },
    "game-factory-tester": {
        "role": TESTER_ROLE,
        "description": "Autonomous playtest: godot validate, headless screenshot, vision QA report.",
        "tags": ["Game-Dev", "QA", "Testing", "Vision"],
        "related": ["game-factory-orchestrator", "game-factory-godot-developer"],
    },
    "game-factory-codex": {
        "role": None,
        "description": "Run gamefactory CLI from Hermes terminal or delegate to Codex exec.",
        "tags": ["Game-Dev", "Codex", "Terminal", "Hermes"],
        "related": [
            "game-factory-orchestrator",
            "codex",
        ],
        "extra_skill": "codex-delegate.md",
    },
}


# Portable tokens written into resources/hermes (safe to ship in Release).
# `hermes install` rewrites them to this machine's absolute paths under ~/.hermes only.
_PLACEHOLDER_ROOT = "<GAMEFACTORY_ROOT>"
_PLACEHOLDER_CLI = "<GAMEFACTORY_ROOT>/cli"


def repo_root() -> Path:
    return _REPO_ROOT


def cli_dir() -> Path:
    return _CLI_DIR


def hermes_source_dir() -> Path:
    return _HERMES_SOURCE


def resolve_hermes_install_dir(target: Path | None = None) -> Path:
    if target is not None:
        return target.expanduser().resolve()
    env = os.environ.get("HERMES_SKILLS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return hermes_home() / "skills"


def _frontmatter(pkg_name: str, meta: dict[str, Any]) -> str:
    tags = meta.get("tags", [])
    related = meta.get("related", [])
    return "\n".join(
        [
            "---",
            f"name: {pkg_name}",
            f'description: "{meta["description"]}"',
            "version: 1.0.0",
            "author: Game AI Foundry",
            "license: MIT",
            "platforms: [linux, macos, windows]",
            "metadata:",
            "  hermes:",
            f"    tags: [{', '.join(tags)}]",
            f"    related_skills: [{', '.join(related)}]",
            "---",
            "",
        ]
    )


def _terminal_section() -> str:
    """Portable terminal instructions — no machine-specific absolute paths."""
    root = _PLACEHOLDER_ROOT
    cli = _PLACEHOLDER_CLI
    return f"""## Hermes / Codex terminal

Run **all** `gamefactory` commands from the CLI directory. Use `pty=true`.

Resolve `<GAMEFACTORY_ROOT>` on this machine with:

```bash
cd cli && python gamefactory.py hermes paths
```

(`repo_root` / `cli_dir` in that JSON). Or set env `GAMEFACTORY_ROOT` to the Foundry repo/app root.
`hermes install` stamps the real paths into `~/.hermes/skills` for local use; **Release / git sources stay portable.**

```text
terminal(
  command="cd {cli} && python gamefactory.py <subcommand> ...",
  workdir="{root}",
  pty=true,
)
```

Environment (optional):

- `GAMEFACTORY_ROOT={root}`
- Config: `~/.gamefactory/config.json` (see `resources/config.example.json`)
- OpenRouter proxy (if needed): set top-level `proxy` (e.g. local Clash `http://127.0.0.1:7897`); legacy `image.proxy` / `prompt.proxy` still read

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd {cli} && python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4",
  workdir="{root}",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="{root}"`.
"""


def stamp_local_paths(text: str, *, root: Path | None = None, cli: Path | None = None) -> str:
    """Replace portable placeholders with absolute paths for a local Hermes install."""
    root_s = str((root or _REPO_ROOT).resolve())
    cli_s = str((cli or _CLI_DIR).resolve())
    # Order matters: longer token first
    out = text.replace(_PLACEHOLDER_CLI, cli_s)
    out = out.replace(f"{_PLACEHOLDER_ROOT}\\cli", cli_s)
    out = out.replace(_PLACEHOLDER_ROOT, root_s)
    return out


def _stamp_skill_file(skill_path: Path) -> None:
    if not skill_path.is_file():
        return
    original = skill_path.read_text(encoding="utf-8")
    stamped = stamp_local_paths(original)
    if stamped != original:
        skill_path.write_text(stamped, encoding="utf-8")


def _role_body(role: str) -> str:
    parts = [load_role_skill(role, name) for name in ROLE_SKILLS[role]]
    return "\n\n---\n\n".join(parts)


def _extra_body(filename: str) -> str:
    path = skills_root().parent / "hermes" / "_includes" / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing Hermes include: {path}")
    return path.read_text(encoding="utf-8")


def build_skill_markdown(pkg_name: str, meta: dict[str, Any]) -> str:
    role = meta.get("role")
    if role:
        body = _role_body(role)
    else:
        body = _extra_body(str(meta["extra_skill"]))

    title = pkg_name.replace("-", " ").title()
    return (
        _frontmatter(pkg_name, meta)
        + f"# {title}\n\n"
        + body
        + "\n\n---\n\n"
        + _terminal_section()
    )


def sync_hermes_skills(target_dir: Path | None = None) -> list[Path]:
    """Generate SKILL.md packages under resources/hermes/ (source of truth, portable)."""
    out_root = target_dir or _HERMES_SOURCE
    out_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for pkg_name, meta in HERMES_PACKAGES.items():
        pkg_dir = out_root / pkg_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        skill_path = pkg_dir / "SKILL.md"
        skill_path.write_text(
            build_skill_markdown(pkg_name, meta),
            encoding="utf-8",
        )
        written.append(skill_path)

    return written


def install_hermes_skills(
    install_dir: Path | None = None,
    *,
    sync_first: bool = True,
    use_symlink: bool | None = None,
    stamp_paths: bool = True,
) -> dict[str, Any]:
    """Install generated skills into Hermes skills directory.

    Prefer symlink when requested; on Windows (or any OSError such as
    privilege WinError 1314) fall back to copytree so GUI install always works.

    When copying (or when stamp_paths and symlink would point at portable
    source), write machine-local absolute paths into the install copy only —
    never into resources/hermes shipped in Release.
    """
    if sync_first:
        sync_hermes_skills()

    dest_root = resolve_hermes_install_dir(install_dir)
    dest_root.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    used_symlink = False
    # Default: try symlink on non-Windows; Windows often lacks SeCreateSymbolicLinkPrivilege.
    prefer_symlink = (use_symlink is True) or (
        use_symlink is None and sys.platform != "win32"
    )
    # Stamping needs a real copy; writing through a symlink would mutate portable repo source.
    if stamp_paths:
        prefer_symlink = False

    for pkg_name in HERMES_PACKAGES:
        src = _HERMES_SOURCE / pkg_name
        if not src.is_dir():
            raise FileNotFoundError(
                f"Hermes skill package missing: {src}. Run `hermes sync` first."
            )
        dest = dest_root / pkg_name
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            else:
                shutil.rmtree(dest)

        linked = False
        if prefer_symlink:
            try:
                dest.symlink_to(src.resolve(), target_is_directory=True)
                linked = True
                used_symlink = True
            except OSError:
                linked = False
        if not linked:
            shutil.copytree(src, dest)
            if stamp_paths:
                _stamp_skill_file(dest / "SKILL.md")

        installed.append(str(dest))

    return {
        "install_dir": str(dest_root),
        "packages": installed,
        "symlink": used_symlink,
        "stamped_paths": stamp_paths and not used_symlink,
        "source": str(_HERMES_SOURCE),
        "repo_root": str(_REPO_ROOT),
    }


def hermes_paths_info() -> dict[str, str]:
    home = hermes_home()
    return {
        "repo_root": str(_REPO_ROOT),
        "cli_dir": str(_CLI_DIR),
        "hermes_home": str(home),
        "skills_source": str(_HERMES_SOURCE),
        "skills_install_default": str(home / "skills"),
        "config_path": str(Path.home() / ".gamefactory" / "config.json"),
        "hermes_env": str(home / ".env"),
        "hermes_config": str(home / "config.yaml"),
    }


def dump_paths_json() -> str:
    return json.dumps(hermes_paths_info(), indent=2, ensure_ascii=False)
