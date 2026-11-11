"""Grade the true existing oral chart while protecting all skin and lip UVs."""
from collections import Counter
import json
from pathlib import Path
import numpy as np
from PIL import Image
from bake_material import WORK, load_image_chart, raster, read_glb, read_parts, sha, smooth

SOURCE=WORK/"mouth-r3/fish.glb"
OUT=WORK/"mouth-r4"
DOC,BIN=read_glb(SOURCE)
parts=[p for p in read_parts(DOC,BIN) if p["node"]=="Closed_body"]
oral=next(p for p in parts if p["material"]=="Front mouth oral chart")
img=oral["image"]
original=load_image_chart(DOC,BIN,img)
result=original.copy()
h,w=original.shape[:2]
protected=np.zeros((h,w),bool)
for part in parts:
    if part is oral or part["image"]!=img:
        continue
    for face in part["faces"]:
        px,_,_=raster(part["uv"][face],w,h,1.75)
        protected[px[:,1],px[:,0]]=True
keys=Counter(tuple(sorted((tuple(np.round(a.astype(float),7)),tuple(np.round(b.astype(float),7)))))
             for face in oral["pos"][oral["faces"]] for a,b in zip(face,np.roll(face,-1,axis=0)))
rim=np.array([edge for edge,count in keys.items() if count==1])
assert len(rim)==104
p0,p1=rim.transpose(1,0,2)
directions=p1-p0
length2=(directions**2).sum(1)
assert np.all(length2>0)
covered=np.zeros((h,w),bool)
depth_max=0.
for face in oral["faces"]:
    px,beta,_=raster(oral["uv"][face],w,h,.85)
    x,y=px.T
    valid=~protected[y,x]
    x,y,beta=x[valid],y[valid],beta[valid]
    if not len(x):
        continue
    point=beta@oral["pos"][face]
    d=point[:,None,:]-p0[None,:,:]
    t=np.clip((d*directions).sum(2)/length2,0,1)
    depth=np.sqrt(((d-t[:,:,None]*directions)**2).sum(2).min(1))
    depth_max=max(depth_max,depth.max())
    rgb=original[y,x,:3].astype(float)
    # Original local value variations survive in the warm recessed palette.
    luminance=rgb@np.array([.23,.62,.15])
    target=np.array([32.,16.,13.])+luminance[:,None]*np.array([.15,.105,.078])
    recess=smooth((depth-.00065)/.0067)
    near=smooth((depth-.00020)/.0020)
    # Take the green cast down gently near the lower oral lip. This operates
    # only behind the geometry seam and never crosses the protected skin UVs.
    green=np.maximum(0,rgb[:,1]-.70*rgb[:,0])
    soft=rgb.copy()
    soft[:,1]-=np.minimum(20,green)*near*.8
    soft[:,0]+=np.minimum(12,green)*near*.12
    color=soft*(1-recess[:,None]) + target*recess[:,None]
    result[y,x,:3]=np.rint(np.clip(color,0,255)).astype("uint8")
    covered[y,x]=True
changed=np.any(result!=original,axis=2)
assert changed.any() and not np.any(changed&protected)
assert np.array_equal(result[:,:,3],original[:,:,3]) and np.array_equal(result[~covered],original[~covered])
OUT.mkdir(exist_ok=False)
image=OUT/"oral-chart.png"
Image.fromarray(result).save(image)
(OUT/"oral-color.validation.json").write_text(json.dumps(dict(
    ok=True,source_model_sha256=sha(SOURCE),chart_sha256=sha(image),image_index=img,
    changed_oral_rgb_texels=int(changed.sum()),protected_skin_texels=int(protected.sum()),
    oral_closed_rim_edges=len(rim),maximum_rim_distance_native=float(depth_max),
    alpha_exact=True,all_non_oral_texels_exact=True,
    scope="Real oral surface projection; near-lip warm tone and recessed oral cavity darkened. No outer skin edit."
),indent=2)+"\n")
