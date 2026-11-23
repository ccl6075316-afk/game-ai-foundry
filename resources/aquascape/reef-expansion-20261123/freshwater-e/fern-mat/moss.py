"""Low thalloid mat from revised substrate-free six-view source."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

folder=Path(__file__).resolve().parent
root=folder.parents[4]
common=folder.parents[1]/"corals-c"
sys.path.insert(0,str(common))
import build_colonies as common_build
from build_colonies import make_glb, fit_surface, estimate_topology, inspect, sha
from forms import branch, oval, union
from surface_palette import texture_atlas

key="riverwort_moss_mat"
work=root/"work/reef-expansion-20261123/freshwater-e/fern-mat"
candidate=folder/"candidates"/key
source=root/f"projects/aquascape-e-riverwort-moss-mat-r2/output/{key}_six_views_raw.png"
dims=(.48,.14,.32)
dirs=("front","right","rear","left","top","bottom")


def low_mesh(g):
    x,y,z=g
    base=oval(g,(-.002,.078,-.014),(.385,.155,.351))
    ret=base
    branches=[
        ((-.13,.12,-.05),(-.328,.31,-.24),(-.39,.45,-.39),.120),
        ((-.03,.12,-.067),(-.078,.44,-.24),(-.24,.78,-.38),.111),
        ((-.06,.12,-.008),(-.305,.33,.05),(-.464,.53,.129),.116),
        ((-.018,.141,.01),(-.141,.24,.205),(-.194,.31,.381),.12),
        ((.04,.142,.028),(.13,.29,.229),(.16,.44,.43),.12),
        ((.102,.153,-.052),(.21,.367,-.207),(.34,.544,-.38),.118),
        ((.093,.146,-.011),(.27,.38,-.058),(.429,.513,-.101),.12),
        ((.087,.14,.067),(.269,.29,.115),(.431,.42,.242),.107)
    ]
    for i,(a,b,c,r) in enumerate(branches):
        ret=union(ret,branch(g,[(a,r),(b,r*.91),(c,r*.67)],(1,1.33,.85)),.032)
        b=np.asarray(b)
        c=np.asarray(c)
        for side in (-1,1):
            outward=np.array([a[2]-c[2],0,c[0]-a[0]])
            stem=b*.85+c*.15
            tip=stem+side*.30*outward+.18*(c-b)+[0,.054,0]
            piece=branch(g,[(stem,r*.65),(tip,r*.54)],(1,1.2,.88))
            ret=union(ret,piece,.028)
    return ret


def read_source(path):
    pix=np.asarray(Image.open(path).convert("RGBA"))
    h,w=pix.shape[:2]
    ink=(pix[:,:,3]>=180)&(pix[:,:,1]>pix[:,:,2]*1.13)
    labels,_=ndi.label(ink)
    boxes=ndi.find_objects(labels)
    areas=np.bincount(labels.ravel())
    views={}
    rects={}
    masks={}
    for row in range(2):
        entries=[(size,i,box) for i,(size,box) in enumerate(zip(areas[1:], boxes),1)
                 if box is not None and h*row/2 <= (box[0].start+box[0].stop)/2<h*(row+1)/2]
        chosen=sorted(sorted(entries,reverse=True)[:3],key=lambda item:item[2][1].start+item[2][1].stop)
        if min(c[0] for c in chosen)<2000:
            raise ValueError("Could not locate six mat silhouettes")
        for i,(_,lab,(yr,xr)) in enumerate(chosen):
            name=dirs[3*row+i]
            data=pix[yr,xr,:3]
            mask=labels[yr,xr]==lab
            measure, indices=ndi.distance_transform_edt(~ndi.binary_erosion(mask),return_indices=True)
            views[name]=(data[indices[0],indices[1]],measure)
            rects[name]=[xr.start,yr.start,xr.stop,yr.stop]
            masks[name]=mask
    return views, rects, masks


def output():
    candidate.mkdir(parents=True,exist_ok=True)
    review=work/"review-input"/key
    review.mkdir(parents=True,exist_ok=True)
    art=candidate/"six-material-views-r2.png"
    shutil.copyfile(source,art)
    common_build.FORMS[key]=low_mesh
    v,f,report=fit_surface(key,dims,736)
    bounds=estimate_topology(v,f)
    assert len(f)<=1000 and bounds["connected_components"]==1 and bounds["open_edges"]==0 and bounds["nonmanifold_edges"]==0
    tri=v[f]
    fn=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    n=np.zeros_like(v)
    for k in range(3):
        np.add.at(n,f[:,k],fn)
    n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-10)
    fn/=np.maximum(np.linalg.norm(fn,axis=1)[:,None],1e-10)
    donors,rects,masks=read_source(art)
    x,y,z=dims
    spans={"front":[x,y],"rear":[x,y],"right":[z,y],"left":[z,y],"top":[x,z],"bottom":[x,z]}
    texture, uv, owner=texture_atlas(key,f,tri,n,fn,donors,spans)
    model=candidate/f"{key}.glb"
    editable=candidate/f"{key}.blend"
    make_glb(model,"Riverbank liverwort thallus",v,f,uv,texture,n)
    make_glb(review/f"{key}-gray.glb","Review gray",v,f,np.full((len(f)*3,2),.5,np.float32),
             Image.new("RGBA",(2,2),(161,166,166,255)),n)
    exchange=model.with_suffix(".npz")
    np.savez_compressed(exchange,vertices=v,faces=f)
    run=[str(common_build.blender),"-b","--python-exit-code","1","--python",
         str(common/"blend_source.py"),"--",str(model),"--editable-dir",str(candidate)]
    subprocess.run(run,check=True)
    exchange.unlink()
    verify=[str(common_build.blender),"-b",str(editable),"--python-exit-code","1","--python",
            str(root/"work/reef-expansion-20261123/verify_blend_source.py"),"--",str(candidate)]
    subprocess.run(verify,check=True)
    catalog={"id":key,"name":"溪床贴石藓片","label":"溪床贴石藓片","category":"plant","budget_type":"broadleaf_plant",
             "nominal_xyz_m":dims,"triangles":len(f),"model":str(model),"source_glb":str(model),
             "editable_source":str(editable),"source_intent":str(art),"validation":str(candidate/"validation.json"),
             "source_url":"https://www.britishbryologicalsociety.org.uk/learning/species-finder/riccardia-chamedryfolia/",
             "habitat":"淡水溪床硬附着的扁叶状枝体模块，参照溪生苔类，非定种。","user_acceptance":"pending"}
    evidence={**catalog,"geometry":{**report,**bounds,"contact_vertices":int((v[:,1]==0).sum())},
              "glb":inspect(model),"packed_blend_verified":True,"source_views":rects,"source_sha256":sha(art),
              "source_review":"R2 六面去除 R1 的大块承载木头，附着面留有真的红棕分支和低暖绿层片。用原图 alpha 安全阈值隔开半透明背景雾。",
              "material":{"filter":"nearest","atlas":1536,"owners":owner,"material_count":1},
              "status":"static_candidate_pending_native","motion":"低贴附着块，静态置景，根附着层仍为实体。"}
    common_build.write_json(candidate/"validation.json",evidence)
    common_build.write_json(candidate/"catalog-entry.json",catalog)


if __name__=="__main__":
    output()
