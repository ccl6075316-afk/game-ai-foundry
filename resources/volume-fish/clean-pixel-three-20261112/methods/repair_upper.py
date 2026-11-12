"""Continuous surface-angle bake across native dorsal/side UV seams."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from PIL import Image
from bake_three import (WORK,ROOT,Donor,body_mask,read_image,read_glb,read_parts,load_image_chart,raster,smooth,digest,sha,export_image_candidate)

class Surface:
    def __init__(self,skin):
        vertices=np.concatenate([p['pos'] for p in skin])
        self.lo,self.hi=vertices[:,0].min(),vertices[:,0].max()
        self.x=np.linspace(self.lo+1e-7,self.hi-1e-7,1537)
        es=np.concatenate([p['pos'][p['faces'][:,[0,1,1,2,2,0]].reshape(-1,2)] for p in skin])
        a,b=es[:,0],es[:,1]; dx=b[:,0]-a[:,0]
        keep=np.abs(dx)>1e-9;a,b,dx=a[keep],b[keep],dx[keep]
        rows=[]
        for x in self.x:
            t=(x-a[:,0])/dx;k=(t>=-1e-6)&(t<=1+1e-6)
            q=a[k]+t[k,None]*(b[k]-a[k]);rows.append([q[:,1].min(),q[:,1].max(),q[:,2].min(),q[:,2].max()])
        self.bounds=np.array(rows)
    def coordinates(self,pos):
        limits=np.array([np.interp(pos[:,0],self.x,self.bounds[:,i]) for i in range(4)]).T
        yl,yh,zl,zh=limits.T
        y=(pos[:,1]-(yl+yh)*.5)/np.maximum((yh-yl)*.5,1e-5)
        z=(pos[:,2]-(zl+zh)*.5)/np.maximum((zh-zl)*.5,1e-5)
        theta=np.arctan2(y,np.abs(z))
        return (pos[:,0]-self.lo)/(self.hi-self.lo),theta,y

def main():
    ap=argparse.ArgumentParser();ap.add_argument('species');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    s=args.species;out=args.output.resolve();assert s in ['zander','african_catfish'] and out.is_relative_to(WORK) and not out.exists()
    source=WORK/s/'candidate/fish.glb';doc,blob=read_glb(source);parts=read_parts(doc,blob)
    skin=[p for p in parts if p['node']=='Closed_body' and p['material']!='Front mouth oral chart']
    originals={i:load_image_chart(doc,blob,i) for i in range(len(doc['images']))}
    result={i:im.copy() for i,im in originals.items()};ids={p['image'] for p in skin}
    protected={i:np.zeros(result[i].shape[:2],bool) for i in ids}
    for p in parts:
        i=p['image']
        if i not in ids or p in skin:continue
        h,w=protected[i].shape
        for face in p['faces']:
            pix,_,_=raster(p['uv'][face],w,h,2.);protected[i][pix[:,1],pix[:,0]]=True
    donor_im=read_image(WORK/s/'body-side-r3.png');donor=Donor(donor_im,body_mask(donor_im),1)
    surface=Surface(skin);ranks={i:np.zeros(im.shape[:2],np.float32) for i,im in result.items()}
    left,right,upper,lower=donor.bounds;changed=[]
    for p in skin:
        i=p['image'];h,w=ranks[i].shape
        for face in p['faces']:
            pix,bary,rank=raster(p['uv'][face],w,h,2.)
            x,y=pix.T;keep=(rank>ranks[i][y,x])&~protected[i][y,x]
            x,y,bary,rank=x[keep],y[keep],bary[keep],rank[keep]
            if not len(x):continue
            pos=bary@p['pos'][face];u,theta,height=surface.coordinates(pos)
            cross=.055+.89*(.5-theta/np.pi)
            sx=left+np.clip(u,0,1)*(right-left);ix=np.rint(sx).astype(int)
            sy=upper[ix]+cross*(lower[ix]-upper[ix])
            color=donor.sample(sx,sy)
            # Continuous surface coordinates, never split render normals.
            # Full dorsal replacement removes previous mismatched axial donor.
            weight=smooth((height-.03)/.42)*(1-smooth((u-.70)/.17))*smooth((u-.008)/.045)
            # Source painting supplies scale/mottle position on both sides and back.
            old=originals[i][y,x,:3].astype(float)
            result[i][y,x,:3]=np.rint(old*(1-weight[:,None])+color*weight[:,None]).astype('uint8')
            ranks[i][y,x]=rank
    out.mkdir(parents=True)
    patches={}
    for i in ids:
        assert np.array_equal(result[i][protected[i]],originals[i][protected[i]])
        assert np.array_equal(result[i][:,:,3],originals[i][:,:,3])
        path=out/f'image-{i}.png';Image.fromarray(result[i]).save(path)
        patches[str(i)]={'path':str(path),'sha256':sha(path),'changed_rgb_texels':int(np.any(result[i][:,:,:3]!=originals[i][:,:,:3],2).sum())}
    # Body stage has original formal fins; accepted candidate fin pixels return only after body review.
    baseline=ROOT/'projects/fishing-2d/game/assets/models/fish'/f'{s}.glb';bd,bb=read_glb(baseline)
    baseparts=read_parts(bd,bb)
    fin_ids={p['image'] for p in parts if p['node']!='Closed_body' and 'eye' not in p['node'].lower()}
    for i in fin_ids:
        base=next(p for p in baseparts if p['node']==next(p['node'] for p in parts if p['image']==i))
        path=out/f'original-fin-{i}.png';Image.fromarray(load_image_chart(bd,bb,base['image'])).save(path)
        patches[str(i)]={'path':str(path),'sha256':sha(path),'stage_restore_original_fin':True}
    target=out/'fish.glb';export_image_candidate(doc,blob,target,{int(i):Path(p['path']) for i,p in patches.items()})
    report={'ok':True,'species':s,'stage':'body','model_sha256':sha(target),'input_model_sha256':sha(source),'changed_images':patches,'body_rgba':{str(i):digest(result[i]) for i in sorted(ids)},'alpha_exact':True,'source':str(WORK/s/'body-side-r3.png'),'source_sha256':sha(WORK/s/'body-side-r3.png'),'method':'single continuous circumferential angle field from native finite section envelope; per-UV normals excluded','protected_texels':{str(i):int(v.sum()) for i,v in protected.items()},'donor_fallback':donor.fallback}
    (out/'bake.validation.json').write_text(json.dumps(report,indent=2)+'\n')
    cfg=json.loads((WORK/s/'candidate/capture-body.json').read_bytes());cfg.update(model=str(target),model_sha256=sha(target),output=str(WORK/'experiments'/s/out.name))
    cfg['views'] += [{'name':'dorsal-oblique','direction':[.2,1,.65],'focus':[0,0,0],'width_m':cfg['views'][0]['width_m']}]
    (out/'capture.json').write_text(json.dumps(cfg,indent=2)+'\n');print(s,sha(target),sum(p.get('changed_rgb_texels',0) for p in patches.values()))
if __name__=='__main__':main()
