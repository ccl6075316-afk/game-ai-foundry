"""Bake source-coordinate dorsal/ventral grain charts from verified interior skin.

Keeps source and GLB bytes untouched. Charts transport native pixels across a
surface cross-section rather than enlarging a single side-projection row.
All donor coordinates and excluded fin/outline areas are exported for review.
"""
import argparse,hashlib,io,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from freeze_surface_ownership import read_glb,accessor

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def raster(uv,tri,w,h):
    mask=np.zeros((h,w),np.uint8)
    for face in tri:
        pts=np.rint(uv[face]*[w,h]).astype(np.int32)
        aa=pts[1]-pts[0];bb=pts[2]-pts[0]
        if abs(int(aa[0])*int(bb[1])-int(aa[1])*int(bb[0]))>.5: cv2.fillConvexPoly(mask,pts,255)
    return mask
def seam(error):
    cost=error.copy();parents=np.zeros(error.shape,np.int32)
    for y in range(1,len(cost)):
        prev=cost[y-1];options=np.stack([np.r_[np.inf,prev[:-1]],prev,np.r_[prev[1:],np.inf]])
        choices=options.argmin(0);parents[y]=np.arange(len(prev))+choices-1
        cost[y]+=options[choices,np.arange(len(prev))]
    path=np.empty(len(cost),np.int32);path[-1]=cost[-1].argmin()
    for y in range(len(cost)-1,0,-1):path[y-1]=parents[y,path[y]]
    return path
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game',type=Path,required=True);ap.add_argument('--parameters',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--species',nargs='*')
    a=ap.parse_args();parameters=json.loads(a.parameters.read_text(encoding='utf8'));profiles={};reports=[]
    own=json.loads((a.game/'assets/models/fish/motion/body-opacity.json').read_text())['profiles']
    surf=json.loads((a.game/'assets/models/fish/motion/surface-ownership.json').read_text())['profiles']
    a.output.mkdir(parents=True,exist_ok=True)
    for species,p in parameters['species'].items():
        if a.species and species not in a.species: continue
        if not p.get('enabled',True): continue
        model=a.game/'assets/models/fish'/(species+'.glb');assert sha(model)==p['model_sha256']
        d,b=read_glb(model);candidates=[]
        for node in d['nodes']:
            if 'mesh' not in node or node['name'] in surf[species]['fins']:continue
            if node['name'] in own[species].get('decorative_overlays',{}) or node['name'] in own[species]['suppressed_auxiliary']:continue
            for si,pr in enumerate(d['meshes'][node['mesh']]['primitives']):
                mat=d['materials'][pr['material']];t=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
                if not t:continue
                pos=accessor(d,b,pr['attributes']['POSITION'])
                candidates.append((float(np.ptp(pos[:,0])),node,si,pr,d['textures'][t['index']]['source']))
        _,node,si,pr,ti=max(candidates,key=lambda v:v[0]);assert not any(k in node for k in ['matrix','translation','rotation','scale'])
        image=d['images'][ti];view=d['bufferViews'][image['bufferView']];encoded=bytes(b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])
        rgba=np.array(Image.open(io.BytesIO(encoded)).convert('RGBA'));h,w=rgba.shape[:2]
        v=accessor(d,b,pr['attributes']['POSITION']);uv=accessor(d,b,pr['attributes']['TEXCOORD_0']);tri=accessor(d,b,pr['indices']).reshape(-1,3)
        body=raster(uv,tri,w,h);finmask=np.zeros((h,w),np.uint8)
        for n in d['nodes']:
            if 'mesh' not in n or n.get('name') not in surf[species]['fins']:continue
            for q in d['meshes'][n['mesh']]['primitives']:
                tex=d['materials'][q['material']].get('pbrMetallicRoughness',{}).get('baseColorTexture')
                if not tex or d['textures'][tex['index']]['source']!=ti:continue
                finmask=np.maximum(finmask,raster(accessor(d,b,q['attributes']['TEXCOORD_0']),accessor(d,b,q['indices']).reshape(-1,3),w,h))
        margin=int(p['outline_exclusion_pixels']);radius=max(2,int(p['patch_pixels'])//2)
        body_safe=cv2.erode(body,np.ones((margin*2+1,margin*2+1),np.uint8))
        fin_exclude=cv2.dilate(finmask,np.ones((margin+1,margin+1),np.uint8))
        valid=(body_safe>0)&(fin_exclude==0)&(rgba[:,:,3]>=250)
        for rect in p.get('protected_source_rects',[]):
            x0,y0,x1,y1=np.rint(np.array(rect)*[w,h,w,h]).astype(int);valid[max(0,y0):min(h,y1),max(0,x0):min(w,x1)]=False
        centers=cv2.erode(valid.astype(np.uint8),np.ones((radius*2+1,radius*2+1),np.uint8))>0
        ys,xs=np.where(centers);assert len(xs)>200,(species,'No clean patch donors')
        tree=cKDTree(np.column_stack([xs,ys]));column=np.arange(w)
        tops=np.full(w,np.nan);bottoms=np.full(w,np.nan)
        for x in column:
            rows=np.flatnonzero(body[:,x]);
            if len(rows):tops[x]=rows[0];bottoms[x]=rows[-1]
        known=np.flatnonzero(np.isfinite(tops));assert len(known)>20
        tops=np.interp(column,known,tops[known]);bottoms=np.interp(column,known,bottoms[known])
        chart_h=int(p['chart_height']);block=int(p['patch_pixels']);overlap=max(3,block//3);step=block-overlap;maps=[];textures=[];used=np.zeros((h,w),np.uint8)
        # Native two-dimensional patches, with donor centers constrained to the
        # nearest safe whole patch. Never take ink/fin/alpha-nearest boundary.
        for kind,edge,sign in [('dorsal',tops,1),('ventral',bottoms,-1)]:
            grid_y=np.arange(h)[:,None];middle=(tops+bottoms)[None,:]*.5
            kind_valid=valid & ((grid_y<=middle) if kind=='dorsal' else (grid_y>=middle))
            # Anatomical half alone is insufficient: spots from the upper
            # flank must not become new dorsal markings. Freeze a reviewed
            # two-dimensional donor domain for each reconstructed surface.
            if kind in p.get('donor_domains_px',{}):
                domain=np.zeros((h,w),np.uint8)
                for polygon in p['donor_domains_px'][kind]:
                    cv2.fillPoly(domain,[np.rint(polygon).astype(np.int32)],255)
                kind_valid &= domain>0
            kind_centers=cv2.erode(kind_valid.astype(np.uint8),np.ones((radius*2+1,radius*2+1),np.uint8))>0
            ys,xs=np.where(kind_centers);assert len(xs)>100,(species,kind,'No same-side clean skin donors')
            tree=cKDTree(np.column_stack([xs,ys]))
            mapping=np.zeros((chart_h,w,2),np.int32);filled=np.zeros((chart_h,w),bool)
            for yy in range(0,chart_h,step):
                for xx in range(0,w,step):
                    bh=min(block,chart_h-yy);bw=min(block,w-xx)
                    cx=xx+bw//2;desired=[cx,edge[cx]+sign*(margin+radius+yy+bh//2)]
                    _,near=tree.query(desired,k=min(16,len(xs)))
                    dy,dx=np.mgrid[:bh,:bw];over=filled[yy:yy+bh,xx:xx+bw]
                    oldmap=mapping[yy:yy+bh,xx:xx+bw]
                    existing=rgba[oldmap[:,:,1],oldmap[:,:,0],:3].astype(float)
                    best=None;bestcost=np.inf
                    for idx in np.atleast_1d(near):
                        sx=int(xs[idx])+dx-bw//2;sy=int(ys[idx])+sign*(dy-bh//2)
                        candidate=rgba[sy,sx,:3].astype(float)
                        error=((candidate-existing)**2).mean(2)
                        score=float(error[over].mean()) if over.any() else 0.
                        score+=.03*((int(xs[idx])-desired[0])**2+(int(ys[idx])-desired[1])**2)
                        if score<bestcost:bestcost=score;best=(sx,sy,error)
                    sx,sy,error=best
                    assert kind_valid[sy,sx].all(),(species,kind,'Invalid surface-specific donor')
                    keep=np.zeros((bh,bw),bool)
                    if xx:
                        n=min(overlap,bw);path=seam(error[:,:n]);keep|=np.arange(bw)[None,:]<path[:,None]
                    if yy:
                        n=min(overlap,bh);path=seam(error[:n,:].T);keep|=np.arange(bh)[:,None]<path[None,:]
                    replace=~(keep&over)
                    oldmap[:,:,0][replace]=sx[replace];oldmap[:,:,1][replace]=sy[replace]
                    filled[yy:yy+bh,xx:xx+bw]=True
            colors=rgba[mapping[:,:,1],mapping[:,:,0]].copy();colors[:,:,3]=255
            target=a.output/f'{species}-{kind}.png';Image.fromarray(colors).save(target)
            used[mapping[:,:,1],mapping[:,:,0]]=255
            mapfile=a.output/f'{species}-{kind}-donors.npz';np.savez_compressed(mapfile,xy=mapping)
            maps.append({'kind':kind,'map':str(mapfile),'sha256':sha(mapfile)})
            textures.append({'path':'res://assets/models/fish/motion/surface112/'+target.name,'sha256':sha(target)})
        Image.fromarray(np.dstack([valid.astype(np.uint8)*255,fin_exclude,used,np.full((h,w),255,np.uint8)])).save(a.output/f'{species}-donor-review.png')
        # True skin triangle intersections supply cross-section positions; no
        # borrowed species envelope and no geometry or anatomy change.
        xyz=v[tri].astype(float);stations=np.linspace(float(v[:,0].min())+1e-6,float(v[:,0].max())-1e-6,128);sections=[]
        for x in stations:
            hits=[]
            for i,j in [(0,1),(1,2),(2,0)]:
                aa=xyz[:,i];zz=xyz[:,j];mask=(np.minimum(aa[:,0],zz[:,0])<=x)&(np.maximum(aa[:,0],zz[:,0])>=x)&(np.abs(zz[:,0]-aa[:,0])>1e-12)
                t=(x-aa[mask,0])/(zz[mask,0]-aa[mask,0]);hits.append(aa[mask]+t[:,None]*(zz[mask]-aa[mask]))
            points=np.concatenate(hits)
            if len(points)<4:continue
            low=points.min(0);high=points.max(0)
            sections.append([x,(low[1]+high[1])*.5,max((high[1]-low[1])*.5,1e-6),max((high[2]-low[2])*.5,1e-6)])
        fit=np.linalg.lstsq(np.column_stack([v[:,0],np.ones(len(v))]),uv[:,0],rcond=None)[0]
        # Anatomical marks are never inferred from this sampling field.
        profiles[species]={'model_sha256':p['model_sha256'],'mesh':node['name'],'surface':si,'source_embedded_sha256':hashlib.sha256(encoded).hexdigest(),'source_size':[w,h],'u_affine':fit.tolist(),'pixel_per_native':abs(float(fit[0]))*w,'chart_height':chart_h,'sections':sections,'dorsal':textures[0],'ventral':textures[1],'normal_blend':p['normal_blend'],'longitudinal_u':p['longitudinal_u']}
        reports.append({'species':species,'source_sha256':hashlib.sha256(encoded).hexdigest(),'model_sha256':p['model_sha256'],'clean_donor_pixels':int(valid.sum()),'used_donor_pixels':int((used>0).sum()),'donors_outside_valid':int(((used>0)&~valid).sum()),'maps':maps,'source_bytes_unchanged':True,'model_bytes_unchanged':True,'limits':'Chart reconstruction uses source interior skin as an artistic continuation, not observed hidden skin. Native patch seams require actual multi-view review.'})
        print('SURFACE_CHART',species,flush=True)
    (a.output/'surface-charts.json').write_text(json.dumps({'schema_version':1,'profiles':profiles},indent=2)+'\n',encoding='utf8')
    (a.output/'build.validation.json').write_text(json.dumps({'ok':bool(reports),'parameters_sha256':sha(a.parameters),'script_sha256':sha(__file__),'items':reports},indent=2)+'\n')
if __name__=='__main__':main()
