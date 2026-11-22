"""Bake six unlit projections of the release croaker for the ocean-school LODs."""
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt


def bake(source: Path, destination: Path):
    data = source.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + length])
    binary = memoryview(data)[28 + length:]

    def view(index):
        v = gltf["bufferViews"][index]
        start = v.get("byteOffset", 0)
        return binary[start:start + v["byteLength"]]

    def accessor(index):
        a = gltf["accessors"][index]
        dtype = {5126: "<f4", 5123: "<u2", 5125: "<u4"}[a["componentType"]]
        dim = {"VEC2": 2, "VEC3": 3, "SCALAR": 1}[a["type"]]
        return np.frombuffer(view(a["bufferView"]), dtype, a["count"] * dim,
                             a.get("byteOffset", 0)).reshape(-1, dim)

    surfaces = []
    for primitive in gltf["meshes"][0]["primitives"]:
        attr = primitive["attributes"]
        material = gltf["materials"][primitive["material"]]
        tex = material["pbrMetallicRoughness"]["baseColorTexture"]["index"]
        image = gltf["images"][gltf["textures"][tex]["source"]]
        albedo = np.asarray(Image.open(io.BytesIO(view(image["bufferView"]))).convert("RGBA"))
        surfaces.append((accessor(attr["POSITION"]), accessor(attr["TEXCOORD_0"]),
                         accessor(primitive["indices"]).reshape(-1, 3), material, albedo))

    positions = np.concatenate([s[0] for s in surfaces])
    minimum, extent = positions.min(0), np.ptp(positions, axis=0)
    width, height = 512, 256
    atlas = Image.new("RGB", (2 * width, 3 * height))
    # Rows are side, dorsal/ventral and head/tail. Columns face +axis and -axis.
    for row, (u, v, depth) in enumerate([(0, 1, 2), (0, 2, 1), (2, 1, 0)]):
        for column, sign in enumerate((1, -1)):
            rgb = np.zeros((height, width, 3), np.uint8)
            zbuf = np.full((height, width), -np.inf)
            for xyz, uv, triangles, material, albedo in surfaces:
                frac = (xyz - minimum) / extent
                xy = np.column_stack((frac[:, u] * (width - 1), (1 - frac[:, v]) * (height - 1)))
                for tri in triangles:
                    normal = np.cross(xyz[tri[1]] - xyz[tri[0]], xyz[tri[2]] - xyz[tri[0]])
                    if not material.get("doubleSided", False) and normal[depth] * sign <= 0:
                        continue
                    a, b, c = xy[tri]
                    lo = np.floor(xy[tri].min(0)).astype(int).clip(0, [width-1, height-1])
                    hi = np.ceil(xy[tri].max(0)).astype(int).clip(0, [width-1, height-1])
                    x0, y0 = lo
                    x1, y1 = hi + 1
                    y, x = np.mgrid[y0:y1, x0:x1]
                    ab, ac = b-a, c-a
                    area = ab[0]*ac[1] - ab[1]*ac[0]
                    if abs(area) < 1e-6:
                        continue
                    wb = ((x-a[0])*ac[1] - (y-a[1])*ac[0]) / area
                    wc = (ab[0]*(y-a[1]) - ab[1]*(x-a[0])) / area
                    weights = np.stack((1-wb-wc, wb, wc), axis=-1)
                    z = weights @ xyz[tri, depth] * sign
                    visible = (weights.min(-1) >= -1e-5) & (z > zbuf[y0:y1, x0:x1])
                    if not visible.any():
                        continue
                    h, w = albedo.shape[:2]
                    pixels = ((weights @ uv[tri]) * [w,h]).astype(int).clip(0, [w-1,h-1])
                    colour = albedo[pixels[:,:,1], pixels[:,:,0]]
                    if material.get("alphaMode") == "MASK":
                        visible &= colour[:,:,3] >= 255 * material.get("alphaCutoff", .5)
                    zbuf[y0:y1,x0:x1][visible] = z[visible]
                    rgb[y0:y1,x0:x1][visible] = colour[:,:,:3][visible]
            # The mesh supplies the proxy silhouette. Pad its UV border with the
            # nearest actual pigment for positions displaced by simplification.
            nearest = distance_transform_edt(~np.isfinite(zbuf), return_distances=False,
                                             return_indices=True)
            atlas.paste(Image.fromarray(rgb[tuple(nearest)]), (column*width, row*height))
    atlas.save(destination)


if __name__ == "__main__":
    assets = Path(__file__).resolve().parents[3] / "projects/fishing-2d/game/assets/models/fish"
    bake(assets / "yellow_croaker.glb", assets / "yellow_croaker_school_views.png")
