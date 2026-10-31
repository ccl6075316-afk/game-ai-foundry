"""Read-only code/disk inventory. Reports candidates; never deletes assets."""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
from collections import defaultdict
from pathlib import Path


def linked_directory(path: Path) -> bool:
    """Path.is_junction was added in Python 3.12; 3.11 remains supported."""
    is_junction = getattr(path, "is_junction", None)
    if path.is_symlink():
        return True
    if is_junction is not None:
        return is_junction()
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return True  # Skip a directory that disappeared during the inventory.
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def inventory(root: Path) -> dict:
    repos = []
    for repo in (root, root / "projects/fishing-2d"):
        if not (repo / ".git").exists():
            repos.append({"path": str(repo), "available": False})
            continue
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo).decode().split("\0")
        code = []
        families = defaultdict(int)
        for rel in filter(None, tracked):
            path = repo / rel
            if path.suffix not in {".cs", ".gd", ".py"} or not path.is_file():
                continue
            lines = len(path.read_bytes().splitlines())
            code.append({"path": rel, "lines": lines})
            if path.suffix == ".cs":
                families[str(path.parent.relative_to(repo) / path.name.split(".")[0])] += lines
        repos.append({"path": str(repo), "largest_code": sorted(code, key=lambda x: -x["lines"])[:40],
                      "csharp_families": sorted(families.items(), key=lambda x: -x[1])[:15],
                      "git_status": subprocess.check_output(["git", "status", "--short"], cwd=repo, text=True)})
    sizes = defaultdict(int)
    cache_dirs = defaultdict(lambda: {"files": 0, "bytes": 0})
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "node_modules"}
                   and not linked_directory(Path(current) / d)]
        for name in files:
            path = Path(current) / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            parts = path.relative_to(root).parts
            sizes["/".join(parts[:3] if parts[0] == "projects" else parts[:2])] += size
            for i, part in enumerate(parts[:-1]):
                if part in {".godot", "__pycache__", ".pytest_cache"}:
                    entry = cache_dirs["/".join(parts[:i + 1])]
                    entry["files"] += 1
                    entry["bytes"] += size
                    break
    return {"schema_version": 1, "command": "maintenance.inventory", "ok": True,
            "repositories": repos, "disk_groups": sorted(sizes.items(), key=lambda x: -x[1]),
            "cache_candidates": [{"path": k, **v} for k, v in sorted(cache_dirs.items(), key=lambda x: -x[1]["bytes"])],
            "policy": "Cache candidates require process, reference and Git checks before any deletion. Size/age is not obsolescence."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    allowed = [root / "output", root / "projects/fishing-2d/plans/reviews"]
    if not any(output.is_relative_to(base) for base in allowed):
        parser.error("Output must be inside repository output/ or the game review directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory(root), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output)}))


if __name__ == "__main__":
    main()
