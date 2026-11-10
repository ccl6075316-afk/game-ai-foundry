"""Bluegill-only donor registration into frozen original UVs. No geometry edits.

Two explicit stages: whole clean body donor first, then independently bake fins.
Fins use approved concept RGB. A checked body atlas is immutable during fin bake.
RGB-only texel bake; original alpha, nonimage GLB bytes and contracts preserved.
"""
from pathlib import Path
import argparse,copy,hashlib,io,json,struct,sys
import cv2,numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt,binary_fill_holes
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'resources/scripts/volume-fish/portable'))
from glb_io import read_glb,arrays
from parts import packed_arrays

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def image(p):return np.array(Image.open(p).convert('RGBA'))
def foreground(im):
    r,g,b=np.moveaxis(im[:,:,:3].astype(float),2,0)
    return (((r>g*.95)&(g>b*1.15))|(g>90)).astype(np.uint8)
def largest(mask):
    contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    out=np.zeros(mask.shape,np.uint8);cv2.drawContours(out,[max(contours,key=cv2.contourArea)],-1,1,-1)
    return out.astype(bool)
def extents(mask):
    yy,xx=np.where(mask);xs=np.unique(xx);lo=np.full(mask.shape[1],np.nan);hi=lo.copy()
    for x in xs:
        y=np.where(mask[:,x])[0];lo[x]=y.min();hi[x]=y.max()
    allx=np.arange(len(lo));return (int(xx.min()),int(xx.max()),np.interp(allx,xs,lo[xs]),np.interp(allx,xs,hi[xs]))
def projection(p,w,h,view='side'):
    if view=='side':return np.c_[(.5+p[:,0]/1.14)*w,(.5-p[:,1]/(1.14*620/900))*h]
    return np.c_[(.5+(p[:,0] if view=='top' else -p[:,0])/1.14)*w,(.5+p[:,2]/(1.14*620/900))*h]
def mask_for(p,tri,w,h,view='side'):
    coords=projection(p,w,h,view);mask=np.zeros((h,w),np.uint8)
    for ids in tri:cv2.fillConvexPoly(mask,np.rint(coords[ids]).astype(np.int32),1)
    return mask.astype(bool)
class Sampler:
    def __init__(self,im,mask,name):
        self.im=im[:,:,:3];self.mask=mask;self.name=name;self.dist,self.near=distance_transform_edt(~mask,return_indices=True);self.count=0;self.fallback=0;self.maximum=0.
    def sample(self,xy):
        h,w=self.mask.shape;xx=np.clip(np.rint(xy[:,0]).astype(int),0,w-1);yy=np.clip(np.rint(xy[:,1]).astype(int),0,h-1)
        d=self.dist[yy,xx];self.count+=len(xx);self.fallback+=int((d>0).sum());self.maximum=max(self.maximum,float(d.max(initial=0)))
        ny,nx=self.near[:,yy,xx];return self.im[ny,nx].astype(float)
    def report(self):return {'samples':self.count,'fallback_samples':self.fallback,'max_fallback_pixels':self.maximum}

def main(a):
    base=Path(__file__).resolve().parent;out=a.output.resolve();assert out.is_relative_to(base) and not out.exists();out.mkdir()
    state=json.loads((base/'manifest.json').read_text());assert state['user_style_acceptance']['status']=='accepted'
    assert sha(a.input)==state['model_sha256'] and sha(base/'style-concept-v1.png')==state['style_concept']['sha256']
    spec=json.loads((base/'parts-spec.json').read_text());doc,blob,node,prim,parts,attrs,indices,names,expected=packed_arrays(a.input,spec)
    P=attrs['POSITION'];N=attrs['NORMAL'];UV=attrs['TEXCOORD_0'];tri=indices.reshape(-1,3)
    concept=image(base/'style-concept-v1.png');ch,cw=concept.shape[:2]
    iv=doc['bufferViews'][doc['images'][0]['bufferView']];off=iv.get('byteOffset',0)
    old=np.array(Image.open(io.BytesIO(blob[off:off+iv['byteLength']])).convert('RGBA'));atlas=old.copy();H,W=old.shape[:2]
    frozen_body=np.zeros((H,W),bool)
    if a.stage=='fins':
        assert a.body_checkpoint is not None
        checkpoint=a.body_checkpoint.resolve();receipt=json.loads((checkpoint/'bake.validation.json').read_text())
        reviewed=json.loads((checkpoint/'body-review.validation.json').read_text())
        assert receipt['ok'] and reviewed['ok'] and reviewed['model_sha256']==sha(checkpoint/'fish.glb')
        assert sha(checkpoint/'atlas.png')==receipt['atlas_sha256']
        atlas=image(checkpoint/'atlas.png');frozen_body=np.load(checkpoint/'body-ownership.npz')['owned']
    starting_atlas=atlas.copy()
    body_tri=np.concatenate([indices[slice(*r['index_range'])].reshape(-1,3)for r in parts if r['role'] in ('body_skin','mouth')])
    bodymask=mask_for(P,body_tri,cw,ch)
    # The approved whole-fish plate is already in the same normalized camera.
    # Keep same-part nearest fallback finite and visible in the receipt.
    samplers={};fin_masks={}
    for r in parts:
        if r['role']!='fin':continue
        key=r['name'];mask=mask_for(P,indices[slice(*r['index_range'])].reshape(-1,3),cw,ch)
        mask=cv2.dilate(mask.astype(np.uint8),np.ones((5,5),np.uint8))>0
        if not key.startswith(('Pectoral','Pelvic')):mask &= ~(cv2.erode(bodymask.astype(np.uint8),np.ones((3,3),np.uint8))>0)
        rgb=concept[:,:,:3].astype(float);valid=foreground(concept).astype(bool)&(rgb[:,:,0]<rgb[:,:,1]*1.42)
        mask &= valid;mask=cv2.erode(mask.astype(np.uint8),np.ones((3,3),np.uint8))>0
        assert mask.sum()>30,key
        fin_masks[key]=mask;samplers[key]=Sampler(concept,mask,key)
    body=image(base/'body-donors-v1.png');bh,bw=body.shape[:2]
    # These boundaries are measured on this generated 1511x1041 sheet.
    panel_windows=[(0,520),(520,760),(760,bh)];panels=[];registrations=[]
    for view,(y0,y1) in zip(['side','top','bottom'],panel_windows):
        im=body[y0:y1];mask=largest(foreground(im));mask=cv2.erode(mask.astype(np.uint8),np.ones((3,3),np.uint8))>0
        src=extents(mask);template=extents(mask_for(P,body_tri,900,620,view))
        sampler=Sampler(im,mask,'body-'+view);samplers['body-'+view]=sampler;panels.append((view,sampler,src,template))
        registrations.append({'view':view,'panel_y':[y0,y1],'generated_x':[src[0],src[1]],'template_x':[template[0],template[1]],'method':'per-station same-body silhouette registration; no mesh modification'})
    def body_sample(p,q):
        view,s,src,t=panels[q];xy=projection(p,900,620,view);tx=np.clip(np.rint(xy[:,0]).astype(int),0,899)
        x=src[0]+(xy[:,0]-t[0])/(t[1]-t[0])*(src[1]-src[0])
        if q==0:
            # One continuous clean-body coordinate map. Head landmarks keep the
            # approved eye/opercular positions, without mixing separate body RGB.
            target_x=np.array([t[0],850*900/1511,1005*900/1511,1222*900/1511,1298*900/1511,t[1]])
            source_x=np.array([src[0],850,1017,1176,1243,src[1]])
            x=np.interp(xy[:,0],target_x,source_x)
        ix=np.clip(np.rint(x).astype(int),0,len(src[2])-1)
        ratio=(xy[:,1]-t[2][tx])/np.maximum(1,t[3][tx]-t[2][tx])
        if q==0:
            target_eye=(499*620/1041-t[2][tx])/np.maximum(1,t[3][tx]-t[2][tx])
            source_eye=(248-src[2][ix])/np.maximum(1,src[3][ix]-src[2][ix])
            target_eye=np.clip(target_eye,.08,.92);source_eye=np.clip(source_eye,.08,.92)
            mapped=np.where(ratio<target_eye,ratio*source_eye/target_eye,source_eye+(ratio-target_eye)*(1-source_eye)/(1-target_eye))
            head_weight=smooth((xy[:,0]*1511/900-1080)/100)
            ratio=ratio*(1-head_weight)+mapped*head_weight
        y=src[2][ix]+ratio*(src[3][ix]-src[2][ix]);return s.sample(np.c_[x,y])
    front=None
    if (base/'mouth-donor-v1.png').exists():
        front=image(base/'mouth-donor-v1.png');fh,fw=front.shape[:2]
        # Foreground skin only excludes dark interior for outer-body samples.
        fm=foreground(front).astype(bool);samplers['front-skin']=Sampler(front,fm,'front-skin');samplers['front-all']=Sampler(front,np.ones((fh,fw),bool),'front-all')
    head=None
    if (base/'head-donor-v1.png').exists():
        head=image(base/'head-donor-v1.png');hh,hw=head.shape[:2]
        samplers['forehead']=Sampler(head,foreground(head).astype(bool),'forehead')
    owner=np.full((H,W),-1,np.int16);weight=np.zeros((H,W),np.float32);records=[]
    for ordinal,r in enumerate(parts):
        if (a.stage=='body' and r['role']=='fin') or (a.stage=='fins' and r['role']!='fin'):continue
        start,end=r['index_range'];samples=0
        for ids in indices[start:end].reshape(-1,3):
            z=UV[ids]*[W,H]-.5;A=np.column_stack((z[1]-z[0],z[2]-z[0]));det=np.linalg.det(A)
            if abs(det)<1e-9:continue
            lo=np.maximum(np.floor(z.min(0)-2).astype(int),0);hi=np.minimum(np.ceil(z.max(0)+2).astype(int),[W-1,H-1])
            xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));points=np.c_[xx.ravel(),yy.ravel()]
            ab=(points-z[0])@np.linalg.inv(A).T;beta=np.c_[1-ab.sum(1),ab];distance=np.full(len(points),1e8)
            for a0,a1 in zip(z,np.roll(z,-1,axis=0)):
                e=a1-a0;t=np.clip(((points-a0)*e).sum(1)/max(e@e,1e-20),0,1);distance=np.minimum(distance,np.linalg.norm(points-(a0+t[:,None]*e),axis=1))
            take=(beta.min(1)>=-1e-7)|(distance<=1.25);points=points[take];beta=beta[take];dist=distance[take]
            priority=np.where(beta.min(1)>=-1e-7,3.,1/(1+dist));keep=priority>=weight[points[:,1],points[:,0]]
            points=points[keep];beta=np.maximum(beta[keep],0);beta/=beta.sum(1)[:,None];priority=priority[keep]
            if not len(points):continue
            p=beta@P[ids];n=beta@N[ids];n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-8)
            if r['role']=='fin':color=samplers[r['name']].sample(projection(p,cw,ch))
            else:
                side=body_sample(p,0)
                top=smooth((n[:,1]-.40)/.45);bottom=smooth((-n[:,1]-.40)/.45)
                color=side*(1-top-bottom)[:,None]+body_sample(p,1)*top[:,None]+body_sample(p,2)*bottom[:,None]
                if front is not None:
                    # Actual front camera: eye=(+X), screen right=-Z, up=+Y.
                    xy=np.c_[(.5-p[:,2]/.14)*fw,(.5-(p[:,1]+.045)/(.14*620/900))*fh]
                    f=samplers['front-all' if r['role']=='mouth' else 'front-skin'].sample(xy)
                    blend=smooth((p[:,0]-.415)/.045)
                    if r['role']=='mouth':blend=np.ones(len(p))
                    color=color*(1-blend[:,None])+f*blend[:,None]
                elif r['role']=='mouth':color=old[points[:,1],points[:,0],:3].astype(float)
                if head is not None and r['role']=='body_skin':
                    # Only central anterior skin; keep actual lateral eyes and
                    # selected side artwork, and keep the registered oral map.
                    blend=(1-smooth((np.abs(p[:,2])-.030)/.015))*smooth((p[:,0]-.30)/.05)*smooth((p[:,1]+.015)/.025)
                    active=blend>0
                    if active.any():
                        xy=np.c_[(.5-p[active,2]/.30)*hw,(.5-p[active,1]/.45)*hh]
                        f=samplers['forehead'].sample(xy)
                        color[active]=color[active]*(1-blend[active,None])+f*blend[active,None]
            if a.stage=='fins':
                assert not frozen_body[points[:,1],points[:,0]].any(), 'Fin atlas footprint overlaps frozen body ownership'
            atlas[points[:,1],points[:,0],:3]=np.rint(np.clip(color,0,255)).astype(np.uint8)
            owner[points[:,1],points[:,0]]=ordinal;weight[points[:,1],points[:,0]]=priority;samples+=len(points)
        records.append({'part':r['name'],'role':r['role'],'sampled_texels_with_overlap':samples})
    assert np.array_equal(old[:,:,3],atlas[:,:,3]);assert np.array_equal(starting_atlas[owner<0],atlas[owner<0])
    if a.stage=='body':np.savez_compressed(out/'body-ownership.npz',owned=owner>=0)
    else:assert np.array_equal(starting_atlas[frozen_body],atlas[frozen_body])
    ap=out/'atlas.png';Image.fromarray(atlas).save(ap)
    new=copy.deepcopy(doc);payload=bytearray(blob);payload.extend(b'\0'*(-len(payload)%4));offset=len(payload);png=ap.read_bytes();payload.extend(png)
    new['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(png)});new['images'][0]['bufferView']=len(new['bufferViews'])-1;new['buffers'][0]['byteLength']=len(payload)
    payload.extend(b'\0'*(-len(payload)%4));js=json.dumps(new,separators=(',',':')).encode();js+=b' '*(-len(js)%4)
    candidate=out/'fish.glb';candidate.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(js)+len(payload))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(payload),0x004e4942)+payload)
    nd,nb=read_glb(candidate);assert nb[:len(blob)]==blob
    assert all(np.array_equal(arrays(doc,blob,i),arrays(nd,nb,i))for i in range(len(doc['accessors'])))
    for key in ['meshes','nodes','skins','animations','materials','textures','samplers','accessors']:assert doc.get(key)==nd.get(key)
    overlay=concept[:,:,:3].copy()
    for i,(name,mask) in enumerate(fin_masks.items()):
        contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(overlay,contours,-1,(255,70+(i*25)%170,255),1)
    Image.fromarray(overlay).save(out/'donor-domain-overlay.png')
    proof={'ok':True,'species':'bluegill','kind':'approved_concept_existing_UV_rgb_bake','model_input_sha256':sha(a.input),'approved_concept_sha256':sha(base/'style-concept-v1.png'),'body_donor_sha256':sha(base/'body-donors-v1.png'),'mouth_donor_sha256':sha(base/'mouth-donor-v1.png')if front is not None else None,'atlas_sha256':sha(ap),'model_sha256':sha(candidate),'non_image_accessors_exact':len(doc['accessors']),'original_BIN_prefix_exact':True,'material_sampler_and_all_alpha_exact':True,'outside_owned_texels_exact':True,'atlas_size':[W,H],'changed_rgb_texels':int(np.any(old[:,:,:3]!=atlas[:,:,:3],axis=2).sum()),'parts':records,'body_registrations':registrations,'donor_samples':{k:s.report()for k,s in samplers.items()},'formal_acceptance':False,'visual_review':'pending','limits':'Generated supplementary views are artistic colors, not anatomy. Same-pose visual review and current final gates still required; nearest fallback maxima reported, not automatic visual approval.'}
    proof['stage']=a.stage
    proof['body_side_source']='complete clean side panel; no local pectoral patch; no whole-fish side donor on body'
    proof['body_checkpoint']=str(a.body_checkpoint)if a.body_checkpoint else None
    proof['frozen_body_texels_preserved']=int(frozen_body.sum())if a.stage=='fins' else None
    proof['stage_changed_rgb_texels']=int(np.any(starting_atlas[:,:,:3]!=atlas[:,:,:3],axis=2).sum())
    proof['head_donor_sha256']=sha(base/'head-donor-v1.png')if head is not None else None
    proof['sampling_count_note']='Body/top/bottom/front samplers count preblend lookups too, including zero-weight lookups; forehead is active-weight-only. Fallback maxima are not visual pass thresholds.'
    (out/'bake.validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'ok':True,'output':str(out),'changed_texels':proof['changed_rgb_texels'],'nonimage_streams_exact':proof['non_image_accessors_exact']}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['body','fins'],required=True);p.add_argument('--body-checkpoint',type=Path);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
