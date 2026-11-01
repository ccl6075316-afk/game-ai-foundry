"""Rebuild seven Nile fin cages from source contours within a whole-fish probe.

Rejected mixed-route diagnostic: A-derived body and B-derived fins. The user
selected B; this script is retained only to reproduce the deviation evidence.
"""

import bpy
import bmesh
import hashlib
import json
import math
import sys
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform, delaunay_2d_cdt

if "--reproduce-rejected-mixed-route" not in sys.argv:
    raise SystemExit("Rejected A-body/B-fin diagnostic; continue the selected B route instead.")


repo = Path(__file__).resolve().parents[3]
trial = repo / "projects/fishing-2d/experiments/nile-dorsal-route-trial"
base = trial / "round2"
out = trial / "round3-whole-budget-probe"
assert out.is_dir()
source = base / "fins-candidate.blend"
plan = json.loads((base / "fin-build.plan.json").read_text(encoding="utf8"))
profile = json.loads((trial / "trial-profile.json").read_text(encoding="utf8"))
targets = {"Dorsal": 40, "Anal": 24, "Caudal": 28,
           "Pectoral_left": 12, "Pectoral_right": 12,
           "Pelvic_left": 10, "Pelvic_right": 10}


def nearline(q, line):
    best = (float("inf"), None)
    for a, b in zip(line, line[1:]):
        edge = b - a
        t = max(0.0, min(1.0, (q - a).dot(edge) / max(edge.length_squared, 1e-12)))
        point = a + edge * t
        if (q - point).length < best[0]:
            best = ((q - point).length, point)
    return best


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def simplify(poly, baseline, target):
    # Preserve root stations and extremal source landmarks. The remaining
    # boundary uses a progressive area metric rather than mesh decimation.
    locked = {min(range(len(poly)), key=lambda i: (poly[i] - q).length)
              for q in baseline}
    for axis in (0, 1):
        locked.add(min(range(len(poly)), key=lambda i: poly[i][axis]))
        locked.add(max(range(len(poly)), key=lambda i: poly[i][axis]))
    assert len(locked) < target
    live = list(range(len(poly)))
    while len(live) > target:
        costs = []
        for j, idx in enumerate(live):
            if idx in locked:
                continue
            a, b, c = (poly[live[(j + k) % len(live)]] for k in (-1, 0, 1))
            area = abs((b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x))
            costs.append((area, j))
        assert costs
        live.pop(min(costs)[1])
    return [poly[i] for i in live]


def material(name, path):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.surface_render_method = "DITHERED"
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 1.0
    image = bpy.data.images.load(str(path), check_existing=True)
    image.pack()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest"
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat


bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.preferences.filepaths.save_version = 0
assert hashlib.sha256(source.read_bytes()).hexdigest() == "e5d5364e8768487765baac4c7df4a2ba9e2b035e9e7b5aba035dcb8050406bc4"
for name in ("Eye_relief112_-1_0", "Eye_relief112_1_0"):
    bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
body = bpy.data.objects["Closed_body"]
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
modifier = body.modifiers.new("budget-probe", "DECIMATE")
modifier.ratio = 920 / len(body.data.polygons)
modifier.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=modifier.name)
assert len(body.data.polygons) == 920
body_points = [v.co.copy() for v in body.data.vertices]
body_faces = [tuple(p.vertices) for p in body.data.polygons]
bvh = BVHTree.FromPolygons(body_points, body_faces, all_triangles=True)
body_weights = [{body.vertex_groups[g.group].name:g.weight for g in v.groups}
                for v in body.data.vertices]
xmin = min(v.x for v in body_points)
zcenter = (min(v.z for v in body_points if v.x < xmin + .002) +
           max(v.z for v in body_points if v.x < xmin + .002)) / 2


def body_hit(q, direction):
    hit, normal, face, _ = bvh.ray_cast(q + direction * 2, -direction, 4)
    if hit is None:
        hit, normal, face, _ = bvh.find_nearest(q)
    if normal.dot(direction) < 0:
        normal = -normal
    return hit, normal


def weights(point):
    hit, _, face, _ = bvh.find_nearest(point)
    ids = body_faces[face]
    bary = barycentric_transform(hit, *[body_points[i] for i in ids[:3]],
                                  Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1)))
    result = defaultdict(float)
    for i, w in zip(ids, bary):
        for name, value in body_weights[i].items():
            result[name] += max(0, w) * value
    return result


records = []
for spec in plan["fins"]:
    name = spec["name"]
    obj = bpy.data.objects[name]
    original = [Vector(p) for p in spec["polygon_px"]]
    baseline = [Vector(p) for p in spec["baseline_px"]]
    outline = simplify(original, baseline, targets[name])
    # Add a few interior support points. CDT keeps the simplified authored
    # boundary while making a finite, bendable membrane rather than a fan
    # of highly stretched triangles around a single center.
    center = sum(outline, Vector((0,0))) / len(outline)
    root = sum(baseline, Vector((0,0))) / len(baseline)
    seeds = outline + [root.lerp(center, f) for f in (.45, .8)]
    xy, _, faces, *_ = delaunay_2d_cdt(
        [p / 1961 for p in seeds],
        [(i, (i+1)%len(outline)) for i in range(len(outline))],
        [list(range(len(outline)))], 1, 1e-8)
    tri = [tuple(face) for face in faces if len(face) == 3]
    used = sorted({i for face in tri for i in face})
    remap = {index:i for i,index in enumerate(used)}
    pixels = [xy[i]*1961 for i in used]
    tri = [tuple(remap[i] for i in face) for face in tri]
    n = len(pixels)
    distances = [nearline(p, baseline)[0] for p in pixels]
    max_distance = max(distances)
    paired = name.startswith(("Pectoral", "Pelvic"))
    tail = name == "Caudal"
    side = -1 if name.endswith("_left") else 1
    direction = Vector((0,side,0)) if paired else Vector((-1,0,0)) if tail else Vector((0,0,1 if name == "Dorsal" else -1))
    verts = []
    skin = []
    thickness = []
    roots = []
    bone = name + "_2"
    for i, (p, distance) in enumerate(zip(pixels, distances)):
        basal = nearline(p, baseline)[1]
        bp = Vector(((basal.x-980.5)/1961, 0, (486-basal.y)/1961))
        if tail:
            bp.z = zcenter + (bp.z-zcenter)*plan["tail"]["end_height_scale"]
        hit, normal = body_hit(bp, direction)
        s = min(1.0, distance/max_distance)
        gain = 1-smooth(distance/14)
        point = Vector(((p.x-980.5)/1961, 0, (486-p.y)/1961))
        if paired:
            point.y = side*(abs(hit.y)+spec["spread_native"]*smooth(s)+spec["camber_mm"]/1000/profile["runtime_scale"]*math.sin(math.pi*s))
        elif tail:
            point.x += xmin+.00015-(baseline[0].x-980.5)/1961
            point.y = spec["camber_mm"]/1000/profile["runtime_scale"]*math.sin(math.pi*s)
        else:
            point.z += hit.z-bp.z
            point.y = spec["camber_mm"]/1000/profile["runtime_scale"]*math.sin(math.pi*s)
        delta = Vector(((p.x-basal.x)/1961, 0, -(p.y-basal.y)/1961))
        tangent = delta-normal*delta.dot(normal)
        if paired:
            tangent.y = side*abs(tangent.y)
        root_point = hit+tangent*.65-normal*.00015
        if tail:
            root_point = Vector((xmin+.00015, 0, bp.z+tangent.z*.65))
        point = point.lerp(root_point, gain)
        root_mm = spec["root_mm"]
        if tail:
            sh, _, _, _ = bvh.ray_cast(Vector((xmin+.0001,1,point.z)),Vector((0,-1,0)),2)
            root_mm = max(.4,2*abs(sh.y)*profile["runtime_scale"]*1000-.08) if sh else .4
        width = spec["edge_mm"]+(root_mm-spec["edge_mm"])*(1-s)**1.6
        thickness.append(width/1000/profile["runtime_scale"])
        if distance <= 4:
            roots.append(i)
        elif not tail:
            nearest, nn, _, _ = bvh.find_nearest(point)
            clearance = thickness[-1]*.5+.0003
            if (point-nearest).dot(nn) < clearance:
                point = nearest+nn*clearance
        mix = weights(point)
        fin_weight = smooth((distance-5)/max(10,max_distance*.65))*spec["fin_influence"]
        mix = {key:val*(1-fin_weight) for key,val in mix.items()}
        mix[bone] = mix.get(bone,0)+fin_weight
        mix = dict(sorted(mix.items(),key=lambda v:-v[1])[:4])
        amount = sum(mix.values())
        skin.append({key:value/amount for key,value in mix.items()})
        verts.append(point)
    assert roots, name
    mid = bpy.data.meshes.new(name+"_low_mid")
    mid.from_pydata(verts,[],tri)
    mid.update()
    bm = bmesh.new()
    bm.from_mesh(mid)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mid)
    bm.free()
    tri = [tuple(face.vertices) for face in mid.polygons]
    normal = [v.normal.copy() for v in mid.vertices]
    solid = [p+normal[i]*thickness[i]*.5 for i,p in enumerate(verts)] + [p-normal[i]*thickness[i]*.5 for i,p in enumerate(verts)]
    faces = tri+[tuple(i+n for i in reversed(t)) for t in tri]
    edges = Counter(tuple(sorted((face[j],face[(j+1)%3]))) for face in tri for j in range(3))
    for a,b,c in tri:
        for x,y in ((a,b),(b,c),(c,a)):
            if edges[tuple(sorted((x,y)))] == 1:
                faces.extend(((x,x+n,y+n),(x,y+n,y)))
    mesh = bpy.data.meshes.new(name+"_source_low")
    mesh.from_pydata(solid,[],faces)
    mesh.update()
    obj.data = mesh
    uv = mesh.uv_layers.new(name="UVMap")
    safe = np.load(base/spec["wall_donor_field"])
    for face in mesh.polygons:
        face.material_index = int(face.index >= len(tri)*2)
        face.use_smooth = True
        for li in face.loop_indices:
            index = mesh.loops[li].vertex_index%n
            pixel = pixels[index]
            if face.material_index:
                x,y = round(pixel.x),round(pixel.y)
                x = max(0,min(1960,x)); y = max(0,min(971,y))
                pixel = Vector((float(safe["x"][y,x])+.5,float(safe["y"][y,x])+.5))
            uv.data[li].uv = (pixel.x/1961,1-pixel.y/972)
    obj.vertex_groups.clear()
    for i, row in enumerate(skin+skin):
        for bone_name,value in row.items():
            group = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
            group.add([i],value,"REPLACE")
    mesh.materials.clear()
    mat = material(name+"_low_source",base/spec["image"])
    mesh.materials.append(mat)
    mesh.materials.append(mat)
    bm = bmesh.new(); bm.from_mesh(mesh)
    manifold = all(edge.is_manifold for edge in bm.edges)
    zero = sum(face.calc_area() <= 1e-13 for face in bm.faces)
    bm.free()
    assert manifold and zero == 0, (name,manifold,zero)
    records.append({"name":name,"outline_vertices":len(outline),"triangles":len(faces),"root_vertices":len(roots)*2,"manifold":manifold})
    bpy.data.meshes.remove(mid)

total = len(body.data.polygons)+sum(row["triangles"] for row in records)
assert total <= 1500, total
blend = out/"whole-1500-source-fin-probe.blend"
glb = out/"whole-1500-source-fin-probe.glb"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",use_selection=True,export_skins=True,export_animations=True)
sha = lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report = {"kind":"nile_source_fin_lowpoly_probe","ok":True,"formal_acceptance":False,"installed":False,
          "body_triangles":len(body.data.polygons),"fins":records,"whole_triangles":total,
          "source_round2_sha256":sha(base/"fins-candidate.blend"),
          "blend_sha256":sha(blend),"glb_sha256":sha(glb),
          "limitations":["Body is a decimated comparator, not final B construction","Texture alpha/sidewall and root transfer need visual and full motion review","Static material migration remains pending"]}
(out/"source-fin-probe.validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print(json.dumps(report,ensure_ascii=False))
