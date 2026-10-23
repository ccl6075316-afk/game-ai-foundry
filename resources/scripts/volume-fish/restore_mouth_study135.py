"""Verify or restore the retained static mouth study, without installing assets.

The manifest uses Fish-relative paths. Historical receipts remain byte exact;
only temporary execution plans are rebased when restoring to an empty directory.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root, name):
    part = PurePosixPath(name)
    if part.is_absolute() or ".." in part.parts:
        raise ValueError(f"Unsafe manifest path: {name}")
    path = root.joinpath(*part.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes root: {name}")
    return path


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--foundry", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--restore-to", type=Path, help="Empty scratch directory; never the live checkout")
    args = parser.parse_args()
    foundry = args.foundry.resolve()
    fish = foundry / "projects/fishing-2d"
    manifest = json.loads(args.manifest.read_text())
    for item in manifest["retained_files"]:
        assert sha(safe_path(fish, item["path"])) == item["sha256"], item["path"]
    for item in manifest["foundry_tools"] + manifest["external_inputs"]:
        assert sha(safe_path(foundry, item["path"])) == item["sha256"], item["path"]
    archive = safe_path(fish, manifest["archive"]["path"])
    assert sha(archive) == manifest["archive"]["sha256"]
    expected = {item["path"]: item for item in manifest["archive"]["members"]}
    with tarfile.open(archive, "r:xz") as stream:
        members = stream.getmembers()
        assert len(members) == len(expected) and {m.name for m in members} == set(expected)
        for member in members:
            safe_path(fish, member.name)
            assert member.isfile() and member.size == expected[member.name]["bytes"]
            assert hashlib.sha256(stream.extractfile(member).read()).hexdigest() == expected[member.name]["sha256"], member.name
    result = {"ok": True, "command": "fish.verify-mouth-study135", "retained_files": len(manifest["retained_files"]), "archive_members": len(expected), "production_installed": False}
    if args.restore_to:
        dest = args.restore_to.resolve()
        assert not dest.is_relative_to(foundry) and not foundry.is_relative_to(dest), "Restore outside the live checkout"
        assert not dest.exists() or not any(dest.iterdir()), "Restore target must be empty"
        dest.mkdir(parents=True, exist_ok=True)
        restored_fish = dest / "projects/fishing-2d"
        for item in manifest["retained_files"]:
            target = safe_path(restored_fish, item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe_path(fish, item["path"]), target)
        with tarfile.open(archive, "r:xz") as stream:
            for member in stream.getmembers():
                target = safe_path(restored_fish, member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(stream.extractfile(member).read())
        old = manifest["original_foundry_root"]
        external = {old + "/" + item["path"]: str(safe_path(foundry, item["path"])) for item in manifest["external_inputs"]}

        def rebase(value):
            if isinstance(value, dict):
                return {rebase(k): rebase(v) for k, v in value.items()}
            if isinstance(value, list):
                return [rebase(v) for v in value]
            if isinstance(value, str):
                if value in external:
                    return external[value]
                if value.startswith(old + "/"):
                    return str(dest) + value[len(old):]
                if value.startswith("projects/fishing-2d/"):
                    return str(dest / value)
            return value

        study = restored_fish / "experiments/blender-fish"
        # Only execution dependencies need new paths. Keep other historical
        # plans/reports untouched, and do not claim their old hashes validate a rerun.
        for name in ["mouth-ink-132/trial.plan.json", "lip-pixels-134/trial.plan.json", "lip-uv-alignment-135/trial.plan.json", "lip-uv-alignment-135/preview.plan.json"]:
            path = study / name
            value = rebase(json.loads(path.read_text()))
            if name == "lip-uv-alignment-135/trial.plan.json":
                value["frozen_inputs"] = {p: sha(Path(p)) for p in value["frozen_inputs"]}
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        result.update(command="fish.restore-mouth-study135", restored_root=str(dest), trial=str(study / "lip-uv-alignment-135"), note="Scratch execution plans rebased; historical reports are not new validation. Render with the live Fish project and retained Foundry renderer. No rig/motion/fin/body/LOD acceptance.")
        (dest / "replay.receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    run()
