"""Sculpt a standing upturned root plate with real root passages and a rear stump."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.measure import marching_cubes

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[4]
sys.path.insert(0, str(ROOT / "resources/scripts/aquascape"))
from bake_reef_arch_six_view_art import read_donors, texture_atlas
from build_decor_ten import ray_hits
from build_from_art import Glb
from build_reef_arch_from_material_views import (
    blend_opposites, projection_reports, reduce_mesh, round_intersection, sampled_distance,
)
from build_reef_relief_set import leading_volume, topology
from validate_art_models import inspect

ID = "wood_upturned_root_plate"
SIZE = (2.35, 1.66, 1.58)
RAW = Path("projects/aquascape-e-wood-upturned-root-plate-r2/output") / (ID + "_six_views_raw.png")
BOXES = {"front":(1,43,376,324), "right":(451,43,610,325), "rear":(681,45,1056,323),
         "left":(85,401,237,687), "top":(291,437,658,680), "bottom":(678,436,1048,671)}
SPANS = {"front":SIZE[:2], "rear":SIZE[:2], "right":(SIZE[2], SIZE[1]), "left":(SIZE[2], SIZE[1]),
         "top":(SIZE[0], SIZE[2]), "bottom":(SIZE[0], SIZE[2])}

# Ribs start from the same basal knot, extend into the separately visible
# woody fingers, and sweep through different depths. Broad branches share
# contact with the root disk; tips have independent changes in direction.
RIBS = [
    [(-.14,.25,.23,.19),(-.37,.40,.30,.13),(-.65,.52,.33,.10),(-.92,.47,.24,.092),(-1.075,.40,.21,.045)],
    [(-.07,.26,.19,.18),(-.31,.54,.37,.14),(-.54,.73,.39,.091),(-.87,.78,.27,.071),(-1.06,.89,.18,.051)],
    [(-.04,.25,.12,.19),(-.27,.56,.30,.14),(-.44,.87,.31,.10),(-.74,1.01,.23,.088),(-.85,1.24,.15,.05)],
    [(-.02,.29,.04,.21),(-.21,.67,.27,.137),(-.31,1.03,.26,.10),(-.40,1.28,.17,.083),(-.42,1.52,.055,.052)],
    [(0,.30,.04,.17),(.10,.61,.21,.142),(.16,.94,.28,.102),(.23,1.28,.20,.077),(.31,1.50,.064,.043)],
    [(.05,.28,.18,.17),(.29,.57,.28,.13),(.44,.85,.32,.104),(.61,1.11,.26,.094),(.68,1.37,.14,.05)],
    [(.07,.28,.25,.19),(.32,.49,.36,.144),(.53,.64,.37,.11),(.82,.79,.29,.08),(.96,1.01,.23,.063)],
    [(.09,.25,.16,.18),(.29,.42,.28,.133),(.61,.50,.36,.092),(.84,.55,.29,.078),(1.11,.59,.19,.053)],
    [(.13,.25,.16,.16),(.41,.29,.31,.105),(.65,.26,.34,.08),(.91,.15,.31,.06),(1.04,.10,.19,.055)],
    [(-.02,.24,-.013,.19),(-.24,.47,-.22,.137),(-.42,.75,-.27,.115),(-.61,.96,-.22,.08)],
    [(.05,.21,-.05,.21),(.21,.48,-.22,.153),(.32,.76,-.26,.099),(.45,1.11,-.15,.067)],
    [(-.02,.22,-.06,.18),(-.26,.31,-.21,.13),(-.58,.38,-.28,.10),(-.92,.31,-.20,.065)],
    [(.05,.23,-.08,.18),(.33,.36,-.23,.127),(.60,.44,-.27,.10),(.90,.61,-.20,.072)],
]
# Openings follow the mirrored daylight in the broad art. Larger central
# channels are left to right and set away from the trunk shoulder.
HOLES = [("左下根环",-.682,.342,.088,.073, 29),
         ("左外根环",-.893,.798,.084,.084,-23),
         ("左上裂口",-.518,1.010,.080,.074,31),
         ("左冠根叉",-.413,1.248,.069,.093,27),
         ("中冠根叉",.081,1.254,.070,.098,-20),
         ("右腰根环",.693,.744,.114,.078,30),
         ("右外根环",.982,.754,.072,.086,39),
         ("右上根叉",.474,1.292,.068,.082,-35)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def donors():
    source = ROOT / RAW
    sheet = Image.open(source).convert("RGB")
    views, masks = {}, {}
    for view, box in BOXES.items():
        rect = np.rint(np.asarray(box) * sheet.width / 1060).astype(int)
        crop = sheet.crop(tuple(rect))
        rgb = np.asarray(crop)
        mask = (rgb.min(axis=2) < 220) & (rgb.max(axis=2) < 244)
        mask = ndi.binary_closing(mask, iterations=2)
        labels, _ = ndi.label(mask, structure=ndi.generate_binary_structure(2, 2))
        count = np.bincount(labels.ravel())
        count[0] = 0
        mask = count[labels] >= 50
        iy, ix = np.nonzero(mask)
        x0, y0, x1, y1 = int(ix.min()), int(iy.min()), int(ix.max()+1), int(iy.max()+1)
        if min(x0,y0,crop.width-x1,crop.height-y1) < 1:
            raise ValueError((view, "cropped branch end is missing"))
        art = FOLDER / (view + ".png")
        stencil = FOLDER / (view + "-outline.png")
        masks[view] = mask[y0:y1, x0:x1]
        crop.crop((x0,y0,x1,y1)).save(art, optimize=True)
        Image.fromarray(masks[view]).save(stencil, optimize=True)
        views[view] = {"path": art.name, "source_png_sha256": sha(art),
                       "outline_sha256":sha(stencil), "source_rect_raw_px":rect.tolist(),
                       "cropped_pixel_size":[x1-x0,y1-y0]}
    handoff = {
        "id": ID, "name_zh": "倒伏树盘", "geometry_budget":"wood",
        "environment":"freshwater", "nominal_xyz_m":SIZE,
        "board":str(RAW), "board_sha256":sha(source), "views":views, "user_acceptance":"pending",
        "review":"新版六面显示竖起的宽树根盘、向外分叉的老根、低基部和向后短桩。正反孔位大体对应，俯视略斜，俯仰图看木纹与横向展开；短桩深度、断面角度和净空按侧面与模型截面核对。",
    }
    (FOLDER / "material-source.handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n")
    return read_donors(FOLDER, views), masks


def wood_rib(field, xyz, rib):
    for p, q in zip(rib, rib[1:]):
        start = np.asarray(p[:3])
        delta = np.asarray(q[:3]) - start
        offset = [scale - base for scale, base in zip(xyz, start)]
        t = np.clip(sum(axis * component for axis, component in zip(offset, delta)) / np.dot(delta, delta), 0, 1)
        dx, dy, dz = [component - t * shift for component, shift in zip(offset, delta)]
        radius = p[3] + (q[3]-p[3])*t
        divide = np.hypot(dx,dy)
        angle = np.arctan2(dz, divide)
        fibers = 1 + .082 * np.cos(5*angle + 1.52*xyz[1]) + .034*np.cos(7*angle + 2.43*xyz[0])
        rib_form = radius * fibers - np.sqrt(dx*dx + dy*dy + (dz / .84)**2)
        transition = np.maximum(1.0 - abs(field - rib_form)/.035, 0.0)
        field[:] = np.maximum(field, rib_form) + .00875 * transition ** 2


def sculpt(masks):
    step = .016
    axes = [np.arange(lo, hi, step) for lo, hi in [(-1.39,1.39),(-.07,1.88),(-.98,.73)]]
    xyz = np.ix_(*axes)
    x,y,z = xyz
    f = sampled_distance(ndi.binary_fill_holes(masks["front"]), xyz, "front", SPANS)
    b = sampled_distance(ndi.binary_fill_holes(masks["rear"]), xyz, "rear", SPANS)
    silhouette = blend_opposites(f,b)
    # Shallow curved overall wafer, taper and change the axial slope around
    # the branch tips. Use the front/rear envelope as the root spacing guide.
    zmid = .02 + .14*np.cos(2.42*x)*(1-.40*y) - .115*y + .063*np.sin(5.4*x+3.3*y)
    taper = .108 + .04*np.cos(2.4*x)*np.exp(-2.5*abs(y-.27))
    plate = round_intersection(silhouette, taper-abs(z-zmid), .055)
    for rib in RIBS:
        wood_rib(plate, xyz, rib)
    plate = round_intersection(plate, silhouette + .049, .040)

    # Thick off-axis heel links fan to a short outward stump; its rear end
    # stays solid and receives rear end grain from the actual material study.
    stump_z = np.clip((z + .75)/.99, 0.0, 1.0)
    trunk_x = -.058 + .077*stump_z + .035*np.sin(3.4*stump_z)
    trunk_y = .245 - .024*stump_z
    rx = .228 + .075*stump_z**2
    ry = .205 + .062*stump_z**2
    u,w = (x-trunk_x)/rx, (y-trunk_y)/ry
    angle = np.arctan2(w, u)
    bark = (1.0 + .056*np.cos(5*angle+.9*z) + .049*np.cos(8*angle+1.8*z)) - np.hypot(u,w)
    grain_cut = -.78 + .031*np.sin(4*angle) - .020*u + .028*w
    stump = round_intersection(.19*bark, np.minimum(z-grain_cut,.30-z),.042)
    field = -round_intersection(-plate, -stump, .083)
    for _, cx, cy, sx, sy, deg in HOLES:
        rotation = np.deg2rad(deg)
        dx,dy = x-cx-.055*z,y-cy+.043*z
        a = (dx*np.cos(rotation) + dy*np.sin(rotation))/sx
        b = (dy*np.cos(rotation) - dx*np.sin(rotation))/sy
        contour = 1.0 + .095*np.cos(3*np.arctan2(b,a)+.9) - np.hypot(a,b)
        field = round_intersection(field,-contour*min(sx,sy), .025)
    ground = .040
    field = np.minimum(ndi.gaussian_filter(field, .61),y-ground)
    body, retained = leading_volume(field)
    field[(field > 0) & ~body] = -step
    field[[0,-1],:,:] = field[:,[0,-1],:] = field[:,:,[0,-1]] = -step
    v,f,_,_ = marching_cubes(field,0,spacing=(step,)*3,allow_degenerate=False)
    v += [a[0] for a in axes]
    return v,f,ground,retained


def main(blender, scratch):
    art, masks = donors()
    v,f,ground,retained = sculpt(masks)
    v,f = reduce_mesh(v,f,blender,1124)
    v[:,1] -= ground
    v[v[:,1] < .006,1] = 0
    xyz = v[f]
    cross = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
    n = np.repeat(cross/np.linalg.norm(cross,axis=1,keepdims=True),3,axis=0)
    g=Glb()
    mat=g.material(Image.new("RGBA",(4,4),(158,153,149,255)),"Neutral")
    g.mesh(v,f,np.zeros((len(v),2),dtype=np.float32),mat,ID)
    gray_path = FOLDER / (ID + "-gray.glb")
    g.save(gray_path)
    atlas,uv,weights = texture_atlas(f,xyz.reshape(-1,3),n,f.ravel(),art,SPANS,ground,True)
    atlas=atlas.resize((1536,1536),Image.Resampling.NEAREST)
    glb=Glb()
    mat=glb.material(atlas,ID+" · six-direction root wood")
    glb.mesh(xyz.reshape(-1,3),np.arange(xyz.size//3).reshape(-1,3),uv,mat,ID)
    output = FOLDER / (ID + ".glb")
    glb.save(output)
    npz = output.with_suffix(".npz")
    np.savez_compressed(npz,vertices=v,faces=f)
    shell_count,euler = topology(v,f)
    details=inspect(output)
    space = {label:ray_hits(v,f,[x,y-ground,1.3],[0,0,-1],2.6) for label,x,y,*_ in HOLES}
    center = ray_hits(v,f,[-.057,.22,-1.19],[0,0,1],2.7)
    mid = ray_hits(v,f,[.16,.91,1.10],[0,0,-1],2.5)
    rear_reach=(0.85-center[0]) if center else 0
    disk_depth=(mid[-1]-mid[0]) if len(mid)>=2 else 0
    valid = bool(details["ok"] and retained > .96 and shell_count == 1 and euler <= -4
                 and len(center) == 2 and disk_depth > .12 and rear_reach > .32
                 and sum(not h for h in space.values()) >= 5
                 and g.triangles==glb.triangles==len(f)<=1200 and all(w>.01 for w in weights.values()))
    scratch.mkdir(exist_ok=True,parents=True)
    outlines = projection_reports(v,f,masks,SPANS,ground,scratch)
    proof = {
        "id":ID, "ok":valid, "nominal_xyz_m":SIZE, "bounds_xyz_m":np.ptp(v,axis=0).tolist(),
        "triangle_budget":{"preferred":800,"hard_limit":1200,"type":"wood"}, "triangles":len(f),
        "connected_shells":shell_count, "surface_euler":euler, "retained_volume":retained,
        "open_edges":details["open_edges"],"nonmanifold_edges":details["nonmanifold_edges"],"sampler":"nearest",
        "projection_outlines":outlines, "art_texel_share":weights,"atlas_size":list(atlas.size),
        "material_passes":1, "rear_stump_ray_hits":center, "rear_stump_exposure_m":rear_reach,
        "middle_root_plate_depth_m":disk_depth,"screen_direction_openings":space,
        "glb":str(output),"glb_sha256":sha(output),"gray":str(gray_path),"gray_sha256":sha(gray_path),
        "source_handoff":str(FOLDER/"material-source.handoff.json"),
        "source_handoff_sha256":sha(FOLDER/"material-source.handoff.json"),
    }
    report = FOLDER/"geometry-and-material.validation.json"
    report.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n")
    print(ID, valid, len(f), euler, "through rays", sum(not h for h in space.values()), flush=True)
    if not valid:
        return False
    subprocess.run([str(blender),"-b","--python-exit-code","1","--python",
                    str(ROOT/"resources/scripts/aquascape/blender_reef_mesh.py"),"--",
                    str(output),"--editable-dir",str(FOLDER)], check=True)
    npz.unlink()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender",type=Path,required=True)
    parser.add_argument("--scratch",type=Path,required=True)
    args = parser.parse_args()
    raise SystemExit(not main(args.blender,args.scratch))
