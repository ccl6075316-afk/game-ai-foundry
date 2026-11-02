"""Read source packed skin weights without changing source meshes or UnityPy.

UnityPy 1.25.4's fourth-weight branch uses 1 - integer_sum. The packed
integer weights use units of 1/31, so the remainder is (31-sum)/31.
"""
from UnityPy.helpers.PackedBitVector import unpack_ints


def decode_compressed_skin(compressed_mesh, vertex_count):
    packed_weights = unpack_ints(compressed_mesh.m_Weights)
    packed_indices = unpack_ints(compressed_mesh.m_BoneIndices)
    weight_cursor = index_cursor = 0
    all_weights, all_indices = [], []
    for _ in range(vertex_count):
        weights, indices, integer_sum = [], [], 0
        for _ in range(3):
            value = packed_weights[weight_cursor]
            weight_cursor += 1
            indices.append(packed_indices[index_cursor])
            index_cursor += 1
            integer_sum += value
            if not 0 <= integer_sum <= 31:
                raise ValueError('Packed vertex weights exceed quantized total')
            weights.append(value / 31.0)
            if integer_sum == 31:
                break
        if integer_sum < 31:
            weights.append((31 - integer_sum) / 31.0)
            indices.append(packed_indices[index_cursor])
            index_cursor += 1
        all_weights.append(tuple(weights + [0.0] * (4 - len(weights))))
        all_indices.append(tuple(indices + [0] * (4 - len(indices))))
    if weight_cursor != len(packed_weights) or index_cursor != len(packed_indices):
        raise ValueError('Packed skin stream was not consumed exactly')
    return all_weights, all_indices
