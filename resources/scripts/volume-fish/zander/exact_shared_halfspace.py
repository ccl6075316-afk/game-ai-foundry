"""Strict high precision halfspace proof for a suspected shared seam contact.

This is a read-only predicate, NOT a whole fish validator. It never enlarges an
epsilon. Exact coplanar ambiguity returns not-proven and must be sent to a finite
2D clipping test. The proof is relative to the supplied binary64 coordinates.
"""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import numpy as np


def orient3d(a, b, c, d):
    # Exact binary rational signs avoid another floating/Decimal tolerance in
    # the very near-coplanar cases for which this narrow fallback is intended.
    points = [[Fraction.from_float(float(x)) for x in p] for p in [a, b, c, d]]
    u, v, w = [[points[k][i] - points[0][i] for i in range(3)] for k in [1, 2, 3]]
    return (u[0] * (v[1] * w[2] - v[2] * w[1])
            - u[1] * (v[0] * w[2] - v[2] * w[0])
            + u[2] * (v[0] * w[1] - v[1] * w[0]))


def display80(value):
    with localcontext() as ctx:
        ctx.prec = 80
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def shared_contact_halfspace(a, b):
    """Prove contact is contained in an exactly shared vertex/edge, or defer.

    Sharing an approximate point is insufficient. Coplanar triangles, duplicate
    faces and crossing configurations are never exempted by this predicate.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    assert a.shape == b.shape == (3, 3) and np.isfinite(a).all() and np.isfinite(b).all()
    assert np.max(abs(np.r_[a, b])) < 100, 'Predicate audited for local sub-100m coordinates'
    shared = [(i, j) for i in range(3) for j in range(3) if np.array_equal(a[i], b[j])]
    if len(shared) not in [1, 2] or len({i for i, _ in shared}) != len(shared) or len({j for _, j in shared}) != len(shared):
        return {'proved_legal_shared_contact': False, 'reason': 'not one exact shared vertex or edge'}
    records = []
    for label, plane, tested, shared_tested in [
            ('B against A', a, b, {j for _, j in shared}),
            ('A against B', b, a, {i for i, _ in shared})]:
        values = [orient3d(*plane, point) for point in tested]
        nonshared = [value for index, value in enumerate(values) if index not in shared_tested]
        strictly_same = all(value > 0 for value in nonshared) or all(value < 0 for value in nonshared)
        exact_shared_plane = all(values[index] == 0 for index in shared_tested)
        record = {'direction': label, 'signed_orient3d_exact_rational': list(map(str, values)),
                  'signed_orient3d_display_80digit': list(map(display80, values)),
                  'nonshared_strictly_same_side': strictly_same,
                  'shared_points_exactly_on_plane': exact_shared_plane}
        records.append(record)
        if strictly_same and exact_shared_plane:
            return {'proved_legal_shared_contact': True, 'shared_vertex_pairs': shared,
                    'proof': records, 'reason': 'Triangle can meet the other plane only on the convex hull of the exactly shared points'}
    return {'proved_legal_shared_contact': False, 'shared_vertex_pairs': shared,
            'proof': records, 'reason': 'Not proved; use finite segment/coplanar area logic, never enlarge EPS'}


def controls():
    a = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0]])
    checks = {
        'legal_point': shared_contact_halfspace(a, [[0., 0, 0], [-1, 0, 1], [0, -1, 1]])['proved_legal_shared_contact'],
        'legal_edge': shared_contact_halfspace(a, [[0., 0, 0], [1, 0, 0], [0, 1, 1]])['proved_legal_shared_contact'],
        'proper_crossing_not_exempt': not shared_contact_halfspace(a, [[0., 0, 0], [.2, .2, -1], [.2, .2, 1]])['proved_legal_shared_contact'],
        'coplanar_overlap_not_exempt': not shared_contact_halfspace(a, [[0., 0, 0], [1, 1, 0], [0, 2, 0]])['proved_legal_shared_contact'],
        'duplicate_face_not_exempt': not shared_contact_halfspace(a, a)['proved_legal_shared_contact'],
        'near_point_not_exact_seam': not shared_contact_halfspace(a, [[0., 0, 1e-14], [-1, 0, 1], [0, -1, 1]])['proved_legal_shared_contact'],
    }
    assert all(checks.values()), checks
    return checks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', required=True, type=Path, help='Minimal report with indices and posed_coordinates')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve the previous proof'
    source = json.loads(args.proof.read_text(encoding='utf-8-sig'))
    points = source['posed_coordinates']
    a, b = [np.array([points[str(index)] for index in triangle]) for triangle in source['indices']]
    result = shared_contact_halfspace(a, b)
    result.update(kind='isolated_shared_contact_halfspace_proof_not_fish_acceptance',
                  input_sha256=hashlib.sha256(args.proof.read_bytes()).hexdigest(),
                  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  source_model_sha256=source.get('model_sha256'), controls=controls())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result))
