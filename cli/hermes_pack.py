"""Hermes Agent / Codex skill packaging for Game AI Foundry."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from roles import (
    GODOT_ASSEMBLER_ROLE,
    GODOT_DEVELOPER_ROLE,
    IMAGE_GENERATOR_ROLE,
    ORCHESTRATOR_ROLE,
    PROMPT_CRAFTER_ROLE,
    VIDEO_GENERATOR_ROLE,
)
from skill_loader import ROLE_SKILLS, load_role_skill, skills_root

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLI_DIR = _REPO_ROOT / "cli"
_HERMES_SOURCE = _REPO_ROOT / "resources" / "hermes"

DEFAULT_HERMES_SKILLS_DIR = Path.home() / ".hermes" / "skills"

HERMES_PACKAGES: dict[str, dict[str, Any]] = {
    "game-factory-orchestrator": {
        "role": ORCHESTRATOR_ROLE,
        "description": "Orchestrate Game AI Foundry: brief → six agents → gamefactory CLI.",
        "tags": ["Game-Dev", "Assets", "Pipeline", "Orchestrator", "Godot"],
        "related": [
            "game-factory-prompt-crafter",
            "game-factory-image-generator",
            "game-factory-video-generator",
            "game-factory-godot-assembler",
            "game-factory-godot-developer",
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
    return DEFAULT_HERMES_SKILLS_DIR


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
    root = _REPO_ROOT
    cli = _CLI_DIR
    return f"""## Hermes / Codex terminal

Run **all** `gamefactory` commands from the CLI directory. Use `pty=true`.

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
- OpenRouter proxy (macOS Clash): `http://127.0.0.1:7897` in config `image.proxy` / `prompt.proxy`

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd {cli} && python gamefactory.py prompt craft --brief ../resources/test-brief-dino.json --asset raptor_scavenger -o ../plans/raptor.json",
  workdir="{root}",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="{root}"`.
"""


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
    """Generate SKILL.md packages under resources/hermes/ (source of truth)."""
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
    use_symlink: bool = True,
) -> dict[str, Any]:
    """Install generated skills into Hermes skills directory."""
    if sync_first:
        sync_hermes_skills()

    dest_root = resolve_hermes_install_dir(install_dir)
    dest_root.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []

    for pkg_name in HERMES_PACKAGES:
        src = _HERMES_SOURCE / pkg_name
        dest = dest_root / pkg_name
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            else:
                shutil.rmtree(dest)

        if use_symlink:
            dest.symlink_to(src.resolve(), target_is_directory=True)
        else:
            shutil.copytree(src, dest)

        installed.append(str(dest))

    return {
        "install_dir": str(dest_root),
        "packages": installed,
        "symlink": use_symlink,
        "source": str(_HERMES_SOURCE),
    }


def hermes_paths_info() -> dict[str, str]:
    return {
        "repo_root": str(_REPO_ROOT),
        "cli_dir": str(_CLI_DIR),
        "skills_source": str(_HERMES_SOURCE),
        "skills_install_default": str(DEFAULT_HERMES_SKILLS_DIR),
        "config_path": str(Path.home() / ".gamefactory" / "config.json"),
    }


def dump_paths_json() -> str:
    return json.dumps(hermes_paths_info(), indent=2, ensure_ascii=False)
