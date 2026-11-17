"""Bind the approved two-species feeding replay to an installed game checkout."""
from hashlib import sha256
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parent
ASSETS = {
    "smooth_hammerhead": ("无沟双髻鲨", 300, 11, 25, "smooth-hammerhead-final-20261106.json"),
    "scalloped_hammerhead": ("路氏双髻鲨", 250, 9, 24, "scalloped-hammerhead-final-20261104.json"),
}

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True, help="The game's Godot project folder")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    game, output = args.game.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    release = json.loads((ROOT.parent / "release.json").read_text())
    entries, bindings = [], {}
    motion = game / "scripts/aquarium/FoundryFishMotion.gd"
    assert digest(motion) == release["swim_controller_sha256"], motion
    for species, (label, length, mesh_count, surface_count, profile) in ASSETS.items():
        model = game / f"assets/models/fish/{species}.glb"
        assert digest(model) == release["fish"][species]["model_sha256"], species
        profile = game / "assets/models/fish/motion" / profile
        assert digest(profile) == release["fish"][species]["motion_profile_sha256"], species
        input_paths = [model, motion, profile, *sorted(ROOT.rglob("*.gd"))]
        bindings.update({str(path): digest(path) for path in input_paths})
        viewer = {
            "species": species, "model": str(model), "model_sha256": digest(model),
            "model_scale": [1, 1, 1], "inventory": {"mesh_count": mesh_count, "surface_count": surface_count},
            "controller": {"runtime": str(motion), "profile": str(profile), "action": "Swim"},
            "engine_materials": {"texture_filter": "nearest"},
            "input_paths": [str(path) for path in input_paths],
        }
        entries.append({"id": species, "species": species, "label": label, "status": "已验收",
                        "length_cm": length, "triangles": 3994, "viewer": viewer})
    path = output / "catalog.json"
    path.write_text(json.dumps({"mode": "interactive", "entries": entries, "bindings": bindings,
                                "output": str(output)}, ensure_ascii=False, indent=2) + "\n")
    print(path)

if __name__ == "__main__":
    main()
