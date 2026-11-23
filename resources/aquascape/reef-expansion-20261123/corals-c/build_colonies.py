"""Bake source-art textures after building attached, genuinely volumetric colonies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from skimage.measure import marching_cubes
from PIL import Image

folder = Path(__file__).resolve().parent
root = folder.parents[3]
work = root / "work/reef-expansion-20261123/corals-c"
sys.path.insert(0, str(root / "resources/scripts/aquascape"))
from surface_palette import texture_atlas
from build_from_art import Glb
from build_reef_arch_from_material_views import projection_reports, reduce_mesh
from validate_art_models import inspect
from forms import FORMS

profile = json.loads((folder / "profile.json").read_text())
policy = json.loads((root / "resources/aquascape/geometry-budgets.json").read_text())["types"]
blender = Path(os.environ.get("BLENDER", str(Path.home() / ".gamefactory/toolchain/blender/Blender.app/Contents/MacOS/Blender")))
build = folder / "candidates"
views = ("front", "right", "rear", "left", "top", "bottom")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def donors_from(source, selection, dims):
    b = np.asarray(Image.open(source).convert("RGB"))
    h0,w0 = b.shape[:2]
    donors={}
    masks={}
    rectangles={}
    w,h,d=dims
    spans={"front":[w,h],"rear":[w,h],"right":[d,h],"left":[d,h],"top":[w,d],"bottom":[w,d]}
    selection.mkdir(parents=True, exist_ok=True)
    ink=b.min(axis=-1)<239
    labels,_=ndi.label(ink)
    sizes=np.bincount(labels.ravel())
    sizes[0]=0
    objects=ndi.find_objects(labels)
    for row in range(2):
        r0=h0*row/2
        r1=h0*(row+1)/2
        primary=[(size,i,box) for i,(size,box) in enumerate(zip(sizes[1:],objects),1)
                 if box is not None and r0 <= (box[0].start + box[0].stop)/2 < r1]
        targets=sorted(sorted(primary,reverse=True)[:3],key=lambda item:item[2][1].start+item[2][1].stop)
        if len(targets)!=3 or min(item[0] for item in targets) < 1800:
            raise ValueError(f"{source.name}: expected complete source of three distinct views per row")
        for offset, (_, label, (ys,xs)) in enumerate(targets):
            view=views[row*3+offset]
            rgb=b[ys,xs]
            mask=labels[ys,xs]==label
            trusted=ndi.binary_erosion(mask, iterations=2)
            distances, edges=ndi.distance_transform_edt(~trusted, return_indices=True)
            donors[view]=(rgb[edges[0], edges[1]], distances)
            masks[view]=mask
            rectangles[view]=[xs.start,ys.start,xs.stop,ys.stop]
    return donors,masks,spans,rectangles


def estimate_topology(vertices, faces):
    ea = np.concatenate([faces[:,a] for a in (0,1,2)])
    eb = np.concatenate([faces[:,b] for b in (1,2,0)])
    edge = np.sort(np.column_stack((ea,eb)),axis=1)
    unique, counts = np.unique(edge,axis=0,return_counts=True)
    sparse = coo_matrix((np.ones(len(unique)), (unique[:,0],unique[:,1])), shape=(len(vertices), len(vertices))).tocsr()
    n=connected_components(sparse,directed=False,return_labels=False)
    return {"connected_components": n, "euler_characteristic": len(vertices)-len(unique)+len(faces),
            "open_edges": int(np.count_nonzero(counts==1)), "nonmanifold_edges": int(np.count_nonzero(counts>2))}


def fit_surface(key, dims, goal):
    step = .011 if key == "reef_sea_fan" else .014
    a = np.arange(-.71,.71+step,step,dtype=np.float32)
    b = np.arange(-.21,1.32+step,step,dtype=np.float32)
    g = np.meshgrid(a,b,a,indexing="ij",sparse=True)
    field = np.maximum(FORMS[key](g), -.7*g[1])
    if any(np.min(np.take(field, [0,-1], axis=i)) <= 0 for i in range(3)):
        raise ValueError("Field crosses extraction bounds")
    # Isolated tiny lobe fragments should never hang in the water.
    labels,n = ndi.label(field < 0)
    sizes = np.bincount(labels.ravel())
    sizes[0]=0
    biggest=int(sizes.argmax())
    removed=int(sizes.sum()-sizes[biggest])
    field[(labels != biggest) & (field < 0)] = step
    vertices,faces,*_=marching_cubes(field,0,spacing=(step,step,step),allow_degenerate=False)
    vertices+=np.array([a[0],b[0],a[0]])
    mins, maxs = vertices.min(0), vertices.max(0)
    center=(mins+maxs)/2
    center[1]=mins[1]
    dims=np.asarray(dims)
    vertices=(vertices-center)*dims/(maxs-mins)
    vertices,faces=reduce_mesh(vertices,faces,blender,goal)
    ymin=float(vertices[:,1].min())
    vertices[:,1]-=ymin
    vertices[np.abs(vertices[:,1]) < .0012,1]=0
    return vertices,faces,{"source_field_components":n,"isolated_voxels_removed":removed,
                           "bounds_xyz_m": np.ptp(vertices,axis=0).tolist()}


def make_glb(path, label, vertices, faces, uv, tex, smooth=None):
    glb=Glb()
    material=glb.material(tex,label)
    corners = vertices[faces].reshape(-1,3)
    unshared = np.arange(len(corners), dtype=np.int32).reshape(-1,3)
    glb.mesh(corners, unshared, uv, material, path.stem)
    if smooth is not None:
        prim=glb.doc["meshes"][0]["primitives"][0]
        attrs=prim["attributes"]
        normal=smooth[faces].reshape(-1,3).copy()
        floor=(vertices[faces,1] < .0015).all(axis=1)
        normal.reshape(-1,3,3)[floor]=[0,-1,0]
        attrs["NORMAL"]=glb.accessor(normal,"VEC3")
    glb.save(path)


def opening_probes(key, vertices, faces):
    if key == "reef_tube_sponge":
        hints=[[-.15,-.047],[-.31,.25],[.25,-.08],[.20,.27]]
    elif key == "reef_barrel_sponge":
        hints=[[0,0]]
    else:
        return {}
    from build_reef_arch_from_material_views import ray_hits
    span=np.ptp(vertices,axis=0)
    size_x,size_y,size_z=span
    hits=[]
    for dx,dz in hints:
        distances=[]
        for ox in [-.024,0,.024]:
            for oz in [-.024,0,.024]:
                vals=ray_hits(vertices,faces,[(dx+ox)*size_x,size_y+.2,(dz+oz)*size_z],[0,-1,0],size_y+.4)
                if vals:
                    distances.append(round(float(size_y+.2-vals[0]),4))
        hits.append({"normalized_xz":[dx,dz],"first_surface_heights_m":distances})
    return {"vertical_cavity_floor_probes":hits}


def author(i, row):
    key,name,species,sea,category,dims,kind,shape,url,use=row
    from shutil import copyfile
    art_status = "draft_intent"
    source = root / f"projects/aquascape-c-six-material-{i//2+1:02d}-20261123/output/{key}_raw.png"
    approved_bits = work / "source-notes.json"
    notes=json.loads(approved_bits.read_text()) if approved_bits.is_file() else {}
    if key not in notes:
        raise ValueError(f"Six-view source was not visually checked: {key}")
    candidate = build/key
    candidate.mkdir(parents=True,exist_ok=True)
    review = work/"review-input"/key
    review.mkdir(parents=True,exist_ok=True)
    donor_art = candidate / "six-material-views.png"
    copyfile(source, donor_art)
    donors,masks,spans,rectangles=donors_from(donor_art, review, dims)
    preferred=policy[kind]["preferred"]
    hard=policy[kind]["hard_limit"]
    overrides={"reef_sea_fan": 978,"reef_tube_sponge": 924,"reef_staghorn_coral":820,
               "reef_table_coral":818,"reef_foliose_coral":880,"reef_scroll_coral":884,"reef_barrel_sponge":818}
    verts,faces,field = fit_surface(key, dims, overrides.get(key,preferred))
    topology=estimate_topology(verts,faces)
    if len(faces)>hard or topology["open_edges"] or topology["nonmanifold_edges"] or topology["connected_components"]!=1:
        raise ValueError(f"{key}: complete mesh outside budget or closure fails {len(faces)} {topology}")
    tri = verts[faces]
    norms = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    smooth=np.zeros_like(verts)
    for j in range(3):
        np.add.at(smooth,faces[:,j],norms)
    smooth/=np.maximum(np.linalg.norm(smooth,axis=-1)[:,None],1e-10)
    norms/=np.maximum(np.linalg.norm(norms,axis=-1)[:,None],1e-10)
    forward = np.einsum("ij,ij->i",tri[:,0],np.cross(tri[:,1],tri[:,2])).sum()
    if forward <= 0:
        raise ValueError(f"{key}: invalid signed volume")
    uv0=np.full((len(faces)*3,2),.5,dtype=np.float32)
    gray=review/f"{key}-gray.glb"
    make_glb(gray,"Review gray",verts,faces,uv0,Image.new("RGBA",(2,2),(161,166,166,255)),smooth)
    atlas, uv, owner = texture_atlas(key,faces,tri,smooth,norms,donors,spans)
    model=candidate/f"{key}.glb"
    make_glb(model,name,verts,faces,uv,atlas,smooth)
    checked=inspect(model)
    if not checked["ok"] or checked["nonmanifold_edges"]:
        raise ValueError(checked)
    exchange=model.with_suffix(".npz")
    np.savez_compressed(exchange,vertices=verts,faces=faces)
    run=[str(blender),"-b","--python-exit-code","1","--python",
         str(folder/"blend_source.py"),"--",str(model),"--editable-dir",str(candidate)]
    subprocess.run(run,check=True,capture_output=True,text=True)
    exchange.unlink()
    blend=model.with_suffix(".blend")
    verify=[str(blender),"-b",str(blend),"--python-exit-code","1","--python",
            str(root/"work/reef-expansion-20261123/verify_blend_source.py"),"--",str(candidate)]
    result=subprocess.run(verify,check=True,capture_output=True,text=True)
    (review/"cold-source.log").write_text(result.stdout)
    silhouette=projection_reports(verts,faces,masks,spans,0,review)
    report={"id":key,"name":name,"species":species,"geography":sea,"category":category,"nominal_xyz_m":dims,
            "ecology_and_use":use,"primary_reference":url,"approvals":{"user_intent":"pending","user_native":"pending"},
            "source":{"file":donor_art.name,"sha256":sha(donor_art),"status":art_status,"views":rectangles,"review":notes[key]},
            "shape_specification":shape,"shape_method":FORMS[key].__name__,"geometry": {**field,**topology,**opening_probes(key,verts,faces),
            "signed_volume_m3":float(forward/6),"triangle_count":len(faces),"budget_type":kind,
            "preferred_triangles":preferred,"hard_triangle_limit":hard,"ground_y_min":float(verts[:,1].min()),
            "contact_vertices":int(np.count_nonzero(verts[:,1]==0)),"projection":silhouette},
            "material":{"native_source_pixel_selection":True,"filter":"nearest","atlas":1536,
                        "macro_shadow_removed_for_cavities":"sponge" in key,
                        "primitive_count":1,"material_count":1,"source_fractions":owner},
            "blend":{"file":blend.name,"sha256":sha(blend),"cold_geometry_uv_texture_pass":True},
            "glb":checked,
            "current_status":"static_only_pending_native" if category=="octocoral" else "static_candidate_pending_native",
            "scope":"低面展缸艺术模块。结构与方向参考六面意向，非生物实测。相机近似会影响投影重叠。"}
    write_json(candidate/"validation.json",report)
    data={"id":key,"name":name,"label":name,"scientific_name":species,"aquatic_ecology":sea,
          "category":category,"nominal_xyz_m":dims,"budget_type":kind,"triangles":len(faces),
          "source_glb":str(model),"editable_source":str(blend),"source_intent":str(donor_art),
          "validation": str(candidate/"validation.json"), "model":str(model), "user_acceptance":"pending"}
    write_json(candidate/"catalog-entry.json",data)
    print(key,len(faces),topology,"Godot pending",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="+")
    args=parser.parse_args()
    for i,row in enumerate(profile):
        if row[0] in args.ids:
            author(i,row)


if __name__=="__main__":
    main()
