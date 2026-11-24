"""Repaint the exact deployed chest and ship meshes from separate art for every face."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from bake_reef_arch_six_view_art import texture_atlas
from build_from_art import Glb
from optimize_scenery import compact
from rig_plant_current import array,read_glb
from validate_art_models import inspect

boxes = {
    "treasure_chest": {
        "front":(4,46,522,462),"right":(557,39,960,472),"rear":(1014,49,1530,456),
        "left":(71,474,492,974),"top":(518,488,1009,948),"bottom":(1019,490,1531,949),
    },
    "shipwreck": {
        "front":(8,85,540,447),"right":(540,73,979,464),"left":(1007,92,1532,463),
        "rear":(6,567,523,878),"top":(515,568,1034,876),"bottom":(1037,565,1530,877),
    },
}
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def art_donors(board,key):
    donors={}
    corners={}
    for view, box in boxes[key].items():
        pixels=np.array(board.crop(box).convert("RGB"))
        chroma=np.max(pixels,axis=2)-np.min(pixels,axis=2)
        mask=(np.min(pixels,axis=2)<218) & (chroma>8)
        mask=ndi.binary_closing(mask,iterations=2)
        labels,_=ndi.label(mask)
        counts=np.bincount(labels.ravel())
        counts[0]=0
        mask &= counts[labels]>55
        rows,cols=mask.nonzero()
        y0,y1,x0,x1=rows.min(),rows.max()+1,cols.min(),cols.max()+1
        pixels=pixels[y0:y1,x0:x1]
        trust=ndi.binary_erosion(mask[y0:y1,x0:x1],iterations=2)
        dist,field=ndi.distance_transform_edt(~trust,return_indices=True)
        donors[view]=pixels[field[0],field[1]],dist
        corners[view]=[int(box[0]+x0),int(box[1]+y0),int(box[0]+x1),int(box[1]+y1)]
    return donors,corners

def bake(key, old, board, blender, builder, folder):
    folder.mkdir(parents=True, exist_ok=True)
    new = folder / (key + ".glb")
    d,b=read_glb(old)
    source_prim=d["meshes"][0]["primitives"][0]
    old_attributes=source_prim["attributes"].copy()
    positions=array(d,b,old_attributes["POSITION"])
    normals=array(d,b,old_attributes["NORMAL"])
    low=positions.min(axis=0)
    size=np.ptp(positions,axis=0)
    shift=low+size*[.5,0,.5]
    viewpoints={
        "front":size[[0,1]],"rear":size[[0,1]],
        "left":size[[2,1]],"right":size[[2,1]],
        "top":size[[0,2]],"bottom":size[[0,2]],
    }
    vertices,index=np.unique(positions,axis=0,return_inverse=True)
    triangles=index.reshape(-1,3)
    with Image.open(board) as im:
        donors,coords=art_donors(im,key)
    texture,new_uv,faces=texture_atlas(triangles,positions-shift,normals,index,donors,viewpoints,0,True)
    fresh=Glb()
    fresh.doc=d
    fresh.bin=bytearray(b)
    fresh.doc["materials"]=[]
    fresh.doc["images"]=[]
    fresh.doc["textures"]=[]
    source_prim["material"]=fresh.material(texture,"Six painted wood faces")
    source_prim["attributes"]["TEXCOORD_0"]=fresh.accessor(new_uv,"VEC2")
    compact(fresh)
    fresh.save(new)
    next_doc,next_buffer=read_glb(new)
    attrs=next_doc["meshes"][0]["primitives"][0]["attributes"]
    keep=all(np.array_equal(array(next_doc,next_buffer,attrs[name]),data)
             for name,data in [("POSITION",positions),("NORMAL",normals)])
    assert keep
    result=inspect(new)
    assert result["ok"] and result["nonmanifold_edges"]==0,result
    exchange=new.with_suffix(".npz")
    np.savez_compressed(exchange,vertices=vertices,faces=triangles)
    subprocess.run([str(blender),"-b","-t","2","--python-exit-code","19","-P",str(builder),"--",str(new),"--editable-dir",str(folder)],check=True,stdout=subprocess.DEVNULL)
    exchange.unlink()
    details={"id":key,"preview":str(new),"source_board":str(board),"source_sha256":sha(board),
        "source_crops":coords,"current_glb_sha256":sha(old),"preview_glb_sha256":sha(new),
        "same_position_and_normal_streams":keep,"triangles":len(triangles),"projected_texel_shares":faces,
        "status":"local_review"}
    (folder/"validation.json").write_text(json.dumps(details,indent=2)+"\n")
    return details
