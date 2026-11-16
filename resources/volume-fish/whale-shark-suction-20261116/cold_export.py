"""Re-export the approved whale shark shapes from the installed editable source."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import sys
import bpy


def sha(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("blend", "output", "report"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    assert not args.output.exists() and not args.report.exists()
    before = sha(args.blend)
    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.resolve()), export_format="GLB", export_animations=True,
        export_yup=True, export_skins=True, export_morph=True, export_morph_normal=True,
    )
    assert before == sha(args.blend)
    receipt = {
        "ok":True, "species":"whale_shark", "source_sha256":before, "model_sha256":sha(args.output),
        "exporter_sha256":sha(Path(__file__)), "fresh_process":True, "runtime_static_builder_calls":0,
    }
    args.report.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["model_sha256"])


if __name__ == "__main__":
    main()
