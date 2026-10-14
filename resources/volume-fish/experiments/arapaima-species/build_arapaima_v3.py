"""Species-authored arapaima clay prototype from the accepted side silhouette.

Separate trunk, skull, jaw, opercular plates, and curved fins are deliberate
shape hypotheses. This is an isolated visual experiment, not a game asset.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


profile_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
output = Path(sys.argv[sys.argv.index("--") + 2]).resolve()
output.mkdir(parents=True, exist_ok=True)
profile = json.loads(profile_path.read_text(encoding="utf-8"))
aspect = 1 / profile["source_aspect_ratio"]
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def sample(rows, u, field):
    if u <= rows[0][0]:
        return rows[0][field]
    for a, b in zip(rows, rows[1:]):
        if u <= b[0]:
            t = (u - a[0]) / (b[0] - a[0])
            return a[field] * (1 - t) + b[field] * t
    return rows[-1][field]


def xyz(u, v, y):
    return (u - 0.5, y, (0.5 - v) * aspect)


clay = bpy.data.materials.new("Neutral form study")
clay.diffuse_color = (0.56, 0.59, 0.56, 1)
dark = bpy.data.materials.new("Recessed mouth and gills")
dark.diffuse_color = (0.12, 0.13, 0.12, 1)
report = {}


def mesh(name, verts, faces, mat=clay, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bad = sum(not edge.is_manifold for edge in bm.edges)
    bm.to_mesh(data)
    bm.free()
    for face in data.polygons:
        face.use_smooth = smooth
    report[name] = {"vertices": len(data.vertices), "faces": len(data.polygons), "nonmanifold_edges": bad}
    return obj


def loft(name, start, end, count, top, bottom, half_width, power=1.0):
    radial = 48
    verts, faces = [], []
    for i in range(count):
        u = start + (end - start) * i / (count - 1)
        hi, lo, width = top(u), bottom(u), half_width(u)
        for j in range(radial):
            a = math.tau * j / radial
            c = math.copysign(abs(math.cos(a)) ** power, math.cos(a))
            s = math.copysign(abs(math.sin(a)) ** power, math.sin(a))
            v = (hi + lo) * 0.5 - (lo - hi) * 0.5 * c
            verts.append(xyz(u, v, width * s))
            if i:
                prev = (i - 1) * radial + j
                nxt = (i - 1) * radial + (j + 1) % radial
                faces.append((prev, nxt, nxt + radial, prev + radial))
    faces.append(tuple(reversed(range(radial))))
    faces.append(tuple((count - 1) * radial + j for j in range(radial)))
    return mesh(name, verts, faces)


side = profile["body"]["sections"]
trunk_width = [
    (.083, .004), (.14, .018), (.27, .039), (.42, .053),
    (.58, .065), (.68, .063), (.75, .060), (.81, .055),
]


def source_top(u):
    return sample(side, u, 1)


def source_bottom(u):
    return sample(side, u, 2)


# A long laterally compressed trunk stops behind the gill cover.
loft("Trunk", side[0][0], .808, 115, source_top, source_bottom,
     lambda u: sample(trunk_width, u, 1))

# The upper skull, lip line and lower jaw are independent species landmarks.
# The snout narrows toward the source-image point instead of ending as a disk.
skull_width = [(.78, .058), (.84, .054), (.90, .043), (.95, .027), (.975, .020), (.9914, .015)]
lip_line = [(.78, .615), (.84, .621), (.90, .603), (.95, .559), (.975, .530), (.9914, .505)]
jaw_top = [(.808, .630), (.86, .638), (.91, .614), (.95, .568), (.975, .534), (.995, .510)]
jaw_bottom = [(.808, .711), (.86, .712), (.91, .690), (.95, .627), (.975, .580), (.995, .535)]
jaw_width = [(.808, .033), (.86, .036), (.91, .033), (.95, .027), (.975, .022), (.995, .017)]
loft("Bony_upper_skull", .78, .9914, 65, source_top,
     lambda u: sample(lip_line, u, 1), lambda u: sample(skull_width, u, 1), .84)
loft("Projecting_lower_jaw", .808, .995, 59,
     lambda u: sample(jaw_top, u, 1), lambda u: sample(jaw_bottom, u, 1),
     lambda u: sample(jaw_width, u, 1), .90)


def ellipsoid(name, location, scale, mat=clay):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    report[name] = {"vertices": len(obj.data.vertices), "faces": len(obj.data.polygons),
                    "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges)}
    bm.free()
    return obj


def operculum_edge(sign, label):
    # Curved side-only seam follows the source-image gill border. It must not
    # create a circular plate on the surface or a ring across the fish.
    landmarks = [(.820, .275), (.796, .302), (.779, .365), (.773, .451),
                 (.781, .550), (.807, .642), (.848, .700)]
    path = [Vector(xyz(u, v, sign * .052)) for u, v in landmarks]
    radial, radius = 8, .0013
    verts, faces = [], []
    for i, center in enumerate(path):
        tangent = (path[min(i + 1, len(path)-1)] - path[max(i - 1, 0)]).normalized()
        across = Vector((-tangent.z, 0, tangent.x)).normalized()
        lateral = Vector((0, 1, 0))
        for j in range(radial):
            a = math.tau * j / radial
            verts.append(tuple(center + radius * (math.cos(a) * across + math.sin(a) * lateral)))
            if i:
                q = (i - 1) * radial + j
                k = (i - 1) * radial + (j + 1) % radial
                faces.append((q, k, k + radial, q + radial))
    faces.append(tuple(reversed(range(radial))))
    faces.append(tuple((len(path)-1)*radial+j for j in range(radial)))
    mesh("Operculum_edge_" + label, verts, faces, dark)


for sign, label in [(-1, "left"), (1, "right")]:
    operculum_edge(sign, label)
    ellipsoid("Eye_" + label, xyz(.922, .507, sign * .033), (.006, .0035, .006), dark)


def smooth_outline(points, cuts=4):
    result = []
    n = len(points)
    for i in range(n):
        p0, p1, p2, p3 = [Vector(points[k % n]) for k in (i - 1, i, i + 1, i + 2)]
        for j in range(cuts):
            t = j / cuts
            q = .5 * ((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t
                        + (-p0+3*p1-3*p2+p3)*t*t*t)
            result.append(q)
    return result


for fin in profile["fins"]:
    outline = ([Vector(p) for p in fin["polygon"]] if fin["name"] == "Pectoral"
               else smooth_outline(fin["polygon"]))
    lookup = {(round(p.x, 8), round(p.y, 8)): i for i, p in enumerate(outline)}
    triangles = [tuple(p if isinstance(p, int) else lookup[(round(p.x, 8), round(p.y, 8))] for p in tri)
                 for tri in tessellate_polygon([outline])]
    root = Vector(fin["anchor"])
    direction = Vector(fin["tip"]) - root
    denom = max(direction.length_squared, 1e-8)
    for sign in ([-1, 1] if fin["paired"] else [1]):
        name = fin["name"] + ("_left" if sign < 0 else "_right") if fin["paired"] else fin["name"]
        center, thickness = [], []
        for p in outline:
            t = max(0, min(1, (p - root).dot(direction) / denom))
            depth = fin["root_depth"] * (1 - t) + fin["tip_depth"] * t
            if fin["name"] == "Pectoral":
                depth += .012 * math.sin(math.pi * t)
            center.append(xyz(p.x, p.y, sign * depth))
            thickness.append(max(fin["thickness"], .006 * (1 - t) ** 2)
                             if fin["name"] == "Pectoral" else fin["thickness"])
        n = len(center)
        verts = [(x, y + thickness[i]/2, z) for i, (x, y, z) in enumerate(center)]
        verts += [(x, y - thickness[i]/2, z) for i, (x, y, z) in enumerate(center)]
        faces = list(triangles) + [tuple(reversed([k+n for k in tri])) for tri in triangles]
        faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
        mesh(name, verts, faces)


bpy.ops.wm.save_as_mainfile(filepath=str(output / "arapaima-species-clay.blend"))
bpy.ops.export_scene.gltf(filepath=str(output / "arapaima-species-clay.glb"),
                          export_format="GLB", export_animations=False)
(output / "geometry-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("SPECIES_REPORT " + json.dumps(report))
