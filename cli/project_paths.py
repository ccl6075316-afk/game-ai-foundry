"""Per-game project directory layout under projects/<slug>/.

Isolated layout (new exports):
  projects/<slug>/
    brief.json
    production.json
    progress.json
    pipeline/manifest.json
    plans/
    output/
    game/          # Godot C# project

Flat layout (legacy briefs in resources/ or cli/resources/):
  pipeline/<stem>.json, output/<stem>/, games/<stem>/, plans/
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    return _REPO_ROOT


def project_root_for_brief(brief_path: Path, *, root: Path | None = None) -> Path | None:
    """Return projects/<slug> if brief lives under that tree; else None (flat layout)."""
    repo = (root or _REPO_ROOT).resolve()
    brief = Path(brief_path).resolve()
    try:
        rel = brief.relative_to(repo)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0].lower() == "projects":
        return (repo / "projects" / parts[1]).resolve()
    return None


def is_isolated_brief(brief_path: Path, *, root: Path | None = None) -> bool:
    return project_root_for_brief(brief_path, root=root) is not None


def slug_for_brief(brief_path: Path, *, root: Path | None = None) -> str:
    proj = project_root_for_brief(brief_path, root=root)
    if proj is not None:
        return proj.name
    stem = Path(brief_path).stem
    if stem.endswith("-brief"):
        return stem[: -len("-brief")] or stem
    return stem or "game"


def default_paths_for_brief(brief_path: Path, *, root: Path | None = None) -> dict[str, Any]:
    """Absolute paths for pipeline plan defaults (+ isolated: bool)."""
    repo = (root or _REPO_ROOT).resolve()
    brief = Path(brief_path).resolve()
    proj = project_root_for_brief(brief, root=repo)
    if proj is not None:
        return {
            "project_root": proj,
            "brief": brief,
            "output_dir": proj / "output",
            "plans_dir": proj / "plans",
            "godot_project": proj / "game",
            "manifest": proj / "pipeline" / "manifest.json",
            "progress": proj / "progress.json",
            "production": proj / "production.json",
            "isolated": True,
        }
    slug = slug_for_brief(brief, root=repo)
    stem = brief.stem
    return {
        "project_root": None,
        "brief": brief,
        "output_dir": repo / "output" / stem,
        "plans_dir": repo / "plans",
        "godot_project": repo / "games" / stem,
        "manifest": repo / "pipeline" / f"{slug}.json",
        "progress": repo / "plans" / f"progress_{slug}.json",
        "production": repo / "plans" / f"production_{slug}.json",
        "isolated": False,
    }


def rel_to_repo(path: Path, *, root: Path | None = None) -> str:
    repo = (root or _REPO_ROOT).resolve()
    p = Path(path).resolve()
    try:
        return str(p.relative_to(repo)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def find_briefs(*, root: Path | None = None) -> list[Path]:
    """Newest-first brief candidates (isolated + legacy)."""
    repo = (root or _REPO_ROOT).resolve()
    found: list[Path] = []
    projects = repo / "projects"
    if projects.is_dir():
        for child in projects.iterdir():
            if not child.is_dir():
                continue
            for name in ("brief.json", f"{child.name}-brief.json"):
                p = child / name
                if p.is_file():
                    found.append(p)
                    break
    for folder in (repo / "resources", repo / "cli" / "resources"):
        if not folder.is_dir():
            continue
        for p in folder.glob("*brief*.json"):
            if p.is_file() and "example" not in p.name.lower():
                found.append(p)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def find_default_brief(*, root: Path | None = None) -> Path | None:
    briefs = find_briefs(root=root)
    return briefs[0] if briefs else None


def find_default_progress(*, brief_path: Path | None = None, root: Path | None = None) -> Path | None:
    repo = (root or _REPO_ROOT).resolve()
    if brief_path is not None:
        paths = default_paths_for_brief(brief_path, root=repo)
        prog = paths["progress"]
        if isinstance(prog, Path) and prog.is_file():
            return prog
    # Prefer newest projects/*/progress.json
    projects = repo / "projects"
    candidates: list[Path] = []
    if projects.is_dir():
        candidates.extend(projects.glob("*/progress.json"))
    plans = repo / "plans"
    if plans.is_dir():
        candidates.extend(plans.glob("progress*.json"))
    root_prog = repo / "progress.json"
    if root_prog.is_file():
        candidates.append(root_prog)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def paths_as_rel_dict(brief_path: Path, *, root: Path | None = None) -> dict[str, Any]:
    """JSON-serializable relative paths for GUI / tests."""
    repo = (root or _REPO_ROOT).resolve()
    abs_paths = default_paths_for_brief(brief_path, root=repo)
    out: dict[str, Any] = {"isolated": bool(abs_paths.get("isolated"))}
    for key, val in abs_paths.items():
        if key == "isolated":
            continue
        if val is None:
            out[key] = None
        elif isinstance(val, Path):
            out[key] = rel_to_repo(val, root=repo)
        else:
            out[key] = val
    return out


def _safe_slug(raw: str) -> str:
    import re

    s = re.sub(r"[^a-z0-9]+", "-", (raw or "").lower()).strip("-")
    return s or "game"


def resolve_isolated_brief_for_legacy(
    legacy_rel_or_path: str | Path,
    *,
    root: Path | None = None,
) -> Path | None:
    """If a projects/*/brief.json was migrated from this legacy path, return it."""
    repo = (root or _REPO_ROOT).resolve()
    needle = str(legacy_rel_or_path).replace("\\", "/").lstrip("./")
    base = Path(needle).name
    stem = base.replace(".json", "").replace("-brief", "")
    projects = repo / "projects"
    if not projects.is_dir():
        return None
    for child in projects.iterdir():
        if not child.is_dir():
            continue
        for name in ("brief.json", f"{child.name}-brief.json"):
            p = child / name
            if not p.is_file():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            meta = data.get("brief_meta") if isinstance(data, dict) else None
            if not isinstance(meta, dict):
                continue
            migrated = str(meta.get("migrated_from") or "").replace("\\", "/")
            legacy_names = meta.get("legacy_names") or []
            if migrated and (
                migrated.endswith(base)
                or migrated == needle
                or needle.endswith(migrated)
            ):
                return p.resolve()
            if isinstance(legacy_names, list) and (
                base in legacy_names or stem in legacy_names or needle in legacy_names
            ):
                return p.resolve()
            if child.name == stem or child.name == _safe_slug(stem):
                return p.resolve()
    return None


def migrate_legacy_brief_to_project(
    brief_path: Path,
    *,
    slug: str | None = None,
    root: Path | None = None,
    manifest_path: Path | None = None,
    remove_legacy_brief: bool = True,
) -> dict[str, Any]:
    """Move a flat/cli-resources brief (+ artifacts) into projects/<slug>/.

    Copies brief → projects/<slug>/brief.json, relocates output/game when found,
    rewrites pipeline manifest brief/paths/commands when provided.
    """
    import re
    import shutil

    repo = (root or _REPO_ROOT).resolve()
    src = Path(brief_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"brief not found: {src}")
    if project_root_for_brief(src, root=repo) is not None:
        raise ValueError(f"already isolated: {src}")

    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("brief must be a JSON object")

    title = ""
    project = data.get("project")
    if isinstance(project, dict):
        title = str(project.get("title") or "").strip()
    chosen_slug = _safe_slug(slug or title or slug_for_brief(src, root=repo))
    dest_root = repo / "projects" / chosen_slug
    dest_brief = dest_root / "brief.json"
    if dest_brief.is_file():
        raise FileExistsError(f"target already exists: {dest_brief}")

    dest_root.mkdir(parents=True, exist_ok=True)
    (dest_root / "pipeline").mkdir(exist_ok=True)
    (dest_root / "plans").mkdir(exist_ok=True)
    (dest_root / "output").mkdir(exist_ok=True)
    (dest_root / "game").mkdir(exist_ok=True)

    legacy_rel = rel_to_repo(src, root=repo)
    meta = data.setdefault("brief_meta", {})
    if not isinstance(meta, dict):
        meta = {}
        data["brief_meta"] = meta
    meta["migrated_from"] = legacy_rel
    meta["legacy_names"] = sorted(
        {
            src.name,
            src.stem,
            src.stem.replace("-brief", ""),
            chosen_slug,
            legacy_rel,
        }
    )
    meta["layout"] = "projects"
    dest_brief.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    moved: dict[str, str] = {"brief": rel_to_repo(dest_brief, root=repo)}

    # Discover flat output / godot from optional manifest or stem heuristics
    flat_output: Path | None = None
    flat_game: Path | None = None
    man_src = Path(manifest_path).resolve() if manifest_path else None
    if man_src is None:
        # common legacy names
        for cand in (
            repo / "pipeline" / f"{chosen_slug}.json",
            repo / "pipeline" / "manifest-black-whistle.json",
            repo / "pipeline" / f"{src.stem}.json",
            repo / "pipeline" / f"{slug_for_brief(src, root=repo)}.json",
        ):
            if cand.is_file():
                man_src = cand
                break

    if man_src and man_src.is_file():
        man = json.loads(man_src.read_text(encoding="utf-8"))
        paths = man.get("paths") if isinstance(man, dict) else None
        if isinstance(paths, dict):
            od = str(paths.get("output_dir") or "").replace("\\", "/")
            if od:
                flat_output = (repo / od).resolve() if not Path(od).is_absolute() else Path(od)
            gp = str(paths.get("godot_project") or paths.get("godot") or "").replace("\\", "/")
            if gp:
                flat_game = (repo / gp).resolve() if not Path(gp).is_absolute() else Path(gp)

    stem = src.stem
    if flat_output is None:
        for cand in (
            repo / "output" / chosen_slug,
            repo / "output" / "black-whistle-referee",
            repo / "output" / stem,
            repo / "output" / stem.replace("-brief", ""),
        ):
            if cand.is_dir():
                flat_output = cand
                break
    if flat_game is None:
        for cand in (
            repo / "games" / chosen_slug,
            repo / "games" / "black-whistle-referee",
            repo / "games" / stem,
            repo / "games" / stem.replace("-brief", ""),
        ):
            if cand.is_dir():
                flat_game = cand
                break

    dest_output = dest_root / "output"
    if flat_output and flat_output.is_dir() and flat_output.resolve() != dest_output.resolve():
        # merge into dest_output
        for item in flat_output.iterdir():
            target = dest_output / item.name
            if target.exists():
                continue
            shutil.move(str(item), str(target))
        try:
            flat_output.rmdir()
        except OSError:
            pass
        moved["output"] = rel_to_repo(dest_output, root=repo)

    dest_game = dest_root / "game"
    if flat_game and flat_game.is_dir() and flat_game.resolve() != dest_game.resolve():
        for item in flat_game.iterdir():
            target = dest_game / item.name
            if target.exists():
                continue
            shutil.move(str(item), str(target))
        try:
            flat_game.rmdir()
        except OSError:
            pass
        moved["game"] = rel_to_repo(dest_game, root=repo)

    dest_plans = dest_root / "plans"
    dest_manifest = dest_root / "pipeline" / "manifest.json"
    if man_src and man_src.is_file():
        man = json.loads(man_src.read_text(encoding="utf-8"))
        if not isinstance(man, dict):
            raise ValueError("manifest must be object")
        # Skip if already a redirect pointer
        if man.get("migrated_to") and not man.get("tasks"):
            man_src = None
    if man_src and man_src.is_file():
        man = json.loads(man_src.read_text(encoding="utf-8"))
        if not isinstance(man, dict):
            raise ValueError("manifest must be object")
        brief_cli = f"../projects/{chosen_slug}/brief.json"
        man["brief"] = f"projects/{chosen_slug}/brief.json"
        man["paths"] = {
            "repo_root": ".",
            "cli_dir": "cli",
            "output_dir": f"projects/{chosen_slug}/output",
            "plans_dir": f"projects/{chosen_slug}/plans",
            "assets_manifest": f"projects/{chosen_slug}/output/assets-manifest.json",
            "workdir": "cli",
            "project_root": f"projects/{chosen_slug}",
        }
        for task in man.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            cmd = str(task.get("command") or "")
            cmd = re.sub(r"--brief\s+\S+", f"--brief {brief_cli}", cmd)
            arts = task.get("artifacts")
            if isinstance(arts, dict):
                for k, v in list(arts.items()):
                    s = str(v).replace("\\", "/")
                    if "/plans/" in s or s.startswith("../plans/") or s.startswith("plans/"):
                        name = Path(s).name
                        for src_plan in (
                            repo / "plans" / name,
                            Path(s) if Path(s).is_absolute() else (repo / s.lstrip("./")),
                        ):
                            try:
                                sp = src_plan.resolve()
                            except OSError:
                                continue
                            if sp.is_file():
                                dest_p = dest_plans / name
                                if not dest_p.exists():
                                    shutil.copy2(sp, dest_p)
                                break
                        arts[k] = f"../projects/{chosen_slug}/plans/{name}"
                        cmd = cmd.replace(str(v), arts[k])
                        cmd = cmd.replace(str(v).replace("/", "\\"), arts[k])
            cmd = cmd.replace("output\\black-whistle-referee", f"projects/{chosen_slug}/output")
            cmd = cmd.replace("output/black-whistle-referee", f"projects/{chosen_slug}/output")
            cmd = cmd.replace("../plans\\", f"../projects/{chosen_slug}/plans/")
            cmd = cmd.replace("../plans/", f"../projects/{chosen_slug}/plans/")
            # -o ../plans\foo.json → project plans
            cmd = re.sub(
                r"-o\s+\.\./plans[/\\](\S+)",
                rf"-o ../projects/{chosen_slug}/plans/\1",
                cmd,
            )
            task["command"] = cmd
        dest_manifest.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        moved["manifest"] = rel_to_repo(dest_manifest, root=repo)
        pointer = {
            "migrated_to": f"projects/{chosen_slug}/pipeline/manifest.json",
            "brief": f"projects/{chosen_slug}/brief.json",
        }
        man_src.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if remove_legacy_brief:
        # Replace legacy with a tiny pointer so old GUI localStorage still resolves
        pointer_brief = {
            "brief_meta": {
                "redirect_to": f"projects/{chosen_slug}/brief.json",
                "migrated": True,
            },
            "project": {"title": title or chosen_slug},
            "assets": [],
        }
        src.write_text(json.dumps(pointer_brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "slug": chosen_slug,
        "brief": rel_to_repo(dest_brief, root=repo),
        "project_root": rel_to_repo(dest_root, root=repo),
        "moved": moved,
        "legacy_brief": legacy_rel,
    }
