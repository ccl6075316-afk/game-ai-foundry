"""Bake a bounded model-space ventral skin repair into disjoint packed UV charts.

Existing mouth/fin/side charts and alpha are protected; the donor is an inspected
two-dimensional native skin patch. No geometry or UV is changed by this baker.
"""
import argparse,hashlib,json,sys
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays
from audit_transverse_width import section
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def raster(uv,W,H):
    pixel=uv*np.array([W,H]);lo=np.maximum(np.floor(pixel.min(0)-1).astype(int),0);hi=np.minimum(np.ceil(pixel.max(0)+1).astype(int),[W-1,H-1]);x,y=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));points=np.stack([x+.5,y+.5],axis=-1)
    mat=np.stack([pixel[1]-pixel[0],pixel[2]-pixel[0]],axis=1)
    if abs(np.linalg.det(mat))<1e-12:return None
    st=(points-pixel[0])@np.linalg.inv(mat).T;bary=np.stack([1-st.sum(-1),st[:,:,0],st[:,:,1]],axis=-1)
    # 1px shader footprint padding is evaluated at its nearest real triangle point.
    edge=min(np.linalg.norm(pixel[1]-pixel[0]),np.linalg.norm(pixel[2]-pixel[0]),np.linalg.norm(pixel[2]-pixel[1]));allow=1.1/max(edge,1)
    keep=(bary>=-allow).all(-1);bary=np.maximum(bary[keep],0);bary/=bary.sum(1)[:,None]
    return x[keep],y[keep],bary
def main(a):
    c=json.loads(a.config.read_text(encoding='utf8'));out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists()
    model=ROOT/c['model'];donorpath=ROOT/c['donor'];assert sha(model)==c['model_sha256'] and sha(donorpath)==c['donor_sha256']
    d,b=read_glb(model);p=d['meshes'][0]['primitives'][0];v=arrays(d,b,p['attributes']['POSITION']);uv=arrays(d,b,p['attributes']['TEXCOORD_0']);idx=arrays(d,b,p['indices']).reshape(-1,3);view=d['bufferViews'][d['images'][0]['bufferView']];raw=np.array(Image.open(BytesIO(b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])).convert('RGBA'));H,W=raw.shape[:2];fixed=raw.copy()
    parts=d['extras']['geometry_parts'];body=np.concatenate([idx[q['index_start']//3:(q['index_start']+q['index_count'])//3] for q in parts if q['role']in ['body_skin','mouth']]);mouth=np.concatenate([v[q['vertex_start']:q['vertex_start']+q['vertex_count']] for q in parts if q['role']=='mouth']);tree=cKDTree(mouth)
    xx=np.linspace(c['x_window'][0]-.01,c['x_window'][-1]+.01,100);bounds=np.array([[section(v,body.reshape(-1),x)[:,1].min(),section(v,body.reshape(-1),x)[:,1].max()] for x in xx]);donor=np.array(Image.open(donorpath).convert('RGBA'));DH,DW=donor.shape[:2]
    weightmap=np.zeros((H,W),np.float32);protected=np.zeros((H,W),bool);touched_faces=0
    for q in parts:
        for tri in idx[q['index_start']//3:(q['index_start']+q['index_count'])//3]:
            result=raster(uv[tri],W,H)
            if result is None:continue
            px,py,bary=result
            if q['name']!=c['body_chart']:
                protected[py,px]=True;continue
            pos=bary@v[tri];low=np.interp(pos[:,0],xx,bounds[:,0]);high=np.interp(pos[:,0],xx,bounds[:,1]);fraction=((low+high)/2-pos[:,1])/np.maximum((high-low)/2,1e-7)
            start,full,end,stop=c['x_window'];weight=smooth((pos[:,0]-start)/(full-start))*(1-smooth((pos[:,0]-end)/(stop-end)));weight*=smooth((fraction-c['underside_fade'][0])/(c['underside_fade'][1]-c['underside_fade'][0]));distance=tree.query(pos)[0];weight*=smooth((distance-c['mouth_protection_native'])/c['mouth_fade_native']);take=weight>1e-6
            if not take.any():continue
            touched_faces+=1;px=px[take];py=py[take];weight=weight[take];pos=pos[take]
            # Native-density x/transverse chart through a whole 2D quilt, not
            # copied side gills or a clamped donor row.
            sx=np.floor((pos[:,0]-start)*c['native_source_width']).astype(int)%DW;sy=np.floor(pos[:,2]*c['native_source_width']+DH/2).astype(int)%DH;sample=donor[sy,sx];assert np.all(sample[:,3]==255)
            replace=weight>weightmap[py,px];px=px[replace];py=py[replace];w=weight[replace];sample=sample[replace]
            fixed[py,px,:3]=np.rint(raw[py,px,:3]*(1-w[:,None])+sample[:,:3]*w[:,None]).astype('uint8');weightmap[py,px]=w
    changed=np.any(raw!=fixed,axis=2);assert changed.any() and not np.any(changed&protected),'Patch overlaps a protected mouth/fin/side chart'
    assert np.array_equal(raw[:,:,3],fixed[:,:,3]);assert np.array_equal(raw[weightmap==0],fixed[weightmap==0])
    out.mkdir(parents=True);Image.fromarray(fixed).save(out/'atlas.png');Image.fromarray(np.rint(weightmap*255).astype('uint8')).save(out/'patch-mask.png')
    report={'ok':True,'kind':'bounded_native_ventral_skin_bake','species':c['species'],'model_sha256':sha(model),'config_sha256':sha(a.config),'donor_sha256':sha(donorpath),'atlas_sha256':sha(out/'atlas.png'),'changed_pixels':int(changed.sum()),'touched_faces':touched_faces,'alpha_exact':True,'protected_mouth_fin_side_chart_changed_pixels':0,'outside_mask_RGBA_exact':True,'scope':'Color-only underside chart. Full mouth, native lip semantic charts, source lateral art and all fin charts are excluded; body geometry/UV are not modified.','parameters':c,'formal_acceptance':False};(out/'material.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'changed_pixels':int(changed.sum()),'touched_faces':touched_faces}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);main(p.parse_args())
