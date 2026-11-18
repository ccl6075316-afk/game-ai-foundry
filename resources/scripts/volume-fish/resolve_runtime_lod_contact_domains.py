"""Map complete authored fin roots and accepted packed fin faces to current native Godot indices."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("posed_directory", type=Path)
parser.add_argument("output_directory", type=Path)
parser.add_argument("--search", action="append", type=Path, default=[])
args = parser.parse_args()
d = args.posed_directory
folders = args.search or [Path("projects/fishing-2d/plans/reviews"), Path("resources/volume-fish")]
manifests = [path for folder in folders for path in folder.rglob("*parts-manifest*.json")]
paths = [
    path
    for folder in folders
    for path in folder.rglob("*.json")
    if (
        "root" in path.name.lower()
        or "plan" in path.name.lower()
        or path.name.startswith("nile-tilapia-final")
    )
    and "rest_points_gltf" in path.read_text(encoding="utf-8", errors="replace")
]
fin = re.compile(r"(^|_)(anal|adipose|caudal|dorsal|firstdorsal|seconddorsal|pectoral|pelvic)($|_)", re.I)
body = re.compile("body|ribbon", re.I)
transforms = [np.array([1, 1, f]) for f in (-1, 1)]
tol = 2e-6


def ident(name):
    return name.lower().removesuffix("_mesh")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def catalog_roots():
    out = defaultdict(list)
    for p in sorted(paths):
        try:
            j = read(p)
        except ValueError:
            continue
        for item in j.get("items", [j]):
            if not isinstance(item, dict):
                continue
            s = item.get("species")
            if not s:
                s = next(
                    (n for n in species if n in p.as_posix() or n.replace("_", "-") in p.as_posix()), None
                )
            if not s:
                continue
            f = item.get("current_export_domains", item.get("fins", {}))
            if isinstance(f, list):
                f = {r["name"]: r for r in f}
            if not isinstance(f, dict):
                continue
            domains = {
                ident(k): v["rest_points_gltf"]
                for k, v in f.items()
                if isinstance(v, dict) and len(v.get("rest_points_gltf", [])) >= 2
            }
            if domains:
                out[s].append((p, item, domains))
    return out


def packed(s, positions, faces):
    tree = cKDTree(positions)
    _, ids = np.unique(np.round(positions, 6), axis=0, return_inverse=True)
    tri_keys = {tuple(sorted(ids[f])): i for i, f in enumerate(faces)}
    choices = []
    for p in sorted(manifests):
        if (
            s not in p.as_posix()
            and s.replace("_", "-") not in p.as_posix()
            and not (s == "nile_tilapia" and "nile-clean-pixel" in p.as_posix())
        ):
            continue
        j = read(p)
        if "attributes" not in j:
            continue
        vertex = np.asarray(j["attributes"]["POSITION"])
        indices = np.asarray(j["indices"], dtype=int)
        for flip in transforms:
            ds, idx = tree.query(vertex * flip)
            matched = defaultdict(list)
            missing = defaultdict(int)
            for part in j["parts"]:
                if part["role"] in ("body", "body_skin", "mouth"):
                    continue
                a, b = part["index_range"]
                name = part["name"] if part["role"] == "fin" or fin.search(part["name"]) else "aux"
                for face in indices[a:b].reshape(-1, 3):
                    loc = tri_keys.get(tuple(sorted(ids[idx[face]])))
                    if loc is None or np.max(ds[face]) > tol:
                        missing[name] += 1
                    else:
                        matched[name].append(loc)
            choices.append(
                (sum(len(x) for x in matched.values()), -sum(missing.values()), p, matched, missing)
            )
    if not choices:
        raise ValueError(f"No accepted packed fin manifest for {s}")
    _, count, p, matched, missing = max(choices, key=lambda q: q[:2])
    if count:
        raise ValueError(f"Unmapped packed triangles for {s}: {dict(missing)}")
    return matched, p


species = sorted((p.stem for p in d.glob("*.f32")), key=lambda name: (-len(name), name))
catalog = catalog_roots()
out = args.output_directory
out.mkdir(parents=True, exist_ok=True)
for s in sorted(species):
    inp = read(d / (s + ".json"))
    rows = []
    part_ranges = defaultdict(list)
    packed_path = None
    pos = []
    offset = 0
    for m in inp["mesh"]:
        for i, surface in enumerate(m["surfaces"]):
            p = np.asarray(surface["positions"]).reshape(-1, 3)
            pos.extend(p)
            faces = np.asarray(surface["triangles"]).reshape(-1, 3)
            if len(inp["mesh"]) == 1:
                assert len(m["surfaces"]) == 1
                matched, packed_path = packed(s, p, faces)
                labeled = np.full(len(faces), "body", dtype=object)
                for name, ids in matched.items():
                    labeled[ids] = name
            elif body.search(m["name"]):
                labeled = ["body"] * len(faces)
            elif fin.search(m["name"]):
                labeled = [m["name"]] * len(faces)
            else:
                labeled = ["aux"] * len(faces)
            for face, name in zip(faces, labeled):
                if name not in ["body", "aux"]:
                    part_ranges[name].extend((face + offset).tolist())
            rows.append(dict(mesh=m["name"], surface=i, parts=list(labeled)))
            offset += len(p)
    pos = np.asarray(pos)
    roots = {}
    lacks = []
    for part, vert in part_ranges.items():
        vertex = np.unique(vert)
        tree = cKDTree(pos[vertex])
        candidates = []
        for path, item, fin_domains in catalog[s]:
            if ident(part) not in fin_domains:
                continue
            ref = np.asarray(fin_domains[ident(part)])
            cur = inp["model_sha256"] in str(item.get("model_sha256", item.get("model", "")))
            for flip in transforms:
                distances, indices = tree.query(ref * flip)
                success = np.count_nonzero(distances <= tol)
                coverage = success == len(ref)
                candidates.append(
                    (
                        coverage,
                        cur if coverage else False,
                        success,
                        -float(distances.max()),
                        path,
                        len(ref),
                        indices[distances <= tol],
                    )
                )
        if not candidates:
            lacks.append((part, "source"))
            continue
        full, cur, count, gap, ref, total, ids = max(candidates, key=lambda q: q[:4])
        root_v = np.unique(vertex[ids])
        all_wedges = np.asarray(tree.query_ball_point(pos[root_v], r=tol), dtype=object)
        selected = sorted({int(vertex[j]) for matches in all_wedges for j in matches})
        if not full:
            lacks.append((part, f"{count}/{total}", ref.name))
        roots[part] = dict(
            source=str(ref),
            sha256=sha(ref),
            points=selected,
            source_points=int(count),
            source_total=total,
            max_mapping_error_m=abs(gap),
            exact_model=cur,
            complete=bool(full),
        )
    print(s, len(part_ranges), "missing", lacks)
    (out / (s + ".json")).write_text(
        json.dumps(
            dict(
                model_sha256=inp["model_sha256"],
                surfaces=rows,
                roots=roots,
                unmapped=lacks,
                packed_source=str(packed_path),
                packed_sha256=sha(packed_path) if packed_path else None,
            )
        )
    )
