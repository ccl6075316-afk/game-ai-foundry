"""Build freshwater props from the six material views and authored wood volumes."""

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

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "resources/scripts/aquascape"))
from bake_reef_arch_six_view_art import read_donors, texture_atlas
from build_decor_ten import ray_hits
from build_from_art import Glb
from build_reef_arch_from_material_views import reduce_mesh
from build_reef_relief_set import topology
from validate_art_models import inspect

BATCH = ROOT / "resources/aquascape/reef-expansion-20261123/freshwater-e"
FOLDERS = {
    "wood_hollow_tunnel": {
        "front": (15, 152, 580, 415), "right": (659, 156, 910, 416), "rear": (972, 156, 1525, 420),
        "left": (63, 623, 308, 900), "top": (385, 641, 976, 875), "bottom": (996, 638, 1528, 911),
    },
    "wood_overhang_perch": {
        "front":(7,104,622,414), "right":(622,110,913,412), "rear":(914,116,1530,416),
        "left":(78,614,382,929), "top":(490,606,1029,930), "bottom":(1051,630,1531,917),
    },
    "wood_low_root_weave": {
        "front":(8,168,601,391), "right":(640,164,898,391), "rear":(940,169,1529,391),
        "left":(21,645,317,884), "top":(348,609,921,956), "bottom":(966,613,1529,962),
    },
}
AXES = {
    "front": (0, 1), "rear": (0, 1), "right": (2, 1), "left": (2, 1), "top": (0, 2), "bottom": (0, 2),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def views(asset_id, size, folder, config):
    source = BATCH.parent / "sources" / ("aquascape-e-" + asset_id.replace("_", "-")) / "output" / (asset_id + "_six_views_raw.png")
    board = Image.open(source).convert("RGB")
    cuts = {}
    spans = {}
    for view, rect in config.items():
        crop = board.crop(rect)
        colors = np.asarray(crop)
        stencil = (colors.min(axis=2) < 215) & (colors.max(axis=2) - colors.min(axis=2) > 15)
        stencil = ndi.binary_closing(stencil, iterations=2)
        labels, _ = ndi.label(stencil)
        counts = np.bincount(labels.ravel())
        counts[0] = 0
        stencil &= counts[labels] >= 50
        rows, cols = stencil.nonzero()
        bounds = min(cols), min(rows), max(cols)+1, max(rows)+1
        art = folder / (view + ".png")
        mask = folder / (view + "-outline.png")
        crop.crop(bounds).save(art, optimize=True)
        x0,y0,x1,y1 = bounds
        Image.fromarray(stencil[y0:y1, x0:x1]).save(mask, optimize=True)
        cuts[view] = {"path":art.name, "source_png_sha256":digest(art), "outline_sha256":digest(mask),
                      "source_rect":list(rect), "stencil_bbox":list(map(int, bounds))}
        spans[view] = [size[i] for i in AXES[view]]
    doc = {"id":asset_id, "board":str(source.relative_to(ROOT)), "board_sha256":digest(source), "views":cuts,
           "art_review":"Six views inspected. Some elevations show part of the oblique natural cut near a broken edge.",
           "user_acceptance":"pending"}
    (folder / "material-source.handoff.json").write_text(json.dumps(doc,indent=2)+"\n")
    donors = read_donors(folder, cuts)
    if asset_id == "wood_hollow_tunnel":
        # Generated broad views lean enough to see a broken end. End grain belongs
        # on the rims, so patch only that unobservable side strip with nearby bark.
        for view, mirrored, fraction in (("front", False, .20), ("rear", True, .205), ("top", False, .13)):
            pixels, distance = donors[view]
            if mirrored:
                pixels, distance = pixels[:, ::-1], distance[:, ::-1]
            edge = round(pixels.shape[1] * fraction)
            pixels[:, :edge] = pixels[:, edge:2*edge][:, ::-1]
    return donors, spans

def hollow_log():
    # The dark circles in both end views mark the actual continuous bore.
    # Dimensions and offsets derive from the broad body / end grain and sculpted flutes.
    count = 22
    angular = np.arange(count) * 2*np.pi / count
    end_break = .041*np.sin(5*angular+.44) + .042*np.cos(8*angular-.5) + .020*np.sin(3*angular)
    vertices = []
    rag = [(-1.35,.48,-.035,.405,.494),(-1.24,.467,-.04,.382,.469),(-1.05,.446,-.036,.353,.434),
           (-.80,.423,-.016,.326,.391),(-.54,.401,-.001,.317,.363),(-.22,.405,.020,.314,.365),
           (.12,.410,.037,.322,.365),(.42,.431,.05,.330,.391),(.74,.443,.057,.360,.398),
           (1.02,.454,.058,.373,.418),(1.24,.453,.056,.393,.433),(1.34,.472,.049,.383,.447)]
    for index,(x,cy,cz,ry,rz) in enumerate(rag):
        yshape = (1+.045*np.sin(3*angular + x*.8) + .066*np.cos(6*angular + x*.55)+ .054*np.sin(9*angular + x*.87))
        zshape = (1+.05*np.sin(4*angular - x*.63) + .083*np.cos(7*angular - x*.72))
        py = cy+ry*np.sin(angular)*yshape
        pz = cz+rz*np.cos(angular)*zshape
        px = np.full(count,x)
        strength = np.clip((abs(x)-.92)/.42,0,1)
        px += end_break*strength
        py += strength*.092*np.exp(-4*(np.angle(np.exp(1j*(angular - 1.12)))/.6)**2) * (.6 if x < 0 else 1)
        py[(py<.08)&(abs(x)>0.92)] = .075
        vertices.append(np.c_[px,py,pz])
    inner = [(1.30,.458,.04,.272,.301),(1.04,.452,.048,.245,.282),(.68,.430,.056,.228,.250),
             (.24,.425,.039,.212,.236),(-.24,.419,.020,.218,.243),(-.63,.425,.005,.223,.250),
             (-.98,.454,-.018,.252,.264),(-1.31,.47,-.031,.280,.293)]
    for x,cy,cz,ry,rz in inner:
        circ = 1+.048*np.sin(5*angular+1.1+x*.9)+.06*np.cos(7*angular-.7)
        px = np.full(count,x) + end_break * np.clip((abs(x)-1.0)/.30,0,1)
        vertices.append(np.c_[px,cy+ry*np.sin(angular)*circ,cz+rz*np.cos(angular)*circ])
    faces = []
    inner_faces = []
    for i in range(len(vertices)):
        next_ring = (i+1) % len(vertices)
        for j in range(count):
            k = (j+1) % count
            a,b,c,d = i*count+j, i*count+k, next_ring*count+j, next_ring*count+k
            if len(rag) <= i < len(vertices)-1:
                inner_faces.extend((len(faces),len(faces)+1))
            faces.extend(((a,b,c),(b,d,c)))
    # Winding of the ring creates inward normals on the bore and outward normals on the bark.
    return np.vstack(vertices).astype(np.float32), np.asarray(faces)[:,[0,2,1]], np.asarray(inner_faces)

WOOD_PATHS = {
    # Each row is one sweep: X, Y, Z and taper radius in meters.
    "wood_overhang_perch": [
        [(-1.31,.13,.51,.15),(-1.05,.28,.34,.19),(-.74,.49,.16,.25),(-.48,.51,.03,.24),(-.28,.45,-.01,.19),(.10,.55,-.08,.16),(.51,.68,-.14,.142),(1.00,.87,-.10,.11),(1.38,.94,-.02,.072)],
        [(-.75,.49,.13,.21),(-.98,.64,-.16,.17),(-1.09,.77,-.34,.11)],
        [(-.80,.48,.02,.20),(-1.02,.29,-.25,.14),(-1.17,.10,-.58,.11)],
        [(-.51,.42,.11,.17),(-.31,.26,.30,.115),(-.17,.14,.47,.082),(-.06,.055,.64,.044)],
        [(-.46,.42,.09,.16),(-.21,.21,.27,.103),(.19,.05,.40,.053)],
        [(.46,.67,-.14,.129),(.55,.83,-.22,.108),(.74,1.04,-.37,.043)],
        [(.70,.75,-.02,.10),(.93,.79,.05,.096),(1.31,.86,.14,.042)],
    ],
    "wood_low_root_weave": [
        [(-.96,.18,-.28,.19),(-.86,.35,-.29,.16),(-.89,.49,-.31,.12)],
        [(-.88,.24,-.24,.18),(-.63,.20,-.30,.146),(-.28,.14,-.49,.096),(.11,.11,-.52,.073),(.40,.055,-.48,.038)],
        [(-.78,.24,-.24,.159),(-.44,.18,-.12,.126),(-.19,.16,-.16,.09),(.18,.14,-.28,.09),(.58,.145,-.30,.086),(.95,.08,-.23,.066),(1.18,.03,-.13,.028)],
        [(-.79,.22,-.26,.164),(-.57,.152,-.01,.132),(-.35,.12,.14,.107),(-.01,.08,.19,.078),(.31,.075,.31,.060),(.66,.04,.37,.036),(.95,.035,.52,.024)],
        [(-.55,.18,-.06,.11),(-.31,.123,.00,.079),(-.03,.13,-.03,.066),(.25,.09,.02,.060),(.54,.065,.11,.062),(.79,.06,-.12,.055),(.94,.08,-.23,.061)],
        [(-.54,.142,.10,.11),(-.63,.101,.37,.087),(-.72,.068,.64,.040),(-.62,.04,.77,.035)],
        [(-.88,.27,-.27,.13),(-.91,.15,.025,.088),(-1.06,.079,.24,.065),(-1.19,.035,.43,.051)],
        [(-.49,.11,.04,.106),(-.32,.065,.27,.080),(-.18,.06,.49,.060),(.05,.041,.64,.049),(.24,.038,.76,.035)],
        [(-.78,.15,-.20,.11),(-1.01,.108,-.46,.106),(-1.12,.04,-.63,.05)],
        [(.14,.08,.20,.068),(.33,.078,.28,.055),(.51,.05,.24,.034),(.60,.065,.125,.044)],
    ],
}

def branches(asset_id, size, blender):
    width,height,depth = size
    grid = [np.arange(-width/2-.24, width/2+.24, .018),
            np.arange(-.19,height+.26,.018),
            np.arange(-depth/2-.22,depth/2+.22,.018)]
    xyz = np.ix_(*grid)
    height_scale = .74 if asset_id == "wood_low_root_weave" else .89
    field = np.full(tuple(map(len,grid)), -4., dtype=np.float32)
    for branch in WOOD_PATHS[asset_id]:
        chain = np.array(branch)
        for start,end in zip(chain, chain[1:]):
            p = start[:3]
            d = end[:3]-p
            offset = [(axis-origin) for axis,origin in zip(xyz,p)]
            t = np.clip(sum(shift*delta for shift,delta in zip(offset,d))/np.dot(d,d), 0, 1)
            dx,dy,dz = [component-t*delta for component,delta in zip(offset,d)]
            radius = start[3]+(end[3]-start[3])*t
            angle = np.arctan2(dy/height_scale,dz+dx*.54)
            grain = (.063*np.cos(5*angle + xyz[0]*.8 + xyz[2]*1.2)+
                     .039*np.sin(8*angle-xyz[0]*3.6))
            signed = radius*(1+grain)-np.sqrt(dx*dx+(dy/height_scale)**2+dz*dz)
            np.maximum(field,signed,out=field)
    field = ndi.gaussian_filter(field, .71)
    field = np.minimum(field, xyz[1]-.02)
    vertices, faces, _, _ = marching_cubes(field, 0, spacing=(.018,)*3, allow_degenerate=False)
    vertices += np.array([ax[0] for ax in grid])
    return (*reduce_mesh(vertices,faces,blender,984 if asset_id=="wood_low_root_weave" else 890),
            np.array([],dtype=int))

def validate_bore(vertices, faces, ground):
    tested = []
    for height in [.37,.44,.52]:
        for depth in [-.085,0.,.085]:
            for direction in [-1,1]:
                hits = ray_hits(vertices,faces,[-2*direction,height-ground,depth],[direction,0,0],4)
                tested.append({"z_m":depth,"y_m":height-ground,"direction_x":direction,"passable":len(hits)==0})
    return tested

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", choices=FOLDERS)
    parser.add_argument("--blender", type=Path, required=True)
    args = parser.parse_args()
    profile = json.loads((BATCH/"subjects.json").read_text())[args.id]
    folder = BATCH/args.id
    folder.mkdir(exist_ok=True)
    donors, spans = views(args.id, profile["dimensions_m"], folder, FOLDERS[args.id])
    vertices, faces, inner = hollow_log() if args.id == "wood_hollow_tunnel" else branches(args.id, profile["dimensions_m"], args.blender)
    ground = float(vertices[:,1].min())
    vertices[:,1] -= ground
    gray = Glb()
    mat = gray.material(Image.new("RGBA",(4,4),(166,162,153,255)), "Neutral")
    gray.mesh(vertices,faces,np.zeros((len(vertices),2), dtype=np.float32),mat,args.id)
    gray_path = folder / (args.id+"-gray.glb")
    gray.save(gray_path)
    triangles = vertices[faces]
    cross = np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    normals = np.repeat(cross/np.linalg.norm(cross,axis=1,keepdims=True),3,axis=0)
    paint,uv,shares = texture_atlas(faces,triangles.reshape(-1,3),normals,faces.ravel(),donors,spans,ground,True)
    # Interior donor is inferred from visible wood and kept darker than the exposed bark.
    texels = np.array(paint)
    grids = int(np.ceil(np.sqrt(len(faces))))
    cell = paint.width // grids
    for i in inner:
        x,y = (i % grids)*cell, (i//grids)*cell
        tile = texels[y:y+cell,x:x+cell,:3]
        tile[:] = np.rint(np.clip(tile*np.array([.64,.61,.56]),0,255))
    art = Glb()
    mat = art.material(Image.fromarray(texels),"Weathered hardwood")
    vertices_stream = triangles.reshape(-1,3)
    art.mesh(vertices_stream,np.arange(len(vertices_stream)).reshape(-1,3),uv,mat,args.id)
    model = folder / (args.id+".glb")
    art.save(model)
    np.savez_compressed(model.with_suffix(".npz"),vertices=vertices,faces=faces)
    subprocess.run([str(args.blender),"-b","-P",str(ROOT/"resources/scripts/aquascape/blender_reef_mesh.py"),
                    "--",str(model),"--editable-dir",str(folder)], check=True,stdout=subprocess.DEVNULL)
    model.with_suffix(".npz").unlink()
    component,euler = topology(vertices,faces)
    bore = validate_bore(vertices,faces,ground) if args.id == "wood_hollow_tunnel" else []
    centered = triangles - triangles.mean(axis=(0,1))
    volume = float((np.cross(centered[:,0],centered[:,1])*centered[:,2]).sum()/6.0)
    report = inspect(model)
    ok = bool(report["ok"] and volume>0 and component == 1 and euler <= (0 if bore else 2) and not report["nonmanifold_edges"]
              and all(row["passable"] for row in bore) and art.triangles <= 1200)
    result = {"id":args.id,"ok":ok,"triangles":art.triangles,"connected_components":component,"euler":euler,
              "vertex_bounds_xyz_m":np.ptp(vertices,axis=0).tolist(),"model_sha256":report["sha256"],
              "open_edges":report["open_edges"],"nonmanifold":report["nonmanifold_edges"],"signed_volume_m3":volume,
              "material_count":1,"atlas_size":list(paint.size),"source_texel_shares":shares,"bore_views":bore,
              "gray_sha256":digest(gray_path),"source_blender_sha256":digest(model.with_suffix(".blend"))}
    (folder/"geometry-and-material.validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ["id","ok","triangles","signed_volume_m3"]}))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
