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
    (.58, .065), (.68, .063), (.75, .060), (.808, .060),
    (.865, .052), (.91, .044), (.945, .039), (.974, .036),
    (.9914, .034),
]


def source_top(u):
    return sample(side, u, 1)


def source_bottom(u):
    return sample(side, u, 2)


# One continuous outer surface removes the circular head/trunk end-cap seam.
loft("Body_and_head", side[0][0], .9914, 152, source_top, source_bottom,
     lambda u: sample(trunk_width, u, 1))

# The accepted front reference shows one continuous face and a closed mouth,
# not the separate trapezoid jaw of v3. The cheek and lower jaw are part of a
# single outer shell. Slightly widen the snout cap so it reads as a lip rather
# than a pointed cone when seen from above.
head_width = [(.78, .061), (.808, .060), (.865, .052), (.91, .044),
              (.945, .039), (.974, .036), (.9914, .034)]
mouth_line = [(.925, .590), (.945, .571), (.974, .541), (.9914, .514)]
# Mouth and face color are evaluated separately. Raised tubes on the shell
# looked like whiskers and a straight bar in front view, so v9 omits them.


def mouth_surface_point(u, sign):
    top, bottom = source_top(u), source_bottom(u)
    v = sample(mouth_line, u, 1)
    c = max(-1, min(1, (top + bottom - 2 * v) / (bottom - top)))
    width = sample(head_width, u, 1)
    lateral = width * max(0, 1 - c*c) ** (.86/2)
    return Vector(xyz(u, v, sign * (lateral + .0008)))


def crease_tube(name, path):
    radial, radius = 8, .00095
    verts, faces = [], []
    for i, center in enumerate(path):
        tangent = (path[min(i+1, len(path)-1)] - path[max(i-1, 0)]).normalized()
        across = Vector((-tangent.z, 0, tangent.x)).normalized()
        lateral = tangent.cross(across).normalized()
        for j in range(radial):
            a = math.tau*j/radial
            verts.append(tuple(center + radius*(math.cos(a)*across + math.sin(a)*lateral)))
            if i:
                k = (i-1)*radial+j
                n = (i-1)*radial+(j+1)%radial
                faces.append((k, n, n+radial, k+radial))
    faces.append(tuple(reversed(range(radial))))
    faces.append(tuple((len(path)-1)*radial+j for j in range(radial)))
    mesh(name, verts, faces, dark)




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
    # Preserve the accepted source-image fin silhouette. Catmull rounding
    # made the small polygon fins look swollen and changed their root contour.
    outline = [Vector(p) for p in fin["polygon"]]
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
                depth += .003 * math.sin(math.pi * t)
            center.append(xyz(p.x, p.y, sign * depth))
            thickness.append(max(fin["thickness"], .002 * (1 - t) ** 2)
                             if fin["name"] == "Pectoral" else fin["thickness"])
        n = len(center)
        verts = [(x, y + thickness[i]/2, z) for i, (x, y, z) in enumerate(center)]
        verts += [(x, y - thickness[i]/2, z) for i, (x, y, z) in enumerate(center)]
        faces = list(triangles) + [tuple(reversed([k+n for k in tri])) for tri in triangles]
        faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
        fin_obj = mesh(name, verts, faces, smooth=False)
        # Smooth each membrane face, but keep the narrow perimeter wall sharp.
        # Averaging the wall normal into the membrane was the main puff effect.
        for poly in fin_obj.data.polygons[:2 * len(triangles)]:
            poly.use_smooth = True


bpy.ops.wm.save_as_mainfile(filepath=str(output / "arapaima-species-clay.blend"))
bpy.ops.export_scene.gltf(filepath=str(output / "arapaima-species-clay.glb"),
                          export_format="GLB", export_animations=False)
(output / "geometry-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("SPECIES_REPORT " + json.dumps(report))
