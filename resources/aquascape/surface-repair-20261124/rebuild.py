"""Source-based model variants for the texture inspection window."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

RELEASE = Path(__file__).resolve().parent
ROOT = RELEASE.parents[2]
sys.path.insert(0,str(ROOT/"resources/scripts/aquascape"))
from bake_reef_arch_six_view_art import DIRECTIONS, project, texture_atlas
from build_decor_ten import ray_hits
from build_from_art import Glb
from build_reef_arch_from_material_views import axes,reduce_mesh
from build_reef_relief_set import topology
from optimize_scenery import compact
from rig_plant_current import array,read_glb
from validate_art_models import inspect
from relief import ZONES,sculpt,subdivide

from repaint_ship_and_chest import bake as repaint_ship_and_chest

BUILDER = ROOT / "resources/scripts/aquascape/blender_reef_mesh.py"
DEFAULT_BLENDER = Path.home() / ".gamefactory/toolchain/blender5/Blender.app/Contents/MacOS/Blender"
VIEW_ORDER=["front","right","rear","left","top","bottom"]
# When the drawn board orders views by the geometry rather than the requested label.
SWAP={"clay_pipe":["front","right","left","rear","top","bottom"]}
# Mouth midplanes in normalized old bounds. Coordinates exclude the opening's edge.
OPENINGS={"clay_pipe":(0,.5,.5),"ruin_arch":(2,.48,.37),"ruined_tower":(2,.50,.30),"stone_bridge":(2,.50,.33),
          "slate_cave":(2,.50,.43),"bamboo_shelter":(0,.50,.50)}
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def regions(board,key):
    rgb=np.asarray(board.convert("RGB"))
    height,width=rgb.shape[:2]
    # Locate sufficiently pale gutters near nominal thirds/half, before masking each plane.
    foreground=(rgb.min(2)<220) & ((rgb.max(2)-rgb.min(2)>8)|(rgb.max(2)<166))
    ey=round(height/2)
    path=np.arange(ey-round(height*.085),ey+round(height*.085))
    y_cut=int(path[np.argmin(foreground[path].sum(1)+np.abs(path-ey)*.13)])
    y_edges=(0,y_cut,height)
    donors={}
    details={}
    for row in (0,1):
        a,b=y_edges[row:row+2]
        column_counts=foreground[a:b].sum(0)
        x_edges=[0]
        for section in (1,2):
            boundary=round(width*section/3)
            options=np.arange(boundary-round(width*.060),boundary+round(width*.060))
            x_edges.append(int(options[np.argmin(column_counts[options]+np.abs(options-boundary)*.15)]))
        x_edges.append(width)
        for i in range(3):
            start,end=x_edges[i:i+2]
            picked=SWAP.get(key,VIEW_ORDER)[3*row+i]
            photo=rgb[a:b,start:end]
            mask=foreground[a:b,start:end]
            mask=ndi.binary_closing(mask,iterations=2)
            labels,_=ndi.label(mask)
            count=np.bincount(labels.ravel())
            count[0]=0
            maximum=count.max()
            if maximum<230:raise ValueError(f"{key} {picked} board has no usable object")
            mask&=count[labels]>=max(32,int(maximum*.008))
            iy,ix=mask.nonzero()
            l,t,r,bt=ix.min(),iy.min(),ix.max()+1,iy.max()+1
            photo=photo[t:bt,l:r]
            reliable=ndi.binary_erosion(mask[t:bt,l:r],iterations=2)
            distance,nearest=ndi.distance_transform_edt(~reliable,return_indices=True)
            donors[picked]=photo[nearest[0],nearest[1]],distance
            details[picked]=list(map(int,(start+l,a+t,start+r,a+bt)))
    return donors,details

def open_checks(vertices,faces,ref_verts,ref_faces,profile):
    probes=[]
    low=ref_verts.min(0)
    size=np.ptp(ref_verts,axis=0)
    axis,ca,cb=profile
    a,b=[n for n in range(3) if n!=axis]
    d=np.zeros(3)
    d[axis]=1.
    for u in np.linspace(ca-.14,ca+.14,9):
        for v in np.linspace(cb-.11,cb+.11,9):
            point=low+size*.5
            point[a]=low[a]+size[a]*u
            point[b]=low[b]+size[b]*v
            point[axis]=low[axis]-.11
            distance=size[axis]+.22
            before=ray_hits(ref_verts,ref_faces,point,d,distance)
            if before:continue
            after=ray_hits(vertices,faces,point,d,distance)
            probes.append(not after)
    return {"clear_before":len(probes),"still_clear":sum(probes),"passed":bool(probes) and sum(probes)>=.9*len(probes)}

def save_mesh(path, doc, binary, v, triangles, n, uv, image, same):
    glb=Glb()
    glb.doc=doc
    glb.bin=bytearray(binary)
    glb.doc["materials"]=[]
    glb.doc["textures"]=[]
    glb.doc["images"]=[]
    primitive=doc["meshes"][0]["primitives"][0]
    if not same:
        primitive["attributes"]["POSITION"]=glb.accessor(v[triangles].reshape(-1,3),"VEC3")
        primitive["attributes"]["NORMAL"]=glb.accessor(n,"VEC3")
    primitive["attributes"]["TEXCOORD_0"]=glb.accessor(uv,"VEC2")
    primitive["material"]=glb.material(image,"New artwork from six orthographic views")
    compact(glb)
    glb.save(path)

def register_paint_to_footprint(view, donor, vertices, triangles, spans):
    paint,distance=donor
    h,w=paint.shape[:2]
    width,height=spans[view]
    a,b=axes(vertices.T,view,spans)
    px=np.stack((a*(w-1)/width,b*(h-1)/height),axis=1)
    uv=np.empty_like(paint)
    mask=Image.new("1",(w,h))
    pen=ImageDraw.Draw(mask)
    for poly in px[triangles]:
        pen.polygon([tuple(p) for p in poly],fill=1)
    target = np.array(mask)
    new_valid=target.copy()
    for y in range(h):
        source_x=np.flatnonzero(distance[y]<=.01)
        target_x=np.flatnonzero(target[y])
        if len(source_x)<8 or len(target_x)<4:
            new_valid[y]=False
            continue
        left,right=target_x[[0,-1]]
        sl,sr=source_x[[0,-1]]
        input_cols=np.rint(np.clip((np.arange(w)-left)/max(1,right-left),0.,1.)*(sr-sl)+sl).astype(int)
        # Fit the independent, newly painted plane to its own observed outline.
        # This samples wholly within the generated art and avoids cloned border rows.
        uv[y]=paint[y,input_cols]
    missing,indices=ndi.distance_transform_edt(~new_valid,return_indices=True)
    return uv[indices[0],indices[1]],missing

def coral_surface(verts,faces,donors):
    v,f=subdivide(*subdivide(verts,faces))
    size=np.ptp(v,axis=0)
    shift=v.min(axis=0)+size*[.5,0,.5]
    pos=v-shift
    p=v[f]
    cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
    normal=np.zeros_like(v)
    for i in range(3):
        np.add.at(normal,f[:,i],cross)
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    spans={"front":size[[0,1]],"rear":size[[0,1]],"left":size[[2,1]],"right":size[[2,1]],"top":size[[0,2]],"bottom":size[[0,2]]}
    fields=[]
    weights=[]
    for side,(axis,sign) in DIRECTIONS.items():
        paint,trust=project(side,pos,spans,donors[side])
        tone=(paint@np.array([.26,.62,.12]))/255.
        fields.append(tone)
        weights.append(np.maximum(.002,sign*normal[:,axis])**5 * np.maximum(.005,trust))
    mixture=np.average(np.array(fields),axis=0,weights=np.array(weights))
    # Dark wide tissue grooves in the six-face art physically recede.
    low,high=np.quantile(mixture,[.21,.79])
    tissue=np.clip((mixture-(low+high)*.5)/max(.02,(high-low)*.5),-1,1)
    support=np.clip((pos[:,1]/size[1]-.03)/.15,0,1)
    offsets=(.044*size[1]*tissue)*support
    return v+offsets[:,None]*normal,f,offsets

def process(row, baseline, output, blender):
    key = row["id"]
    raw = ROOT / row["source_art"]
    input_path = baseline / (key + ".glb")
    if sha(raw) != row["source_sha256"] or sha(input_path) != row["before_sha256"]:
        raise ValueError(f"{key}: archived original or six-face board does not match the manifest")
    target_dir = output / key
    if key in ("shipwreck", "treasure_chest"):
        return repaint_ship_and_chest(key, input_path, raw, blender, BUILDER, target_dir)
    doc,bindata=read_glb(input_path)
    attrs=doc["meshes"][0]["primitives"][0]["attributes"]
    stream=array(doc,bindata,attrs["POSITION"])
    old_normals=array(doc,bindata,attrs["NORMAL"])
    original,indices=np.unique(stream,axis=0,return_inverse=True)
    original_faces=indices.reshape(-1,3)
    vertices,tris=original,original_faces
    no_geom=key not in ZONES and key != "reef_brain_coral"
    with Image.open(raw) as source:
        donors,views=regions(source,key)
    target_dir.mkdir(exist_ok=True,parents=True)
    relief_proof=None
    cavity=None
    if not no_geom:
        v,faces,shift=(coral_surface(vertices,tris,donors) if key=="reef_brain_coral" else sculpt(key,vertices,tris))
        policy = json.loads((ROOT / "resources/aquascape/geometry-budgets.json").read_text())
        budget = policy["types"][row["whole_instance_budget"]]
        limit=budget["hard_limit"]
        goal=580 if key in ("lava_rock","dragon_stone","reef_brain_coral") else min(limit-16,round(budget["preferred"]*1.35))
        vertices,tris=reduce_mesh(v,faces,blender,goal)
        after=topology(vertices,tris)
        before=topology(original,original_faces)
        if after!=before:
            raise ValueError(f"{key} topology differs: {before} -> {after}")
        # Measure signed motion against a locally subdivided original for scale.
        before_xyz=original[original_faces].reshape(-1,3)
        old_dims=np.ptp(before_xyz,axis=0)
        new_dims=np.ptp(vertices,axis=0)
        if (abs(new_dims-old_dims)/old_dims>.15).any():
            raise ValueError(f"{key} exceeded shape extent change")
        rough=cKDTree(vertices).query(v)[0]
        relief_proof={"planned_zones":ZONES.get(key,"Six-view pigment aligned macro groove relief"),"max_groove_m":float(shift.min()),
            "max_protrusion_m":float(shift.max()),"width_height_depth_original_m":old_dims.tolist(),
            "width_height_depth_candidate_m":new_dims.tolist(),"local_simplification_distance_median_m":float(np.median(rough)),
            "shell_topology_before":list(before),"shell_topology_after":list(after),"cavity":cavity}
    if key in OPENINGS:
        cavity=open_checks(vertices,tris,original,original_faces,OPENINGS[key])
        assert cavity["passed"],(key,cavity)
        if relief_proof is not None:
            relief_proof["cavity"]=cavity
    loc=vertices.min(axis=0)
    size=np.ptp(vertices,axis=0)
    align=loc+size*[.5,0,.5]
    positions=vertices[tris].reshape(-1,3)
    xyz=vertices[tris]
    normals=old_normals
    if not no_geom:
        cp=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
        normals=np.repeat(cp/np.maximum(np.linalg.norm(cp,axis=1,keepdims=True),1e-12),3,axis=0)
        if key == "reef_brain_coral":
            n=np.zeros_like(vertices)
            for corner in range(3):
                np.add.at(n,tris[:,corner],cp)
            n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
            normals=n[tris].reshape(-1,3)
    spans={"front":size[[0,1]],"rear":size[[0,1]],"left":size[[2,1]],"right":size[[2,1]],"top":size[[0,2]],"bottom":size[[0,2]]}
    registered={"rock":["top"],"slate_stack":["top"],"weathered_log":["top"]}.get(key,[])
    for view in registered:
        donors[view]=register_paint_to_footprint(view,donors[view],vertices-align,tris,spans)
    atlas,uv,ownership=texture_atlas(tris,positions-align,normals,tris.ravel(),donors,spans,0,True)
    candidate=target_dir/(key+".glb")
    save_mesh(candidate,doc,bindata,vertices,tris,normals,uv,atlas,no_geom)
    check=inspect(candidate)
    assert check["ok"] and check["open_edges"]==check["nonmanifold_edges"]==0,(key,check["failures"])
    dd,bb=read_glb(candidate)
    ids=dd["meshes"][0]["primitives"][0]["attributes"]
    if no_geom:
        assert np.array_equal(array(dd,bb,ids["POSITION"]),stream)
        assert np.array_equal(array(dd,bb,ids["NORMAL"]),old_normals)
    else:
        assert len(tris)<=limit
    np.savez_compressed(candidate.with_suffix(".npz"),vertices=vertices,faces=tris)
    subprocess.run([str(blender),"-b","-t","1","--python-exit-code","19","-P",str(BUILDER),
                    "--",str(candidate),"--editable-dir",str(target_dir)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    candidate.with_suffix(".npz").unlink()
    result={"id":key,"name_zh":row["name_zh"],"candidate":str(candidate),"source_art":str(raw),"source_sha256":sha(raw),
            "source_boxes":views,"outline_uv_registration":registered,"source_view_ownership":ownership,"triangles":len(tris),
            "geometry_unchanged":no_geom,"relief":relief_proof,"cavity":cavity,"user_acceptance":"pending","status":"pending_native_review"}
    (target_dir/"validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--id", action="append", help="Limit to the given asset ID (repeatable)")
    options = parser.parse_args()
    baseline = options.baseline.resolve()
    output = options.output.resolve()
    if output.is_relative_to(ROOT / "projects/fishing-2d"):
        parser.error("Choose a scratch output outside the game project")
    manifest = json.loads((RELEASE / "release.json").read_text(encoding="utf-8"))
    available = {row["id"]: row for row in manifest["items"]}
    selected = options.id or list(available)
    unknown = set(selected) - available.keys()
    if unknown:
        parser.error(f"Unknown asset IDs: {', '.join(sorted(unknown))}")
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = {
            key: executor.submit(process, available[key], baseline, output, options.blender)
            for key in selected
        }
        for key, job in jobs.items():
            job.result()
            model = output / key / (key + ".glb")
            if sha(model) != available[key]["after_sha256"]:
                raise ValueError(f"{key}: rebuilt GLB differs from the accepted bytes")
            print(f"{key}: rebuilt GLB matches the release", flush=True)


if __name__ == "__main__":
    main()
