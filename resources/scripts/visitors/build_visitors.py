#!/usr/bin/env python3
"""Build source-painted shared visitor meshes. No generated art or runtime geometry.

Run with the repository venv; --input is the accepted Foundry design sheet.
The atlas preserves each donor pixel (nearest sampling, no downsampling).
Part-specific front/side/back patches prevent facial features reaching the rear.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image


DONORS = {
    "male": {
        "face_front": (174, 600, 234, 655), "face_side": (407, 600, 443, 655),
        "face_back": (590, 602, 654, 652),
        "hair_front": (162, 576, 236, 607), "hair_side": (376, 576, 440, 604),
        "hair_back": (585, 577, 657, 625),
        "shirt_front": (167, 666, 235, 752), "shirt_side": (390, 668, 425, 752),
        "shirt_back": (585, 665, 654, 752),
        "sleeve_front": (147, 684, 169, 728), "sleeve_side": (380, 686, 406, 727),
        "sleeve_back": (566, 684, 588, 727),
        "skin_front": (148, 735, 164, 805), "skin_side": (381, 738, 400, 804),
        "skin_back": (569, 735, 583, 803),
        "pants_front": (168, 759, 197, 939), "pants_side": (173, 765, 195, 939),
        "pants_back": (588, 759, 616, 940),
        "shoe_front": (166, 944, 193, 963), "shoe_side": (383, 945, 438, 962),
        "shoe_back": (585, 944, 611, 962),
    },
    "female": {
        "face_front": (888, 601, 946, 653), "face_side": (1115, 600, 1151, 654),
        "face_back": (1290, 604, 1353, 653),
        "hair_front": (877, 578, 945, 607), "hair_side": (1084, 577, 1145, 606),
        "hair_back": (1283, 578, 1361, 652),
        "shirt_front": (879, 668, 937, 737), "shirt_side": (1101, 665, 1137, 739),
        "shirt_back": (1291, 668, 1353, 737),
        "sleeve_front": (861, 679, 880, 714), "sleeve_side": (1087, 681, 1106, 715),
        "sleeve_back": (1278, 683, 1294, 716),
        "skin_front": (860, 724, 874, 801), "skin_side": (1097, 728, 1113, 801),
        "skin_back": (1281, 726, 1295, 802),
        "pants_front": (878, 749, 906, 939), "pants_side": (883, 755, 904, 939),
        "pants_back": (1292, 749, 1319, 939),
        "shoe_front": (878, 944, 904, 963), "shoe_side": (1096, 944, 1145, 962),
        "shoe_back": (1291, 944, 1317, 962),
    },
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_sheet_background(c):
    return c[0] > 235 and c[1] > 225 and c[2] > 210 and max(c[:3]) - min(c[:3]) < 32


def atlas_from_source(source: Image.Image, out: Path):
    atlas = Image.new("RGB", (1024, 1024), (89, 64, 42))
    rects = {}
    cursor_x, cursor_y, row_height = 4, 4, 0
    filled = 0
    for gender, parts in DONORS.items():
        for part, box in parts.items():
            patch = source.crop(box).convert("RGB")
            pixels = patch.load()
            # Extend the nearest actual painted pixel across the sheet background.
            # Row-local extension retains cloth clusters and prevents cream wedges.
            valid_rows = []
            for y in range(patch.height):
                xs = [x for x in range(patch.width) if not is_sheet_background(pixels[x, y])]
                if xs:
                    valid_rows.append(y)
                    for x in range(patch.width):
                        if is_sheet_background(pixels[x, y]):
                            near = min(xs, key=lambda v: abs(v - x))
                            pixels[x, y] = pixels[near, y]
                            filled += 1
            if not valid_rows:
                raise ValueError(f"Empty donor: {gender}/{part}")
            for y in range(patch.height):
                if y not in valid_rows:
                    near = min(valid_rows, key=lambda v: abs(v - y))
                    for x in range(patch.width):
                        pixels[x, y] = pixels[x, near]
                        filled += 1
            if cursor_x + patch.width + 4 > atlas.width:
                cursor_x, cursor_y = 4, cursor_y + row_height + 8
                row_height = 0
            if cursor_y + patch.height + 4 > atlas.height:
                raise ValueError("Atlas overflow")
            atlas.paste(patch, (cursor_x, cursor_y))
            # Two texels of edge padding, still at original source resolution.
            atlas.paste(patch.crop((0, 0, 1, patch.height)).resize((2, patch.height)), (cursor_x - 2, cursor_y))
            atlas.paste(patch.crop((patch.width - 1, 0, patch.width, patch.height)).resize((2, patch.height)), (cursor_x + patch.width, cursor_y))
            atlas.paste(patch.crop((0, 0, patch.width, 1)).resize((patch.width, 2)), (cursor_x, cursor_y - 2))
            atlas.paste(patch.crop((0, patch.height - 1, patch.width, patch.height)).resize((patch.width, 2)), (cursor_x, cursor_y + patch.height))
            rects[f"{gender}/{part}"] = [cursor_x, cursor_y, patch.width, patch.height]
            cursor_x += patch.width + 8
            row_height = max(row_height, patch.height)
    atlas.save(out)
    return rects, filled


class Mesh:
    def __init__(self, gender, rects):
        self.gender, self.rects = gender, rects
        self.vertices, self.normals, self.uvs, self.uv2s, self.pivots = [], [], [], [], []

    def uv(self, part, direction, u, v):
        x, y, w, h = self.rects[f"{self.gender}/{part}_{direction}"]
        return [(x + .5 + max(0., min(1., u)) * (w - 1)) / 1024,
                (y + .5 + max(0., min(1., v)) * (h - 1)) / 1024]

    def tri(self, points, uv, limb, pivot, region):
        a, b, c = points
        ab, ac = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
        n = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
        length = math.sqrt(sum(v*v for v in n))
        if length < 1e-9:
            return
        n = [v/length for v in n]
        # Godot front faces are clockwise. Keep the geometric outward normal,
        # but emit the opposite index order from the cross-product convention.
        for p, t in zip([points[0], points[2], points[1]], [uv[0], uv[2], uv[1]]):
            self.vertices.extend(p)
            self.normals.extend(n)
            self.uvs.extend(t)
            self.uv2s.extend([limb, region])
            self.pivots.extend([pivot[0], pivot[1], pivot[2], 0.])

    def loft(self, rings, part, limb, pivot, region, sides=10, angles=None):
        """Closed faceted elliptical loft; each ring is (y, rx, rz, cx, cz)."""
        if angles is None:
            angles = [2*math.pi*i/sides for i in range(sides)]
        n = len(angles)
        rows = []
        for y, rx, rz, cx, cz in rings:
            rows.append([(cx + rx*math.sin(t), y, cz - rz*math.cos(t)) for t in angles])
        ylo, yhi = rings[0][0], rings[-1][0]
        for j in range(len(rows)-1):
            for i in range(n):
                k = (i+1) % n
                angle = (angles[i]+(angles[k] if k else 2*math.pi))/2
                sx, sz = math.sin(angle), -math.cos(angle)
                direction = ("front" if sz < 0 else "back") if abs(sz) >= abs(sx)*.85 else "side"
                ps = [rows[j][i], rows[j][k], rows[j+1][k], rows[j+1][i]]
                tex = []
                for p, ri in zip(ps, [j, j, j+1, j+1]):
                    ry, rx, rz, cx, cz = rings[ri]
                    if direction == "side":
                        u = .5 - (p[2]-cz) / max(.001, 2*rz)
                    else:
                        u = .5 + (p[0]-cx) / max(.001, 2*rx) * (1 if direction == "front" else -1)
                    tex.append(self.uv(part, direction, u, 1-(p[1]-ylo)/max(.001, yhi-ylo)))
                # Winding is clockwise for Godot front faces; normals outward.
                face_region = (3 if direction == "back" else 5) if part == "face" else region
                self.tri([ps[0], ps[2], ps[1]], [tex[0], tex[2], tex[1]], limb, pivot, face_region)
                self.tri([ps[0], ps[3], ps[2]], [tex[0], tex[3], tex[2]], limb, pivot, face_region)
        for row, r, reverse in [(rows[0], rings[0], False), (rows[-1], rings[-1], True)]:
            center = (r[3], r[0], r[4])
            for i in range(n):
                k = (i+1)%n
                ps = [center, row[k], row[i]] if reverse else [center, row[i], row[k]]
                tex = [self.uv(part, "back", .5+(p[0]-r[3])/max(.001, r[1]*2), .5+(p[2]-r[4])/max(.001, r[2]*2)) for p in ps]
                self.tri(ps, tex, limb, pivot, region)

    def build(self, child=False):
        # Heads remain proportionally larger for children; torso and legs shorten independently.
        scale_y = .66 if child else 1.
        scale_x = .77 if child else 1.
        hip = .79 * scale_y
        shoulder = 1.29 * scale_y
        head_bottom = 1.345 * scale_y
        head_height = .285 * (.85 if child else 1.)
        head_top = head_bottom + head_height
        top = head_top + .08
        limb_x = .108*scale_x
        phead = (0, head_bottom+.03, 0)
        # Trousers and shoes: thighs have volume, ankles taper, rounded shoe toes.
        for sign, limb in [(-1, 3), (1, 4)]:
            cx = sign*limb_x
            pivot = (cx, hip, 0)
            rings = [(y*scale_y, rx*scale_x, rz*scale_x, cx, z*scale_x) for y,rx,rz,z in [
                (.095,.061,.058,0),(.18,.065,.061,0),(.41,.070,.066,0),(.66,.082,.077,0),(.825,.087,.084,0)]]
            self.loft(rings, "pants", limb, pivot, 2)
            self.loft([(y*scale_y, rx*scale_x, rz*scale_x, cx, z*scale_x) for y,rx,rz,z in [
                (.018,.066,.096,-.025),(.043,.077,.117,-.035),(.085,.069,.109,-.032),(.122,.057,.070,0)]], "shoe", limb, pivot, 4)
        # Waist is a continuous shallow torso with modest shoulder broadening.
        waist = .182 if self.gender == "male" else .160
        self.loft([(y*scale_y, rx*scale_x, rz*scale_x,0,0) for y,rx,rz in [
            (.785,waist*.95,.092),(.86,waist,.101),(.99,waist*.94,.100),(1.15,waist*1.04,.112),(1.265,waist*1.08,.102),(1.315,waist*.82,.084)]],
            "shirt", 0, (0,0,0), 1, 12)
        # Neck and attached shoulder/sleeve volumes avoid hovering cylinders.
        self.loft([(1.29*scale_y,.062*scale_x,.060*scale_x,0,0),
                   (head_bottom+.033,.061*scale_x,.060*scale_x,0,0)], "skin",9,phead,0)
        for sign, limb in [(-1,1),(1,2)]:
            cx=sign*.214*scale_x
            pivot=(cx,shoulder-.025,0)
            self.loft([(y*scale_y,rx*scale_x,rz*scale_x,cx+sign*dx*scale_x,z*scale_x) for y,rx,rz,dx,z in [
                (1.035,.061,.061,.022,0),(1.10,.068,.066,.016,0),(1.235,.077,.074,.002,0),(1.285,.059,.062,-.012,0)]],
                "sleeve",limb,pivot,1)
            self.loft([(y*scale_y,rx*scale_x,rz*scale_x,cx+sign*dx*scale_x,z*scale_x) for y,rx,rz,dx,z in [
                (.755,.036,.041,.03,-.020),(.79,.043,.046,.031,-.013),(.86,.039,.044,.032,-.009),(.97,.046,.047,.025,-.002),(1.07,.050,.052,.022,0)]],
                "skin",limb,pivot,0)
            # Mitten is compact and continuous with the wrist; no separate fingers.
            self.loft([(y*scale_y,rx*scale_x,rz*scale_x,cx+sign*.03*scale_x,z*scale_x) for y,rx,rz,z in [
                (.72,.028,.032,-.023),(.74,.042,.043,-.020),(.79,.046,.046,-.019),(.825,.031,.034,-.010)]],
                "skin",limb,pivot,0)
        head_scale = .88 if child else 1.
        def hring(t,rx,rz,cz=0):
            return (head_bottom+t*head_height,rx*head_scale,rz*head_scale,0,cz*head_scale)
        self.loft([hring(t,rx,rz,cz) for t,rx,rz,cz in [
            (0,.065,.064,-.005),(.12,.100,.093,-.004),(.35,.130,.108,0),(.67,.138,.117,0),(.90,.130,.111,0),(1,.106,.095,0)]],
            "face",9,phead,0,12)
        # A rounded crown, with the long bob extending down the rear only.
        self.loft([(head_top-.065, .141*head_scale,.121*head_scale,0,.002),
                   (head_top+.015,.146*head_scale,.125*head_scale,0,.004),
                   (head_top+.065,.106*head_scale,.096*head_scale,0,.003),
                   (top,.034*head_scale,.035*head_scale,0,0)], "hair",9,phead,3,12)
        if self.gender == "female":
            # Rear bob is a separate attached shell, not a back-projected face.
            self.loft([(head_bottom-.010,.122*head_scale,.066*head_scale,0,.067*head_scale),
                       (head_bottom+.05,.153*head_scale,.080*head_scale,0,.060*head_scale),
                       (head_top-.01,.149*head_scale,.082*head_scale,0,.059*head_scale),
                       (head_top+.04,.113*head_scale,.066*head_scale,0,.052*head_scale)], "hair",9,phead,3,10)
        return {"vertices":self.vertices,"normals":self.normals,"uvs":self.uvs,"uv2s":self.uv2s,"pivots":self.pivots,
                "height":top,"triangles":len(self.vertices)//9,"surfaces":1}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--game",type=Path,required=True)
    p.add_argument("--godot",type=Path,required=True)
    args=p.parse_args()
    output=args.output.resolve(); game=args.game.resolve()
    if not output.is_relative_to(game / "assets"):
        raise ValueError("Output must be inside the specified game's assets directory")
    output.mkdir(parents=True,exist_ok=True)
    source=args.input.resolve()
    if source != output / "visitor_design_source.png":
        shutil.copyfile(source,output / "visitor_design_source.png")
    rects,filled=atlas_from_source(Image.open(source),output / "visitor_atlas.png")
    meshes={}
    for name,gender,child in [("male","male",False),("female","female",False),("boy","male",True),("girl","female",True)]:
        meshes[name]=Mesh(gender,rects).build(child)
    intermediate=output / "mesh_build.json"
    intermediate.write_text(json.dumps(meshes,separators=(",",":")))
    builder=Path(__file__).with_name("save_visitor_meshes.gd").resolve()
    log=game.parent / "output/visitors-v1/review/offline-build.log"
    log.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([str(args.godot.resolve()),"--headless","--log-file",str(log),"--path",str(game),"--script",str(builder),"--",str(output)],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    print(result.stdout.strip())
    intermediate.unlink()
    metadata={"schema_version":1,"source_sha256":digest(source),"source":str(source),"builder_sha256":digest(Path(__file__)),
              "exporter_sha256":digest(builder),"shader_sha256":digest(game / "scripts/aquarium/visitors/VisitorMaterial.gdshader"),
              "atlas_sha256":digest(output / "visitor_atlas.png"),"atlas_size":[1024,1024],"native_source_pixels":True,
              "background_texels_extended":filled,"donors":DONORS,"atlas_rects":rects,
              "meshes":{name:{k:v for k,v in mesh.items() if k in ("height","triangles","surfaces")} for name,mesh in meshes.items()},
              "shader_contract":{"forward":"-Z","feet_y":0,"INSTANCE_CUSTOM":["phase_radians","motion_blend_0_1","palette_index_0_7","older_0_1"],"clock":"crowd_time"},
              "joint_attributes":"CUSTOM0 RGBA_FLOAT; xyz=joint pivot; UV2=limb ID, material region; no vertex-color geometry encoding",
              "discarded_trial_findings":["Opposite triangle winding rendered inner rear faces: emit clockwise indices, retain outward normals.",
                  "Vertex COLOR pivot encoding caused actual GPU limbs to disconnect: replaced with float CUSTOM0, save/reload pivots verified within 1e-6m.",
                  "Source side trouser patches included hanging hands; narrow side contour created dark vertical streaks. Side trouser UV now uses an unobscured central front cloth donor; front/back donor detail preserved."],
              "visual_acceptance":"pending_user_review"}
    for name in meshes:
        path=output / f"visitor_{name}.res"
        metadata["meshes"][name]["sha256"]=digest(path)
    (output / "build_manifest.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(json.dumps({"ok":True,"meshes":metadata["meshes"],"atlas":str(output / "visitor_atlas.png")}))


if __name__ == "__main__":
    main()
