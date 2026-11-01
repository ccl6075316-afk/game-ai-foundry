"""Opt-in actual-Godot bluegill gait trial; never installs production changes."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["qa", "preview", "capture", "body"])
    parser.add_argument("--godot", type=Path, required=True)
    parser.add_argument("--game", type=Path, default=ROOT / "projects/fishing-2d/game")
    parser.add_argument("--output", type=Path, default=ROOT / "projects/fishing-2d/experiments/blender-fish/swim-gait-132")
    args = parser.parse_args()
    from cli.toolchain_paths import toolchain_env
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = None if args.mode == "preview" else args.output / {"qa":"gait.validation.json", "capture":"capture.validation.json", "body":"body-capture.validation.json"}[args.mode]
    if report_path is not None:
        report_path.unlink(missing_ok=True)
        (args.output / (args.mode + ".launcher.validation.json")).unlink(missing_ok=True)
    command = [str(args.godot), "--path", str(args.game.resolve()), "--rendering-method", "gl_compatibility", "--log-file", str(args.output / (args.mode + ".godot.log"))]
    if args.mode == "qa":
        command.append("--headless")
    script = Path(__file__).with_name("body_swim_gait132.gd") if args.mode == "body" else Path(__file__).with_suffix(".gd")
    command += ["--script", str(script), "--", str(ROOT), str(args.output), args.mode]
    result = subprocess.run(command, env=toolchain_env({}), capture_output=args.mode != "preview", text=True)
    if args.mode == "preview":
        return result.returncode
    log = (result.stdout or "") + (result.stderr or "")
    (args.output / (args.mode + ".log")).write_text(log, encoding="utf8")
    report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    ca_diagnostic = r'ERROR: Condition "ret != noErr" is true\. Returning: ""\n\s+at: get_system_ca_certificates \(platform/macos/os_macos\.mm:1035\)\n?'
    filtered, known_ca_warnings = re.subn(ca_diagnostic, "", log)
    ok = result.returncode == 0 and "SCRIPT ERROR" not in filtered and "ERROR:" not in filtered and bool(report.get("ok"))
    body_checks = []
    if ok and args.mode == "body":
        import hashlib
        import numpy as np
        from PIL import Image
        for row in report["records"]:
            for pair in row["pairs"]:
                actual_path, reference_path = [args.output / pair[key] for key in ["actual", "reference"]]
                for key, path in [("actual", actual_path), ("reference", reference_path)]:
                    if hashlib.sha256(path.read_bytes()).hexdigest() != pair[key + "_sha256"]:
                        ok = False
                actual, reference = [np.asarray(Image.open(path).convert("RGBA")) for path in [actual_path, reference_path]]
                mask = reference[:, :, 3] > 128
                missing = int((mask & (actual[:, :, 3] < 128)).sum())
                visible = int(mask.sum())
                body_checks.append({"action":row["action"],"gait":row["candidate"]["gait"],"actual":pair["actual"],"missing_pixels":missing,"reference_pixels":visible})
                ok = ok and missing == 0 and visible > 30
    import hashlib
    receipt = {"ok":ok,"command":"fish.swim-gait132." + args.mode,"status":"done" if ok else "failed","next_action":"human_review" if ok else "fix_input","outputs":[str(report_path), str(args.output / (args.mode + ".log"))],"launcher_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"host_ca_diagnostics":known_ca_warnings,"body_checks":body_checks,"failures":[] if ok else [{"kind":"unknown","code":"godot_trial_failed","message":("Godot did not produce a fresh " + report_path.name) if not report_path.is_file() else log[-6000:]}]}
    (args.output / (args.mode + ".launcher.validation.json")).write_text(json.dumps(receipt, indent=2), encoding="utf8")
    print(json.dumps(receipt, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
