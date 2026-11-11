"""Bake the reviewed finless donor and accepted fin art into native UV charts."""
from pathlib import Path
import argparse
import copy
import hashlib
import io
import json
import sys

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
sys.path.insert(0, str(ROOT / "resources/scripts/volume-fish/portable"))
sys.path.insert(0, str(ROOT / "resources/scripts/volume-fish"))
from glb_io import arrays, read_glb, sha
from patch_existing_fin_meshes import write

BASE = ROOT / "projects/fishing-2d/game/assets/models/fish/yellow_croaker.glb"
FIN_POLYGONS = {
    "Anal": [(460,562),(496,556),(551,575),(603,593),(555,616),(489,646),(479,629),(464,595)],
    "Caudal": [(128,470),(246,392),(276,420),(303,447),(303,519),(274,537),(250,561)],
    "Dorsal": [(406,415),(470,370),(541,339),(608,315),(662,315),(715,334),(759,347),(780,329),(842,256),(873,266),(880,253),(915,283),(974,345),(828,345),(710,362),(590,389),(471,416)],
    "Pectoral": [(888,476),(919,476),(979,480),(1040,498),(1086,516),(1057,540),(1037,552),(991,550),(950,532),(925,510)],
    "Pelvic": [(1000,603),(1032,604),(1014,628),(991,653),(949,686),(899,706),(906,681),(908,655),(930,626)],
}

def smooth(value):
    x = np.clip(value, 0, 1)
    return x*x*(3-2*x)

def read_image(path):
    return np.asarray(Image.open(path).convert("RGBA"))

def biggest_component(mask):
    contours, _ = cv2.findContours(mask.astype("uint8"), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros(mask.shape, "uint8")
    cv2.drawContours(filled, [max(contours, key=cv2.contourArea)], -1, 1, -1)
    return filled.astype(bool)

def foreground(image):
    corners = np.array([image[0,0,:3], image[-1,0,:3], image[0,-1,:3], image[-1,-1,:3]])
    bg = np.median(corners, axis=0)
    return np.linalg.norm(image[:,:,:3].astype("float32") - bg, axis=2) > 40

def columns(mask):
    row, col = np.nonzero(mask)
    x = np.unique(col)
    lo = np.full(mask.shape[1], np.inf)
    hi = np.full(mask.shape[1], -np.inf)
    np.minimum.at(lo, col, row)
    np.maximum.at(hi, col, row)
    return (x[0], x[-1], np.interp(np.arange(len(lo)), x, lo[x]), np.interp(np.arange(len(hi)), x, hi[x]))

class Donor:
    def __init__(self, image, mask, grid=1):
        self.image = image
        self.bounds = columns(mask)
        self.grid = grid
        self.distance, self.nearest = distance_transform_edt(~mask, return_indices=True)
        self.count = 0
        self.fallback = 0

    def sample(self, x, y):
        height, width = self.image.shape[:2]
        ix = np.clip(np.rint(x/self.grid).astype(int)*self.grid, 0, width-1)
        iy = np.clip(np.rint(y/self.grid).astype(int)*self.grid, 0, height-1)
        self.count += len(ix)
        self.fallback += int(np.count_nonzero(self.distance[iy, ix]))
        sy, sx = self.nearest[:, iy, ix]
        return self.image[sy, sx, :3].astype(float)

def project(points, view):
    x = (points[:,0]+.51)*1700
    vertical = -points[:,1] if view == "side" else points[:,2]
    return np.c_[x, (vertical+.23)*1700]

def silhouette(patches, view):
    mask = np.zeros((800, 1800), "uint8")
    for part in patches:
        coords = np.rint(project(part["pos"], view)).astype(int)
        for tri in part["faces"]:
            cv2.fillConvexPoly(mask, coords[tri], 1)
    return columns(mask)

def map_columns(points, view, target, donor, vertical_margin):
    xy = project(points, view)
    lx, rx, top, bottom = target
    sx0, sx1, stop, sbottom = donor.bounds
    if view == "side":
        # Main scale field follows the actual caudal stalk, gill crest and snout stations.
        x = np.interp(xy[:,0], [lx, (.51-.29)*1700, (.51+.29)*1700, rx],
                      [sx0, sx0+75, 1120, sx1]) if sx1 > 1300 and sx0 > 200 else sx0+(xy[:,0]-lx)/(rx-lx)*(sx1-sx0)
    else:
        # Use torso-only color in the direction sheets. The generated anterior
        # has side-view eyes/gill details, unsuitable for median dorsal/chin skin.
        x = np.interp(xy[:,0], [lx, (.51+.27)*1700, rx],
                      [sx0, sx0+.81*(sx1-sx0), sx0+.855*(sx1-sx0)])
    ix = np.clip(np.rint(xy[:,0]).astype(int), 0, len(top)-1)
    source_ix = np.clip(np.rint(x).astype(int), 0, len(stop)-1)
    fraction = np.clip((xy[:,1]-top[ix])/np.maximum(1, bottom[ix]-top[ix]), 0, 1)
    fraction = vertical_margin + fraction*(1-2*vertical_margin)
    y = stop[source_ix]+fraction*(sbottom[source_ix]-stop[source_ix])
    return donor.sample(x, y)

def image_id(doc, primitive):
    material = doc["materials"][primitive["material"]]
    texture = material["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    return doc["textures"][texture]["source"]

def read_parts(doc, blob):
    parts = []
    for node in doc["nodes"]:
        if "mesh" not in node:
            continue
        for primitive in doc["meshes"][node["mesh"]]["primitives"]:
            attribs = primitive["attributes"]
            parts.append(dict(
                node=node["name"], material=doc["materials"][primitive["material"]]["name"],
                image=image_id(doc, primitive), pos=arrays(doc, blob, attribs["POSITION"]),
                uv=arrays(doc, blob, attribs["TEXCOORD_0"]), norm=arrays(doc, blob, attribs["NORMAL"]),
                faces=arrays(doc, blob, primitive["indices"]).reshape(-1,3),
            ))
    return parts

def raster(uv, width, height, pad):
    vertices = uv*[width,height]-.5
    origin = np.maximum(np.floor(vertices.min(0)-pad).astype(int), 0)
    end = np.minimum(np.ceil(vertices.max(0)+pad).astype(int), [width-1,height-1])
    xx, yy = np.meshgrid(np.arange(origin[0], end[0]+1), np.arange(origin[1], end[1]+1))
    points = np.c_[xx.ravel(), yy.ravel()]
    basis = np.column_stack((vertices[1]-vertices[0], vertices[2]-vertices[0]))
    if abs(np.linalg.det(basis)) < 1e-9:
        return points[:0], np.empty((0,3)), np.empty(0)
    ab = (points-vertices[0]) @ np.linalg.inv(basis).T
    beta = np.c_[1-ab.sum(1), ab]
    inside = beta.min(1) >= -1e-7
    if pad == 0:
        return points[inside], beta[inside], np.ones(int(inside.sum()))
    distance = np.full(len(points), np.inf)
    for start, end in zip(vertices, np.roll(vertices, -1, axis=0)):
        edge = end-start
        t = np.clip(((points-start)*edge).sum(1)/max(edge@edge, 1e-20), 0, 1)
        distance = np.minimum(distance, np.linalg.norm(points-(start+t[:,None]*edge), axis=1))
    keep = inside | (distance <= pad)
    bary = np.maximum(beta[keep],0)
    return points[keep], bary/bary.sum(1)[:,None], np.where(inside[keep],2,1/(1+distance[keep]))

def export_image_candidate(doc, blob, out, written):
    new = copy.deepcopy(doc)
    buffer = bytearray(blob)
    for idx, path in written.items():
        buffer.extend(b"\0" * (-len(buffer)%4))
        image = path.read_bytes()
        new["images"][idx]["bufferView"] = len(new["bufferViews"])
        new["bufferViews"].append(dict(buffer=0, byteOffset=len(buffer), byteLength=len(image)))
        buffer.extend(image)
    new["buffers"][0]["byteLength"] = len(buffer)
    write(out, new, buffer)

def load_image_chart(doc, blob, idx):
    view = doc["bufferViews"][doc["images"][idx]["bufferView"]]
    offset = view.get("byteOffset",0)
    return np.array(Image.open(io.BytesIO(blob[offset:offset+view["byteLength"]])).convert("RGBA"))

def digest(array):
    return hashlib.sha256(array.tobytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["body","fins"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--body-checkpoint", type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(WORK) and not out.exists()
    manifest = json.loads((WORK/"manifest.json").read_text())
    assert sha(BASE) == manifest["baseline"]["model_sha256"]
    assert manifest["source_generation"]["user_acceptance"] == "accepted"
    source = BASE if args.stage == "body" else args.body_checkpoint/"fish.glb"
    if args.stage == "fins":
        receipt = json.loads((args.body_checkpoint/"body-review.validation.json").read_text())
        assert receipt["ok"] and receipt["model_sha256"] == sha(source)
    doc, blob = read_glb(source)
    parts = read_parts(doc, blob)
    body = [part for part in parts if part["node"] == "Closed_body"]
    body_images = {part["image"] for part in parts if part["node"] == "Closed_body" or part["node"].startswith("Native_eye")}
    fin_images = set(range(len(doc["images"])))-body_images
    out.mkdir()
    original = {i:load_image_chart(doc, blob, i) for i in range(len(doc["images"]))}
    result = {i:im.copy() for i,im in original.items()}
    weights = {i:np.zeros(im.shape[:2], dtype="float32") for i,im in original.items()}
    protected = {}
    donors = {}
    targets = {}
    if args.stage == "body":
        art = read_image(WORK/"body-side-v1.png")
        sheet = read_image(WORK/"body-top-bottom-v1.png")
        mid = len(sheet)//2
        for key, image in [("side",art), ("top",sheet[:mid]), ("bottom",sheet[mid:])]:
            mask = biggest_component(foreground(image))
            mask = cv2.erode(mask.astype("uint8"), np.ones((5,5),"uint8")).astype(bool)
            donors[key] = Donor(image,mask,grid=2)
            targets[key] = silhouette(body, key)
        for part in parts:
            if part["material"] != "Front mouth oral chart" and not part["node"].startswith("Native_eye"):
                continue
            idx = part["image"]
            height,width = original[idx].shape[:2]
            domain = protected.setdefault(idx, np.zeros((height,width),bool))
            for tri in part["faces"]:
                pixels,_,_ = raster(part["uv"][tri],width,height,1.5)
                domain[pixels[:,1],pixels[:,0]] = True
    else:
        art = read_image(WORK/"style-concept-v1.png")
        for name, poly in FIN_POLYGONS.items():
            mask = np.zeros(art.shape[:2], "uint8")
            cv2.fillPoly(mask,[np.array(poly)],1)
            mask = mask.astype(bool) & foreground(art)
            mask = cv2.erode(mask.astype("uint8"), np.ones((5,5),"uint8")).astype(bool)
            donors[name] = Donor(art,mask,grid=2)
        for part in parts:
            if part["image"] in fin_images:
                targets[part["node"]] = silhouette([part],"side")

    records = []
    for part in parts:
        idx = part["image"]
        if args.stage == "body":
            if part["node"] != "Closed_body" or part["material"] == "Front mouth oral chart":
                continue
        elif idx not in fin_images:
            continue
        atlas = result[idx]
        height, width = atlas.shape[:2]
        count = 0
        for tri in part["faces"]:
            pixels, beta, rank = raster(part["uv"][tri],width,height,1.25)
            x,y = pixels.T
            keep = rank > weights[idx][y,x]
            if idx in protected:
                keep &= ~protected[idx][y,x]
            if args.stage == "fins":
                keep &= original[idx][y,x,3] > 0
            x,y,beta,rank = x[keep],y[keep],beta[keep],rank[keep]
            if not len(x):
                continue
            pos = beta @ part["pos"][tri]
            old = original[idx][y,x,:3].astype(float)
            if args.stage == "body":
                normals = beta @ part["norm"][tri]
                normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-7)
                side = map_columns(pos,"side",targets["side"],donors["side"],.035)
                top = map_columns(pos,"top",targets["top"],donors["top"],.05)
                bottom = map_columns(pos,"bottom",targets["bottom"],donors["bottom"],.06)
                top_mix = smooth((normals[:,1]-.53)/.42)
                bottom_mix = smooth((-normals[:,1]-.54)/.41)
                mapped = side*(1-top_mix-bottom_mix)[:,None]+top*top_mix[:,None]+bottom*bottom_mix[:,None]
                # Keep the real eye surround, chin, lip rim and front chart colors.
                strength = 1-smooth((pos[:,0]-.295)/.105)
                # Preserve original body-to-fin tissue match at the actual caudal stalk cutoff.
                strength *= smooth((pos[:,0]+.361)/.034)
                color = old+(mapped-old)*strength[:,None]
                anterior = smooth((pos[:,0]-.27)/.06) * (1-smooth((pos[:,0]-.462)/.018))
                central = 1-smooth((np.abs(pos[:,2])-.018)/.022)
                roof = anterior*central*top_mix*smooth((pos[:,1]-.022)/.028)*.77
                chin = anterior*central*bottom_mix*smooth((-.046-pos[:,1])/.018)*.66
                color = color*(1-roof-chin)[:,None]+top*roof[:,None]+bottom*chin[:,None]
            else:
                category = part["node"].split("_")[0]
                donor = donors[category]
                points = project(pos,"side")
                x0,x1,t0,t1 = targets[part["node"]]
                sx0,sx1,s0,s1 = donor.bounds
                tx = np.clip(np.rint(points[:,0]).astype(int),0,len(t0)-1)
                u = np.clip((points[:,0]-x0)/max(1,x1-x0),0,1)
                sx = sx0+u*(sx1-sx0)
                ix = np.rint(sx).astype(int)
                v = np.clip((points[:,1]-t0[tx])/np.maximum(1,t1[tx]-t0[tx]),.02,.98)
                mapped = donor.sample(sx,s0[ix]+v*(s1[ix]-s0[ix]))
                strength = np.full(len(x),.87)
                if category == "Caudal":
                    # Keep the old tissue on the cap and native stalk join.
                    strength *= 1-smooth((pos[:,0]+.412)/.044)
                color = old+(mapped-old)*strength[:,None]
            atlas[y,x,:3] = np.rint(np.clip(color,0,255)).astype("uint8")
            weights[idx][y,x] = rank
            count += len(x)
        records.append(dict(mesh=part["node"], material=part["material"], image=idx, raster_samples=count))

    written = {}
    for idx, atlas in result.items():
        assert np.array_equal(original[idx][:,:,3], atlas[:,:,3])
        if idx in protected:
            assert np.array_equal(original[idx][protected[idx]], atlas[protected[idx]])
        if np.array_equal(original[idx],atlas):
            continue
        assert idx in (body_images if args.stage=="body" else fin_images)
        path = out/f"image-{idx}.png"
        Image.fromarray(atlas).save(path)
        written[idx] = path

    candidate = out/"fish.glb"
    export_image_candidate(doc,blob,candidate,written)
    check,check_blob = read_glb(candidate)
    for key in ["meshes","nodes","skins","animations","materials","textures","samplers","accessors"]:
        assert check[key] == doc[key]
    for idx in range(len(doc["accessors"])):
        before = arrays(doc,blob,idx)
        after = arrays(check,check_blob,idx)
        assert np.isfinite(after).all() and before.tobytes()==after.tobytes()
    whole_body = {str(i):digest(result[i]) for i in sorted(body_images)}
    if args.stage == "fins":
        assert whole_body == {str(i):digest(original[i]) for i in sorted(body_images)}
        assert whole_body == json.loads((args.body_checkpoint/"bake.validation.json").read_text())["body_rgba"]
    proof = dict(ok=True, stage=args.stage, species="yellow_croaker", model_sha256=sha(candidate),
                 source_model_sha256=sha(source), nonimage_accessors_exact=len(doc["accessors"]),
                 body_rgba=whole_body, materials_alpha_and_order_exact=True, body_frozen=(args.stage=="fins"),
                 protected_rgba_texels={str(i):int(mask.sum()) for i,mask in protected.items()},
                 changed_images={str(i):dict(path=str(p),sha256=sha(p),rgba_sha256=digest(result[i]),
                                            changed_rgb_texels=int(np.count_nonzero(np.any(original[i][:,:,:3]!=result[i][:,:,:3],axis=2))))
                                 for i,p in written.items()},
                 parts=records, donor_sample_counts={key:[donor.count,donor.fallback] for key,donor in donors.items()},
                 scope="Image RGB only. Geometry and logical parts frozen. Source art is an aesthetic donor.")
    (out/"bake.validation.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({"ok":True,"stage":args.stage,"changed_images":len(written),"model_sha256":proof["model_sha256"]}))

if __name__ == "__main__":
    main()
