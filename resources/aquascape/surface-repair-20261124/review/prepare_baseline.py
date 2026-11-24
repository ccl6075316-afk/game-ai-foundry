"""Restore the previous review meshes from Git and LFS into an ignored cache."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

RELEASE = Path(__file__).resolve().parent.parent
GAME = RELEASE.parents[2] / "projects/fishing-2d"
LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"


def git(*args, data=None):
    return subprocess.run(["git", "-C", str(GAME), *args],
                          input=data, stdout=subprocess.PIPE, check=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RELEASE / "release.json").read_text(encoding="utf-8"))
    revision = manifest["base_game_revision"]
    for row in manifest["items"]:
        dest = args.cache / (row["id"] + ".glb")
        expected = row["before_sha256"]
        if dest.exists() and sha256(dest.read_bytes()).hexdigest() == expected:
            continue
        path = "game/" + row["model"].removeprefix("res://")
        old = git("show", f"{revision}:{path}")
        if old.startswith(LFS_POINTER):
            old = git("lfs", "smudge", "--", path, data=old)
        if sha256(old).hexdigest() != expected:
            raise ValueError(f"Archived asset verification failed: {row['id']}")
        temp = dest.with_suffix(".part")
        temp.write_bytes(old)
        temp.replace(dest)
    print(f"Verified {len(manifest['items'])} previous versions.")


if __name__ == "__main__":
    main()
