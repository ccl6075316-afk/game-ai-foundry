"""Pack explicit nasal source ownership beside existing lip continuity records.

Uses unchanged native source cells and static candidate coordinates. The two
layers share one atlas and lookup sampler so Compatibility budgets stay stable.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',required=True,type=Path);a=ap.parse_args()
    plan=json.loads(a.plan.read_text());out=Path(plan['output']);out.mkdir(parents=True,exist_ok=True)
    for p,h in plan['frozen_inputs'].items(): assert sha(p)==h,p
    source=np.asarray(Image.open(plan['source']).convert('RGBA'))
    x0,y0,x1,y1=plan['donor_rect'];patch=source[y0:y1,x0:x1].copy()
    assert patch.size and np.all(patch[:,:,3]==255)
    assert np.all(patch[:,:,:3].max(2)>80),'Donor includes dark facial feature'
    yy,xx=np.indices(patch.shape[:2]);xx+=x0;yy+=y0
    if plan.get('native_pixel_density'):
        domain=plan['donor_mapping'];density=plan['native_pixel_density']
        width=max(2,round((domain['z_max']-domain['z_min'])*density))
        height=max(2,round((domain['y_max']-domain['y_min'])*density))
        def reflect(n,length):
            q=np.arange(n)%(2*length);return np.minimum(q,2*length-1-q)
        xs=reflect(width,patch.shape[1])+x0;ys=reflect(height,patch.shape[0])+y0
        yy,xx=np.meshgrid(ys,xs,indexing='ij');patch=source[yy,xx].copy()
    atlas=np.asarray(Image.open(plan['skin_atlas']).convert('RGBA'))
    h,w=atlas.shape[:2];ph,pw=patch.shape[:2];W=max(w,pw);H=h+ph
    packed=np.zeros((H,W,4),np.uint8);packed[:h,:w]=atlas;packed[h:,:pw]=patch
    lip=np.asarray(json.loads(Path(plan['skin_records']).read_text()))
    vertices=np.asarray(json.loads(Path(plan['body']).read_text())['parts'][0]['vertices'])
    assert len(lip)==len(vertices)
    lip[:,0]*=w/W;lip[:,1]*=h/H
    cfg=plan['support'];p=vertices
    weight=smooth((p[:,0]-cfg['start_x'])/(cfg['full_x']-cfg['start_x']))
    weight*=1-smooth((abs(p[:,2])-cfg['full_abs_z'])/(cfg['zero_abs_z']-cfg['full_abs_z']))
    weight*=smooth((p[:,1]-cfg['lower_y'])/(cfg['full_lower_y']-cfg['lower_y']))
    weight*=1-smooth((p[:,1]-cfg['full_upper_y'])/(cfg['upper_y']-cfg['full_upper_y']))
    domain=plan['donor_mapping'];u=np.clip((p[:,2]-domain['z_min'])/(domain['z_max']-domain['z_min']),0,1)
    v=np.clip((domain['y_max']-p[:,1])/(domain['y_max']-domain['y_min']),0,1)
    nose=np.c_[(.5+u*(pw-1))/W,(h+.5+v*(ph-1))/H,weight,np.zeros(len(p))]
    records=np.stack([lip,nose],axis=1).reshape(-1,4)
    Image.fromarray(packed).save(out/'ownership-atlas.png')
    (out/'ownership-records.json').write_text(json.dumps(records.tolist(),separators=(',',':')))
    # Every nasal atlas cell is an exact, opaque native source texel.
    donors=[[c,r,int(xx[r,c]),int(yy[r,c])] for r in range(ph) for c in range(pw)]
    (out/'nose-donors.json').write_text(json.dumps(donors,separators=(',',':')))
    result={'ok':True,'species':plan['species'],'plan_sha256':sha(a.plan),'source_sha256':sha(plan['source']),
            'nasal_vertices':int((weight>0).sum()),'source_pixels_modified':0,'record_stride':2,
            'outputs':{n:sha(out/n) for n in ['ownership-atlas.png','ownership-records.json','nose-donors.json']},
            'scope':'Explicit source skin ownership before lip continuity; candidate rest-space lookup. Visual and dynamic gates remain required.'}
    (out/'ownership.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
