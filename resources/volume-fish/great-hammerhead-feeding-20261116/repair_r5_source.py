"""Fit the complete native eye chart to the actual finite head surface."""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'resources/scripts/volume-fish'))
from check_hammerhead_eye_visibility import clip, cross, depth

R4, OUTPUT = map(Path, sys.argv[sys.argv.index('--') + 1:])
OUTPUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R4))
body = bpy.data.objects['Reference_head_body']
body.data.calc_loop_triangles()
body_points = np.asarray([tuple(v.co) for v in body.data.vertices])
body_faces = np.asarray([tuple(t.vertices) for t in body.data.loop_triangles])


def build_eye(eye):
    original = eye.data
    source_positions = np.asarray([tuple(v.co) for v in original.vertices])
    source_projected = source_positions[:, [0, 2]]
    side = float(np.sign(source_positions[:, 1].mean()))
    center = (source_projected.min(0) + source_projected.max(0)) * .5
    radius = (source_projected.max(0) - source_projected.min(0)) * .5
    old_loops = np.asarray([source_projected[corner.vertex_index] for corner in original.loops])
    old_uvs = np.asarray([tuple(c.uv) for c in original.uv_layers.active.data])
    uv_map = np.linalg.lstsq(np.column_stack((old_loops - center, np.ones(len(old_loops)))), old_uvs, rcond=None)[0]
    assert np.max(np.abs(np.column_stack((old_loops - center, np.ones(len(old_loops)))) @ uv_map - old_uvs)) < 1e-6
    assert all(len(v.groups) == 1 and v.groups[0].weight == 1 for v in original.vertices)
    group_name = eye.vertex_groups[original.vertices[0].groups[0].group].name
    assert group_name == 'feeding_head'

    angles = np.arange(36) * math.tau / 36
    outline = center + radius * np.column_stack((np.cos(angles), np.sin(angles)))
    # XY of the projected triangles is (native X,Z), depth is outward native Y.
    surface = body_points[body_faces][:, :, [0, 2, 1]].copy()
    surface[:, :, 2] *= side
    area = np.cross(surface[:, 1] - surface[:, 0], surface[:, 2] - surface[:, 0])[:, 2]
    near = surface[(area * side < -1e-12) & (surface[:, :, 2].max(1) > .43)]
    projected = near[:, :, :2]
    mask = ((projected.max(1) >= outline.min(0)).all(1)
            & (projected.min(1) <= outline.max(0)).all(1))
    near = near[mask]
    points, lookup, front = [], {}, []
    support_depths = []
    area_sum = 0.0

    def point_id(point, triangle):
        key = tuple(np.rint(point * 1e8).astype(int))
        surface_depth = float(depth(triangle, point))
        if key in lookup:
            idx = lookup[key]
            assert abs(support_depths[idx] - surface_depth) < 1e-6, (eye.name, point)
            return idx
        r = float(np.linalg.norm((point - center) / radius))
        offset = .00045 + .00085 * max(0., 1. - r*r)
        idx = len(points)
        lookup[key] = idx
        points.append((float(point[0]), side * (surface_depth + offset), float(point[1])))
        support_depths.append(surface_depth)
        return idx

    for triangle in near:
        region = np.asarray(clip(list(outline), triangle[:, :2]))
        if len(region) < 3:
            continue
        polygon_area = sum(cross(a-center, b-center) for a, b in zip(region, np.roll(region, -1, 0))) * .5
        if polygon_area < 1e-12:
            continue
        area_sum += polygon_area
        boundary = list(dict.fromkeys(point_id(p, triangle) for p in region))
        middle = point_id(region.mean(0), triangle)
        # (X,Z) positive winding faces -Y in native coordinates.
        front.extend((middle, j, i) if side > 0 else (middle, i, j)
                     for i, j in zip(boundary, boundary[1:] + boundary[:1]))

    expected_area = sum(cross(a-center, b-center) for a, b in zip(outline, np.roll(outline, -1, 0))) * .5
    assert abs(area_sum - expected_area) < 1e-9, (eye.name, expected_area, area_sum)
    edge_count = Counter(tuple(sorted((a, b))) for f in front for a, b in zip(f, f[1:] + f[:1]))
    rim = [(a, b) for f in front for a, b in zip(f, f[1:] + f[:1])
           if edge_count[tuple(sorted((a, b)))] == 1]
    n = len(points)
    points += [(x, side * (d - .00095), z) for (x, _, z), d in zip(points, support_depths)]
    faces = front + [tuple(v+n for v in reversed(f)) for f in front]
    faces += [f for a, b in rim for f in [(b, a, a+n), (b, a+n, b+n)]]
    edges = Counter(tuple(sorted((a, b))) for f in faces for a, b in zip(f, f[1:] + f[:1]))
    assert set(edges.values()) == {2}
    vertices = np.asarray(points)
    assert np.min(np.linalg.norm(np.cross(vertices[np.asarray(faces)[:, 1]] - vertices[np.asarray(faces)[:, 0]],
                                         vertices[np.asarray(faces)[:, 2]] - vertices[np.asarray(faces)[:, 0]]), axis=1)) > 1e-12
    mesh = bpy.data.meshes.new(original.name + ' finite eye fit')
    mesh.from_pydata(points, [], faces)
    mesh.materials.append(original.materials[0])
    eye.data = mesh
    uv = mesh.uv_layers.new(name=original.uv_layers.active.name)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for corner_index in polygon.loop_indices:
            x, _, z = points[mesh.loops[corner_index].vertex_index]
            uv.data[corner_index].uv = np.array([x-center[0], z-center[1], 1.]) @ uv_map
    eye.vertex_groups.new(name=group_name).add(list(range(len(points))), 1., 'REPLACE')
    return {'name': eye.name, 'center_xz': center.tolist(), 'radii_xz': radius.tolist(),
            'triangles': len(faces), 'front_triangles': len(front),
            'projected_domain_area': area_sum, 'chart_fit_max_uv_error': float(
                np.max(np.abs(np.column_stack((old_loops-center, np.ones(len(old_loops)))) @ uv_map-old_uvs)))}


report = [build_eye(bpy.data.objects[name]) for name in ['Eye_left', 'Eye_right']]
corner_normals = [corner.vector.copy() for corner in body.data.corner_normals]
normal_repairs = []
for face in body.data.polygons:
    corners = list(face.loop_indices)
    average = sum((corner_normals[i] for i in corners), Vector()) / len(corners)
    direction = face.normal.dot(average)
    if direction <= 0:
        normal_repairs.append({'face': face.index, 'material': body.data.materials[face.material_index].name,
                               'vertices': list(face.vertices), 'old_normal_dot': direction})
        for i in corners:
            corner_normals[i] = face.normal.copy()
if normal_repairs:
    body.data.normals_split_custom_set(corner_normals)
triangles = 0
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
assert triangles <= 6000
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'fish.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUTPUT/'fish.glb'), export_format='GLB', export_animations=True,
                          export_yup=True, export_skins=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
data = {'model_sha256': sha(OUTPUT/'fish.glb'), 'source_sha256': sha(OUTPUT/'fish.blend'),
        'base_source_sha256': sha(R4), 'eyes': report, 'triangles': triangles,
        'body_corner_normal_repairs': normal_repairs,
        'method': 'Clip whole native eye chart to the finite triangle projection, then close along a supported perimeter.'}
(OUTPUT/'eye-authoring.validation.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
print(json.dumps(data), flush=True)
