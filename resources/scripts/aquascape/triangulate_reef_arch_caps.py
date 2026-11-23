"""Run Blender's constrained triangulation on the front and rear arch profiles."""

import sys

import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


path = sys.argv[sys.argv.index("--") + 1]
data = np.load(path)
result = {}
for end in ("rear", "front"):
    points = data[end]
    boundary = list(range(int(data["boundary_count"])))
    vertices, _, faces, origins, _, _ = delaunay_2d_cdt(
        [Vector(point[:2]) for point in points], [], [boundary], 1, 1e-7
    )
    assert len(vertices) == len(points)
    assert all(len(group) == 1 for group in origins)
    mapping = np.array([group[0] for group in origins])
    result[end] = mapping[np.asarray(faces)]
np.savez(path, **result)
