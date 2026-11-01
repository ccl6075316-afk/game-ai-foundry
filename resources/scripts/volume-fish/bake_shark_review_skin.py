"""Bake continuous angular shark skin from explicit two-dimensional native donors.

No runtime material construction. Fin uppers and the source inputs remain exact;
the countershaded undersides and unseen back/belly are documented derivations.
"""
import argparse, hashlib, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def sample(a,x,y):
    return a[np.clip(np.rint(y).astype(int),0,a.shape[0]-1),np.clip(np.rint(x).astype(int),0,a.shape[1]-1),:3]

def neutralize_donor_lighting(source,rects):
    """Remove native painted low-frequency illumination only in hidden donors.

    This is explicit derived albedo, not a claim of exact original RGB. Pixel
    clusters remain in their original resolution and the lateral art is intact.
    """
    mask=np.zeros(source.shape[:2],np.float32)
    for x0,y0,x1,y1 in rects:mask[y0:y1,x0:x1]=1
    rgb=source[:,:,:3].astype(np.float32);den=cv2.GaussianBlur(mask,(0,0),12)
    low=cv2.GaussianBlur(rgb*mask[:,:,None],(0,0),12)/np.maximum(den[:,:,None],1e-8)
    target=np.median(rgb[mask>0],axis=0)
    result=source.copy();result[:,:,:3]=np.clip(np.rint(rgb+target-low),0,255).astype(np.uint8)
    return result,{'target_rgb':target.tolist(),'method':'Masked 12px low-frequency lighting removal in explicit native donor rectangles; source pixel detail retained, donor RGB is derived.'}

def quilt(source, rects, width, height, seed):
    """Native 24px patches, overlap error cuts; save every selected donor XY."""
    rng=np.random.default_rng(seed);block=24;overlap=8;step=block-overlap
    mask=np.zeros(source.shape[:2],np.uint8)
    for x0,y0,x1,y1 in rects: mask[y0:y1,x0:x1]=1
    safe=cv2.erode(mask,np.ones((block,block),np.uint8))>0
    ys,xs=np.where(safe);assert len(xs)>100
    result=np.zeros((height+block,width+block,3),np.uint8)
    donor=np.zeros((height+block,width+block,2),np.uint16)
    for y in range(0,height,step):
        for x in range(0,width,step):
            ids=rng.choice(len(xs),min(96,len(xs)),replace=False)
            candidates=np.array([source[ys[i]-12:ys[i]+12,xs[i]-12:xs[i]+12,:3] for i in ids])
            current=result[y:y+block,x:x+block]
            cost=np.zeros(len(ids))
            if x:cost+=((candidates[:,:,:overlap].astype(float)-current[None,:,:overlap])**2).mean((1,2,3))
            if y:cost+=((candidates[:,:overlap].astype(float)-current[None,:overlap])**2).mean((1,2,3))
            best=int(np.argmin(cost));i=ids[best];patch=candidates[best]
            take=np.ones((block,block),bool)
            # Dynamic-programming seam, independently on the two overlaps.
            error=((patch.astype(float)-current)**2).mean(2)
            for vertical in [True,False]:
                if not (x if vertical else y):continue
                e=error[:,:overlap] if vertical else error[:overlap,:].T
                acc=e.copy();parent=np.zeros(e.shape,np.int32)
                for r in range(1,block):
                    for c in range(overlap):
                        lo=max(0,c-1);hi=min(overlap,c+2);j=lo+int(np.argmin(acc[r-1,lo:hi]));acc[r,c]+=acc[r-1,j];parent[r,c]=j
                path=np.zeros(block,np.int32);path[-1]=int(np.argmin(acc[-1]))
                for r in range(block-1,0,-1):path[r-1]=parent[r,path[r]]
                keep=np.arange(block)[None,:]<path[:,None]
                take&=~(keep if vertical else keep.T)
            current[take]=patch[take]
            yy,xx=np.mgrid[ys[i]-12:ys[i]+12,xs[i]-12:xs[i]+12]
            view=donor[y:y+block,x:x+block];view[take]=np.stack([xx,yy],-1)[take]
    result=result[:height,:width];donor=donor[:height,:width]
    assert np.array_equal(result,source[donor[:,:,1],donor[:,:,0],:3])
    assert mask[donor[:,:,1],donor[:,:,0]].all()
    return result,donor

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    c=json.loads(a.config.read_text(encoding='utf-8'));out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();out.mkdir()
    source=np.array(Image.open(ROOT/c['side_source']).convert('RGBA'));clean=np.array(Image.open(ROOT/c['clean_side']).convert('RGB'));front=np.array(Image.open(ROOT/c['front_source']).convert('RGB'))
    profile=json.loads((ROOT/c['legacy_profile']).read_text());sec=np.array(profile['body']['sections']);H,W=source.shape[:2];ah=c['angular_height']
    backsrc,backlight=neutralize_donor_lighting(source,c['back_donor_rects_px']);bellysrc,bellylight=neutralize_donor_lighting(source,c['belly_donor_rects_px'])
    back,bxy=quilt(backsrc,c['back_donor_rects_px'],W,ah,153);belly,vxy=quilt(bellysrc,c['belly_donor_rects_px'],W,ah,154)
    for name,pixels in [('back-quilt',back),('belly-quilt',belly)]:Image.fromarray(pixels).save(out/(name+'.png'))
    np.savez_compressed(out/'native-donors.npz',back_xy=bxy,belly_xy=vxy)
    yy,xx=np.mgrid[:ah,:W];u=(xx+.5)/W;theta=(yy+.5)/ah*np.pi*2;co=np.cos(theta);si=np.sin(theta)
    top=np.interp(u,sec[:,0],sec[:,1]);bottom=np.interp(u,sec[:,0],sec[:,2]);v=(top+bottom)/2-(bottom-top)/2*co
    side=sample(clean,u*W-.5,v*H-.5).astype(float)
    wb=smooth(.38,.88,co);wv=smooth(.48,.90,-co)
    # Actual eye and gill support stays lateral, never rolled onto the roof.
    protected=(((u>.902)&(u<.935)&(v>.49)&(v<.568))|((u>.725)&(u<.815)&(v>.49)&(v<.69))) & (np.abs(si)>.86)
    wb[protected]=0;wv[protected]=0
    result=side*(1-wb-wv)[:,:,None]+back*wb[:,:,None]+belly*wv[:,:,None]
    # The full anterior cap uses only the own frontal central skin, above its
    # native mouth line. No duplicate eyes or painted mouth on the nose.
    half=np.interp(u,sec[:,0],sec[:,3]);trans=half*si
    fx=(.5+trans/.16*.52862)*front.shape[1]-.5
    fv=.363914+(v-.307443)/(.781553-.307443)*(.940367-.363914)
    fv=np.clip(fv,.42,.705)
    frontal=sample(front,fx,fv*front.shape[0]-.5)
    fw=smooth(.960,.992,u)
    result=result*(1-fw)[:,:,None]+frontal*fw[:,:,None]
    result=np.clip(np.rint(result),0,255).astype(np.uint8)
    # Periodic roof seam shares one exact native strip on both ends.
    result[-1]=result[0]
    Image.fromarray(result).save(out/'body-angular.png')
    # Opposite surfaces of paired fins do not share their dark upper pigment.
    vent=source[:,:,:3].copy();orig=source[:,:,:3];counter=belly[:H] if ah>=H else None
    donorrect=c['fin_ventral_donor_rect_px'];x0,y0,x1,y1=donorrect
    py,px=np.mgrid[:H,:W];sx=x0+(px%(x1-x0));sy=y0+(py%(y1-y0));under=orig[sy,sx]
    finmask=np.zeros((H,W),np.uint8);keep=np.zeros((H,W),np.uint8)
    for row in c['paired_fin_domains']:
        cv2.fillPoly(finmask,[np.rint(np.array(row['polygon'])*[W,H]).astype(np.int32)],1)
        cv2.fillPoly(keep,[np.array(row['protected_tip_px'],np.int32)],1)
    # This chart is exclusive to paired-fin lower tissue, including the whole
    # basal band. A profile's smaller free-fin polygon must not leave old body
    # pigment on the rest of that lower surface.
    vent=under.copy();vent[keep>0]=orig[keep>0]
    # Opaque finite walls are padded from their own anatomical fin, not black
    # transparent pixels. Preserve the original input and all upper-fin RGB.
    from scipy.ndimage import distance_transform_edt
    valid=source[:,:,3]>240;ids=distance_transform_edt(~valid,return_distances=False,return_indices=True);vent=vent[ids[0],ids[1]]
    Image.fromarray(vent).save(out/'paired-fin-ventral.png')
    upper=orig[ids[0],ids[1]]
    Image.fromarray(np.concatenate([upper,vent],axis=1)).save(out/'fin-two-sided.png')
    record={'ok':True,'kind':'continuous_shark_native_surface_chart','config':str(a.config.resolve()),'config_sha256':sha(a.config),'source_sha256':sha(ROOT/c['side_source']),'front_source_sha256':sha(ROOT/c['front_source']),'body_chart_sha256':sha(out/'body-angular.png'),'underside_chart_sha256':sha(out/'paired-fin-ventral.png'),'native_donor_xy_sha256':sha(out/'native-donors.npz'),'back_donor_rects_px':c['back_donor_rects_px'],'belly_donor_rects_px':c['belly_donor_rects_px'],'side_features_lateral_only':True,'continuous_angular_weights':True,'front_mouth_line_excluded':True,'formal_acceptance':False,'scope':'Two-dimensional native quilts and explicit source blending. Unseen pattern continuation and fin countershading are art derivations, not measured biology. Exact original source and upper-fin pixels retained.'}
    record['hidden_donor_lighting']={'back':backlight,'belly':bellylight};record['fin_atlas_sha256']=sha(out/'fin-two-sided.png')
    (out/'validation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record))
if __name__=='__main__':main()
