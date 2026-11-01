"""Verify retained 112 evidence against the installed game without regenerating it."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def verify(game, archive):
    installed = read(archive / "installed-files.manifest.json")
    for row in installed["files"]:
        assert sha(game / row["path"]) == row["sha256"], row["path"]
    completion = read(archive / "completion.validation.json")
    for row in completion["reports"]:
        assert sha(archive / row["file"]) == row["sha256"], row["file"]
    for rel in ["captures/actual-game/capture.validation.json", "captures/transitions/transitions.validation.json"]:
        report = read(archive / rel)
        assert report["ok"] and len(report["records"]) == 23
        for file, digest in report["files"].items():
            assert sha(game / file) == digest, (rel, file)
        for row in report["records"]:
            assert sha(game / "assets/models/fish" / (row["species"] + ".glb")) == row["model_sha256"]
    gates = read(archive / "reports/current-fin-gates.validation.json")
    assert gates["ok"] and len(gates["roots"]) == 23 and len(gates["full_fin"]) == 8
    plan = {r["species"]: r for r in read(archive / "inputs/fin-plan-complete.json")["items"]}
    scripts = Path(__file__).resolve().parent
    for rows, poses in [(gates["roots"], 177), (gates["full_fin"], 490)]:
        for row in rows:
            report_path = archive / row["report"]
            assert sha(report_path) == row.get("report_sha256", row.get("sha256"))
            report = read(report_path)
            assert report["ok"]
            digest = row.get("model_sha256", report.get("model_sha256"))
            assert sha(game / "assets/models/fish" / (row["species"] + ".glb")) == digest
            assert row.get("poses", report.get("poses")) == poses
            if poses == 177:
                assert report["checker_sha256"] == sha(scripts / "check_runtime_fin_attachment.py")
                assert report["export_script_sha256"] == sha(scripts / "export_runtime_fin_roots112.gd")
                controller = plan[row["species"]]["controller_script"].removeprefix("res://")
                assert report["controller_sha256"] == sha(game / controller)
                assert report["exhibit_sha256"] == sha(game / "scripts/aquarium/VolumeFishExhibit.gd")
                assert report["motion_config_sha256"] == sha(game / "assets/models/fish/motion/motion.json")
            else:
                for check in report["checks"]:
                    nested = archive / "reports/final-full-fin" / row["species"] / Path(check["report"]).name
                    assert check["ok"] and sha(nested) == check["sha256"]
    body = read(archive / "reports/actual-game-body/completion.validation.json")
    assert body["ok"] and len(body["species"]) == 23
    for file, digest in body["capture_files"].items():
        assert sha(game / file) == digest, file
    for row in body["species"]:
        assert len(row["views"]) == 16 and all(v["missing_body_pixels"] == 0 for v in row["views"])
        assert sha(game / "assets/models/fish" / (row["species"] + ".glb")) == row["model_sha256"]
    for row in read(archive / "source-inputs.manifest.json")["sources"]:
        for key in ["model", "image"]:
            assert sha(archive / row[key]) == row[key + "_sha256"]
    retained = read(archive / "evidence-retention.manifest.json")
    for row in retained["retained"]:
        assert sha(archive / row["path"]) == row["sha256"], row["path"]
    return {"ok": True, "status": "done", "next_action": "human_review",
            "installed_files": len(installed["files"]), "species": 23,
            "fin_root_poses_each": 177, "full_fin_species": 8, "full_fin_poses_each": 490,
            "body_views_each": 16, "missing_body_pixels": 0,
            "retained_files_verified": len(retained["retained"]),
            "scope": "Current byte bindings and retained historical reports verified. No new GPU run, continuous-time proof, exported-build or user visual acceptance implied."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ["game", "archive", "report"]:
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.game, args.archive)
    except (AssertionError, OSError, KeyError, ValueError) as error:
        result = {"ok": False, "status": "failed", "next_action": "fix_input", "error": str(error)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
