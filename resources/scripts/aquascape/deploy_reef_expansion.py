"""Stage reviewed expansion candidates and register them after Godot cold import."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"resources/scripts/aquascape"))
from optimize_scenery import budget_type, metrics
from validate_art_models import inspect
from validate_scenery_budget import validate

GAME = ROOT/"projects/fishing-2d/game"
ART = ROOT/"resources/aquascape/reef-expansion-20261123"
WORK = ROOT/"work/reef-expansion-20261123"
ACTIVE = GAME/"assets/aquascape-expansion-v1"
POLICY = json.loads((ART.parent/"geometry-budgets.json").read_text())

def load(path):
    return json.loads(path.read_text())

def write(path, value):
    temp = path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")
    temp.replace(path)

def member(row, *keys):
    return next((row[key] for key in keys if row.get(key)), None)

def resolve(value):
    return ROOT/value if value else None

def relative(path):
    return str(path.relative_to(ROOT))

def prepare(row, fixed_ids, fixed_hashes):
    key = row["id"]
    if not re.fullmatch("[a-z][a-z0-9_]+",key) or key in fixed_ids:
        raise ValueError(f"Missing or conflicting asset ID {key}")
    directory = resolve(member(row,"glb","source_glb","model")).parent
    source = directory/(key+".glb")
    editable = resolve(member(row,"blend","editable_source")) or source.with_suffix(".blend")
    proof = resolve(member(row,"report","validation")) or directory/"geometry-and-material.validation.json"
    native = resolve(member(row,"native_review","native_views"))
    intent = resolve(member(row,"source_evidence","source_intent","source_board")) or directory/"material-source.handoff.json"
    if not native or not all(p.is_file() and p.stat().st_size>0 for p in [source,editable,proof,native,intent]):
        raise ValueError(f"{key}: candidate needs source, model, intent, geometry proof and native review")
    number = metrics(source)
    evidence = load(proof)
    if (evidence["ok"] if "ok" in evidence else evidence.get("glb", {}).get("ok")) is not True:
        raise ValueError(f"{key}: candidate proof failed")
    # Both geometry validation and native visual evidence are required before placement.
    if native.stat().st_mtime+1 < source.stat().st_mtime:
        raise ValueError(f"{key}: Godot review predates the candidate build")
    if number["sha256"] in fixed_hashes:
        raise ValueError(f"{key}: binary is already registered under another ID")
    actual = inspect(source, allow_alpha_mask=row.get("material_mode")=="mask")
    kind = budget_type(row,POLICY)
    budget = POLICY["types"][kind]
    if not actual["ok"] or actual["nonmanifold_edges"] or number["triangles"]>budget["hard_limit"]:
        raise ValueError(f"{key}: invalid payload {actual['failures']} or complete-instance budget violation")
    name = member(row,"name_zh","name","label")
    nominal = member(row,"nominal_xyz_m","dimensions_m")
    placed_value = row.get("placement_size_m") or max(nominal)
    if not name or not 0.03<=placed_value<=6:
        raise ValueError(f"{key}: missing name or invalid placement size")
    registered = {
        "id":key,"name_zh":name,"category":row["category"],
        "environment":member(row,"environment","aquatic_ecology","ecology"),
        "budget_type":kind,
        "model":"res://"+(ACTIVE.relative_to(GAME)/(key+".glb")).as_posix(),
        "animated":False,
        "placement_size_m":placed_value,
        "nominal_xyz_m":nominal,
        "geometry_budget":{**budget,"type":kind},
    }
    for field in ("scientific_name","source_url","habitat","algae_option","rooted_current","placement_anchor","material_mode"):
        if row.get(field):
            registered[field] = row[field]
    integrated = {
        "id":key,**number,
        "editable_source":relative(editable),"intent":relative(intent),
        "validation":relative(proof),"native_review":relative(native),"source_glb":relative(source),
        "user_acceptance":"pending",
    }
    return registered, integrated, source

def run(godot, mode, *arguments, logname):
    log = WORK/logname
    with log.open("w") as buf:
        process = subprocess.run([str(godot),"--headless","--path",str(GAME),*mode,*map(str,arguments)],
                                 stdout=buf,stderr=subprocess.STDOUT)
    if process.returncode or (mode[0] == "--script" and any(line.startswith(("SCRIPT ERROR:", "SHADER ERROR:", "ERROR:")) for line in log.read_text().splitlines())):
        raise RuntimeError(f"Godot exited {process.returncode}; see {log}")

def install(manifests, godot):
    WORK.mkdir(parents=True,exist_ok=True)
    catalog = ACTIVE/"catalog.json"
    ledger = ART/"installed-expansion.handoff.json"
    check = ART/"expansion-budget.validation.json"
    placement = ART/"expansion-placement.validation.json"
    previous = load(catalog) if catalog.exists() else {"assets":[]}
    recorded = load(ledger) if ledger.exists() else {"assets":[]}
    current = {r["id"]:r for r in previous["assets"]}
    durable = {r["id"]:r for r in recorded["assets"]}
    baseline_dirs = ("aquascape-v5","aquascape-decor-v1","aquascape-reef-foundation-v1")
    baseline = [row for name in baseline_dirs for row in load(GAME/"assets"/name/"catalog.json")["assets"]]
    fixed_ids = {r["id"] for r in baseline}
    fixed_hashes = {hashlib.sha256((GAME / r["model"].removeprefix("res://")).read_bytes()).hexdigest() for r in baseline}
    seen = set()
    template = (GAME/"assets/aquascape-reef-foundation-v1/reef_backwall.glb.import").read_text().split("[params]",1)[1]
    params = template.replace("meshes/generate_lods=true","meshes/generate_lods=false")
    sources = []
    for manifest in manifests:
        for row in load(manifest)["assets"]:
            registered,integrated,source = prepare(row, fixed_ids, fixed_hashes)
            key = row["id"]
            if key in seen:
                raise ValueError(f"{key} appears multiple times")
            seen.add(key)
            if key in durable:
                if durable[key]["sha256"] != integrated["sha256"]:
                    raise ValueError(f"{key} is already installed with a different build")
                continue
            if any(i["sha256"]==integrated["sha256"] for i in durable.values()):
                raise ValueError(f"{key}: same model already staged")
            current[key],durable[key] = registered,integrated
            sources.append((source,registered))
    if not sources:
        print(f"All {len(durable)} expansion assets already installed")
        return
    ACTIVE.mkdir(exist_ok=True)
    for source,row in sources:
        path = ACTIVE/source.name
        shutil.copyfile(source,path)
        import_uri = row["model"]
        expected = hashlib.md5(import_uri.encode()).hexdigest()
        cache = f"res://.godot/imported/{source.name}-{expected}.scn"
        header = f'[remap]\n\nimporter="scene"\nimporter_version=1\ntype="PackedScene"\npath="{cache}"\n\n[deps]\n\nsource_file="{import_uri}"\ndest_files=["{cache}"]\n\n[params]'
        option = params.replace("meshes/create_shadow_meshes=true","meshes/create_shadow_meshes=false") if row.get("rooted_current") else params
        path.with_suffix(".glb.import").write_text(header+option)
    draft = WORK/"catalog-expansion-staging.json"
    write(draft,{"assets":list(current.values())})
    report = validate(ROOT,[draft],check)
    if not report["ok"]:
        raise RuntimeError(f"Deployment gated by {report['failures']}")
    run(godot,("--editor","--import"),logname="expansion-import.log")
    write(catalog,load(draft))
    try:
        run(godot,("--script",str(ART/"placement_reef_probe.gd"),"--"),placement,logname="expansion-placement.log")
    except RuntimeError:
        if previous["assets"]:
            write(catalog,previous)
        else:
            catalog.unlink()
        raise
    write(ledger,{"assets":list(durable.values()),"count":len(durable),"catalog_total":len(baseline)+len(durable)})
    print(f"Placed and verified {len(baseline)+len(durable)} assets ({len(sources)} added in this run)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot",type=Path,required=True)
    parser.add_argument("manifests",type=Path,nargs="+")
    args = parser.parse_args()
    install(args.manifests,args.godot)
