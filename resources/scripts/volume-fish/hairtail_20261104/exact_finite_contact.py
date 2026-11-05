"""Exact finite-triangle diagnostic for an isolated shared-contact candidate.

No epsilon is used. This is not an inventory or whole-fish collision checker.
Input binary64 coordinates are converted to their exact binary rational values.
"""
from fractions import Fraction as F
import argparse
import hashlib
import json
import math
from pathlib import Path


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def blend(a, b, t):
    return tuple(x+t*(y-x) for x, y in zip(a, b))


def normal(t):
    return cross(sub(t[1], t[0]), sub(t[2], t[0]))


def in_triangle(p, t, n):
    return all(dot(cross(sub(t[(i+1) % 3], t[i]), sub(p, t[i])), n) >= 0 for i in range(3))


def plane_edge_points(triangle, plane, n):
    points = set()
    for i in range(3):
        a, b = triangle[i], triangle[(i+1) % 3]
        da, db = dot(n, sub(a, plane[0])), dot(n, sub(b, plane[0]))
        if da == 0:
            points.add(a)
        if db == 0:
            points.add(b)
        if da*db < 0:
            points.add(blend(a, b, da/(da-db)))
    return points


def coplanar_clip(a, b, n):
    drop = max(range(3), key=lambda i: abs(n[i]))
    axes = [i for i in range(3) if i != drop]

    def area2(p, q, r):
        i, j = axes
        return (q[i]-p[i])*(r[j]-p[j])-(q[j]-p[j])*(r[i]-p[i])

    sign = 1 if area2(*b) > 0 else -1
    polygon = list(a)
    for k in range(3):
        if not polygon:
            break
        clipped = []
        for i in range(len(polygon)):
            start, end = polygon[i-1], polygon[i]
            ds, de = sign*area2(b[k], b[(k+1) % 3], start), sign*area2(b[k], b[(k+1) % 3], end)
            if (ds >= 0) != (de >= 0):
                clipped.append(blend(start, end, ds/(ds-de)))
            if de >= 0:
                clipped.append(end)
        polygon = clipped
    return set(polygon)


def classify(a, b):
    triangles = []
    for t in (a, b):
        assert len(t) == 3 and all(len(p) == 3 for p in t)
        assert all(math.isfinite(float(x)) and abs(float(x)) < 100 for p in t for x in p)
        triangles.append(tuple(tuple(F.from_float(float(x)) for x in p) for p in t))
    a, b = triangles
    na, nb = normal(a), normal(b)
    assert any(na) and any(nb), 'Degenerate triangles require a separate geometry failure'
    shared = set(a) & set(b)
    if len(shared) not in (1, 2):
        return {'proved_legal_shared_contact': False, 'reason': 'Not exactly one shared vertex or edge'}
    coplanar = all(dot(na, sub(p, a[0])) == 0 for p in b)
    if coplanar:
        points = coplanar_clip(a, b, na)
    else:
        points = {p for p in plane_edge_points(b, a, na) if in_triangle(p, a, na)}
        points |= {p for p in plane_edge_points(a, b, nb) if in_triangle(p, b, nb)}

    def on_shared(p):
        if len(shared) == 1:
            return p in shared
        q, r = sorted(shared)
        direction, delta = sub(r, q), sub(p, q)
        return not any(cross(direction, delta)) and 0 <= dot(delta, direction) <= dot(direction, direction)

    outside = [p for p in points if not on_shared(p)]
    assert points and shared <= points
    return {'proved_legal_shared_contact': not outside,
            'reason': 'Exact finite intersection is confined to shared vertex/edge' if not outside else 'Exact finite intersection extends beyond shared vertex/edge',
            'coplanar': coplanar, 'intersection_points_exact_rational': [[str(x) for x in p] for p in sorted(points)],
            'intersection_points_m': [[float(x) for x in p] for p in sorted(points)],
            'maximum_distance_from_shared_vertex_m': max(min(math.dist(tuple(map(float, p)), tuple(map(float, q))) for q in shared) for p in points)}


def controls():
    a = [[0., 0, 0], [1, 0, 0], [0, 1, 0]]
    cases = {
        'legal_vertex': (a, [[0., 0, 0], [-1, 0, 1], [0, -1, 1]], True),
        'legal_edge': (a, [[0., 0, 0], [1, 0, 0], [0, 1, 1]], True),
        'proper_crossing': (a, [[0., 0, 0], [.2, .2, -1], [.2, .2, 1]], False),
        'coplanar_area': (a, [[0., 0, 0], [1, 1, 0], [0, 2, 0]], False),
        'coplanar_legal_edge': (a, [[0., 0, 0], [1, 0, 0], [0, -1, 0]], True),
        'coplanar_legal_vertex': (a, [[0., 0, 0], [-1, 0, 0], [0, -1, 0]], True),
        'duplicate_not_exempt': (a, a, False),
        'tiny_coplanar_overlap': (a, [[0., 0, 0], [1e-14, 0, 0], [0, 1e-14, 0]], False),
    }
    results = {name: classify(x, y)['proved_legal_shared_contact'] == expected for name, (x, y, expected) in cases.items()}
    assert all(results.values()), results
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve prior diagnostic'
    source = json.loads(args.input.read_text(encoding='utf-8-sig'))
    results = {}
    for name, data in source['datasets'].items():
        triangles = [[data['posed_coordinates'][str(i)] for i in t] for t in data['indices']]
        results[name] = classify(*triangles)
    report = {'kind': 'isolated_exact_finite_shared_contact_diagnostic_not_whole_fin_acceptance',
              'model_sha256': source['model_sha256'], 'pose': source['pose'], 'triangle_indices': source['triangle_indices'],
              'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'datasets': results,
              'controls': controls(), 'scope': 'Exact rational finite segments and coplanar clipping, no epsilon or geometry edits.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'path': str(args.output), 'results': {k: {'proved_legal_shared_contact': v['proved_legal_shared_contact'], 'distance_m': v.get('maximum_distance_from_shared_vertex_m')} for k, v in results.items()}, 'controls': report['controls']}))
