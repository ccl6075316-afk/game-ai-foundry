"""Prepare reviewed source swatches, export our Blender source, and check the GLB."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

import numpy as np
from PIL import Image, ImageEnhance
from scipy import ndimage

from layouts import LAYOUTS

ROOT = Path(__file__).resolve().parents[4]
BATCH = Path(__file__).resolve().parent
WORK = ROOT / "work/reef-expansion-20261123/marine-d"
sys.path.insert(0,str(ROOT / "resources/scripts/aquascape"))
from build_from_art import Glb
from optimize_scenery import compact, metrics
from rig_plant_current import array, read_glb
from validate_art_models import inspect
from validate_shader_shells import points

BLENDER = Path.home() / ".gamefactory/toolchain/blender/Blender.app/Contents/MacOS/Blender"
SUBJECTS = json.loads((BATCH/"subjects.json").read_text())
BUDGET = json.loads((ROOT/"resources/aquascape/geometry-budgets.json").read_text())["types"]
CAMERAS = ["front","right","back","left","top","bottom"]

def dump(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative(path):
    return str(path.relative_to(ROOT))

def swatch(board,region):
    view,x0,y0,x1,y1 = region
    region_image = board.crop((x0,y0,x1,y1))
    layer = np.asarray(region_image.convert("RGB"),dtype=np.uint8)
    lo,hi = layer.min(axis=2),layer.max(axis=2)
    mask = (lo < 215) & ((hi.astype(int)-lo > 16) | (hi < 155))
    if region_image.mode=="RGBA":
        mask &= np.asarray(region_image.getchannel("A"))>=235
    if mask.sum() < 20:
        raise ValueError(f"Source region {region} does not contain enough foreground")
    # Extend the interior pigment into the empty portion of narrow blade crops.
    locator = ndimage.distance_transform_edt(~mask,return_distances=False,return_indices=True)
    return Image.fromarray(layer[locator[0],locator[1]])

def make_atlas(board,layout,path):
    atlas = Image.new("RGB",(256,256),(35,31,24))
    for index,patch in enumerate(layout["patches"]):
        donors=layout["swatches"][patch]
        for direction,view_regions in enumerate(donors):
            offset = 0
            texture = Image.new("RGB",(60,60))
            for region_index,region in enumerate(view_regions):
                end=(region_index+1)*60//len(view_regions)
                color=swatch(board,region).resize((60,end-offset),Image.Resampling.NEAREST)
                texture.paste(color,(0,offset))
                offset=end
            tile=np.pad(np.array(texture),((2,2),(2,2),(0,0)),mode="edge")
            atlas.paste(Image.fromarray(tile),((index%4)*64,(index//4)*128+64*direction))
    if "pigment_saturation" in layout:
        atlas=ImageEnhance.Color(atlas).enhance(layout["pigment_saturation"])
    atlas.save(path,optimize=True)

def expand_blender_glb(native,out):
    # Repository scenery validator consumes deindexed triangles. Preserve loop
    # normals, both UV layers and linear pivot colors exactly as Blender emits.
    doc,data=read_glb(native)
    build=Glb()
    build.doc=doc
    build.bin=bytearray(data)
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            indices=array(doc,data,prim.pop("indices")).reshape(-1)
            attributes={}
            for name,index in prim["attributes"].items():
                accessor=doc["accessors"][index]
                values=array(doc,data,index)[indices]
                if accessor["componentType"]==5123 and accessor.get("normalized"):
                    values=values.astype(np.float32)/65535.
                else:
                    assert accessor["componentType"]==5126,(name,accessor)
                attributes[name]=build.accessor(values,accessor["type"])
            prim["attributes"]=attributes
    for sampler in doc["samplers"]:
        sampler.update(minFilter=9728,magFilter=9728)
    compact(build)
    build.save(out)

def validate(path,row,raw_proof):
    key=row["id"]
    out=inspect(path)
    budget=BUDGET[row["budget_type"]]
    metric=metrics(path)
    d,b=read_glb(path)
    attrs=d["meshes"][0]["primitives"][0]["attributes"]
    v=array(d,b,attrs["POSITION"])
    uv=array(d,b,attrs["TEXCOORD_1"])
    color=array(d,b,attrs["COLOR_0"])
    assert np.isfinite(color).all() and np.isfinite(uv).all()
    assert (uv>=0).all() and (uv<=1).all()
    assert len(d["images"])==1 and len(d["materials"])==1 and len(d["meshes"])==1
    assert all(s["minFilter"]==9728 and s["magFilter"]==9728 for s in d["samplers"]),d["samplers"]
    assert out["ok"] and out["open_edges"]==out["nonmanifold_edges"]==0,out
    assert metric["triangles"]<=budget["hard_limit"], (key, metric, budget)
    assert np.allclose(np.ptp(v,axis=0),row["nominal_xyz_m"],atol=1e-5),np.ptp(v,axis=0)
    assert abs(float(v[:,1].min()))<1e-6
    lo,span=np.array(raw_proof["anchor_min"]),np.array(raw_proof["anchor_size"])
    proof={**out,**metric,"budget":budget,"measured_xyz_m":np.ptp(v,axis=0).tolist(),"root_min_y_m":float(v[:,1].min())}
    if raw_proof["bank_contacts"]:
        proof["bank_contacts"]=raw_proof["bank_contacts"]
    amplitude=row["layout"]["amplitude"]
    if amplitude>0:
        anchor_part=uv[:,0]<=.08
        tips=uv[:,0]>=np.max(uv[:,0])*.88
        root_error=0.;loop_error=0.;tip_displacement=0.
        for phase in (0.,.31,.62):
            first=points(v,uv,color,lo,span,0,phase,amplitude)
            loop_error=max(loop_error,np.linalg.norm(points(v,uv,color,lo,span,10,phase,amplitude)-first,axis=1).max())
            for time in np.linspace(0,10,41):
                posed=points(v,uv,color,lo,span,time,phase,amplitude)
                root_error=max(root_error,np.linalg.norm(posed[anchor_part]-v[anchor_part],axis=1).max())
                tip_displacement=max(tip_displacement,np.linalg.norm((posed-first)[tips],axis=1).max())
        assert root_error<1e-6 and loop_error<1e-6 and tip_displacement>.0003,(root_error,loop_error,tip_displacement)
        proof["rooted_current"]={"anchor_min":lo.tolist(),"anchor_size":span.tolist(),"amplitude":amplitude}
        proof["shader_cpu"]={"root_motion_m":root_error,"loop_error_m":loop_error,"max_tip_motion_m":tip_displacement,"sampled_times":41,"instance_phases":[0,.31,.62]}
    return proof

def run(subject,gray):
    key=subject["id"]
    folder=BATCH.parent/"sources"/f"aquascape-d-{key}-20261123"
    final=BATCH/key
    work=WORK/key
    work.mkdir(parents=True,exist_ok=True)
    final.mkdir(parents=True,exist_ok=True)
    source=folder/"output"/f"{key}_six_views_raw.png"
    workflow_assets=folder/"output/assets-manifest.json"
    layout=LAYOUTS[key]()
    row={**subject,"layout":layout,"source_board_sha256":sha(source)}
    status=json.loads(workflow_assets.read_text())["assets"][key+"_six_views"]["stages"]
    assert any(s["status"]=="done" and s["stage"]=="image.raw" for s in status),status
    board=Image.open(source)
    assert board.size==(1536,1024),board.size
    draft=work/"layout.json"
    dump(draft,row)
    atlas=work/"atlas.png"
    if not gray:
        make_atlas(board,layout,atlas)
    native=(work/(key+"-gray.glb")) if gray else (final/(key+".glb"))
    command=[str(BLENDER),"-b","-t","2","--python-exit-code","19","--python",str(BATCH/"model.py"),"--",str(draft),str(atlas),str(native)]
    if gray:
        command+=["--gray"]
    with (work/"blender.log").open("w") as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    if gray:
        return {"id":key,"name_zh":subject["name_zh"],"model":str(native),"nominal_xyz_m":subject["nominal_xyz_m"]}
    raw=native.with_suffix(".export.glb")
    native.replace(raw)
    expand_blender_glb(raw,native)
    raw.unlink()
    raw_proof=json.loads(native.with_suffix(".build.json").read_text())
    proof=validate(native,row,raw_proof)
    evidence=final/"asset.validation.json"
    proof["file"]=relative(native)
    proof["source_board"]={"file":relative(source),"sha256":sha(source),"dimensions":list(board.size),
                           "camera_order":CAMERAS,"concept_review":"agent-reviewed for provisional gray mesh, user pending",
                           "workflow_assets_manifest":relative(workflow_assets),"subject_ecology":subject["source_url"],
                           "assembly_inference":layout["notes"],"texture_sample_regions":layout["swatches"]}
    dump(evidence,proof)
    row={k:v for k,v in subject.items() if k!="brief"}
    row.update(model=relative(native),editable_source=relative(native.with_suffix(".blend")),source_board=relative(source),
               source_board_sha256=sha(source),validation=relative(evidence),model_sha256=sha(native),
               blender_sha256=sha(native.with_suffix(".blend")),triangles=proof["triangles"],
               placement_anchor="bottom",visual_review="pending",user_acceptance="pending")
    if "rooted_current" in proof:
        row["rooted_current"]=proof["rooted_current"]
    dump(final/"candidate.json",row)
    native.with_suffix(".build.json").replace(work/"build-input-metrics.json")
    return row

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset",nargs="+",choices=list(LAYOUTS))
    parser.add_argument("--gray",action="store_true")
    args=parser.parse_args()
    rows=[]
    for subject in SUBJECTS:
        if subject["id"] in args.asset:
            result=run(subject,args.gray)
            rows.append(result)
            print(json.dumps(result,ensure_ascii=False),flush=True)
    if args.gray:
        dump(WORK/"gray.json",rows)
    else:
        dump(BATCH/"candidate-catalog.json",{"assets":[json.loads(p.read_text()) for p in sorted(BATCH.glob("*/candidate.json"))],"user_acceptance":"pending"})
