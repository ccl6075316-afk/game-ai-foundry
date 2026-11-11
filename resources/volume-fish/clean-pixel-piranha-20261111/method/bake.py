"""Sea bass RGB-only bake into original UV; body checkpoint precedes fins."""
from pathlib import Path
import argparse,copy,hashlib,io,json,struct,sys
import cv2,numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
E=Path(__file__).resolve().parent;R=E.parents[1]
sys.path.insert(0,str(R/'resources/scripts/volume-fish/portable'))
from glb_io import read_glb,arrays
from parts import packed_arrays
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def image(p):return np.array(Image.open(p).convert('RGBA'))
def foreground(im):
    rgb = im[:, :, :3].astype(np.float32)
    background = np.median(np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]), axis=0)
    return np.linalg.norm(rgb - background, axis=2) > 24
def largest(mask):
    cs,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);assert cs
    out=np.zeros(mask.shape,np.uint8);cv2.drawContours(out,[max(cs,key=cv2.contourArea)],-1,1,-1);return out.astype(bool)
def extents(mask):
    yy,xx=np.where(mask);xs=np.unique(xx);lo=np.full(mask.shape[1],np.nan);hi=lo.copy()
    for x in xs:y=np.where(mask[:,x])[0];lo[x]=y.min();hi[x]=y.max()
    return int(xx.min()),int(xx.max()),np.interp(np.arange(len(lo)),xs,lo[xs]),np.interp(np.arange(len(hi)),xs,hi[xs])
CONFIG=json.loads((E/'manifest.json').read_text(encoding='utf8'));WIDTH=1.18;CX=0.;CY=0.
def projection(p,w,h,view='side'):
    if view=='side':return np.c_[(.5+(p[:,0]-CX)/WIDTH)*w,(.5-(p[:,1]-CY)/(WIDTH*620/900))*h]
    return np.c_[(.5+((p[:,0]-CX) if view=='top' else -(p[:,0]-CX))/WIDTH)*w,(.5+p[:,2]/(WIDTH*620/900))*h]
def mask_for(p,tri,w,h,view='side'):
    xy=projection(p,w,h,view);out=np.zeros((h,w),np.uint8)
    for ids in tri:cv2.fillConvexPoly(out,np.rint(xy[ids]).astype(np.int32),1)
    return out.astype(bool)
class Sampler:
    def __init__(self,im,mask,name):
        assert mask.any(),name
        self.im=im[:,:,:3];self.mask=mask;self.name=name;self.dist,self.near=distance_transform_edt(~mask,return_indices=True);self.count=0;self.fallback=0;self.maximum=0.
    def sample(self,xy):
        h,w=self.mask.shape;xx=np.clip(np.rint(xy[:,0]).astype(int),0,w-1);yy=np.clip(np.rint(xy[:,1]).astype(int),0,h-1);d=self.dist[yy,xx]
        self.count+=len(xx);self.fallback+=int((d>0).sum());self.maximum=max(self.maximum,float(d.max(initial=0)));ny,nx=self.near[:,yy,xx];return self.im[ny,nx].astype(float)
    def report(self):return {'samples':self.count,'nearest_valid_samples':self.fallback,'maximum_distance_pixels':self.maximum}
def run(a):
    state=json.loads((E/'manifest.json').read_text(encoding='utf8'));assert state['user_style_acceptance']['status']=='accepted';assert sha(a.input)==state['baseline']['model_sha256']
    out=a.output.resolve();assert out.is_relative_to(E) and not out.exists();out.mkdir()
    spec=json.loads((E/'parts-spec.json').read_text(encoding='utf8'));doc,blob,node,prim,parts,attrs,indices,names,expected=packed_arrays(a.input,spec)
    P,N,UV=[attrs[x]for x in ['POSITION','NORMAL','TEXCOORD_0']];v=doc['bufferViews'][doc['images'][0]['bufferView']];offset=v.get('byteOffset',0);old=np.array(Image.open(io.BytesIO(blob[offset:offset+v['byteLength']])).convert('RGBA'));atlas=old.copy();H,W=atlas.shape[:2]
    body_tri=np.concatenate([indices[slice(*p['index_range'])].reshape(-1,3)for p in parts if p['opaque_uv']]);body_owned=np.zeros((H,W),bool)
    if a.stage=='fins':
        checkpoint=a.body_checkpoint.resolve();receipt=json.loads((checkpoint/'body-review.validation.json').read_text(encoding='utf8'));assert receipt['ok'] and receipt['model_sha256']==sha(checkpoint/'fish.glb');atlas=image(checkpoint/'atlas.png');assert sha(checkpoint/'atlas.png')==json.loads((checkpoint/'bake.validation.json').read_text(encoding='utf8'))['atlas_sha256'];body_owned=np.load(checkpoint/'body-ownership.npz')['owned']
    start=atlas.copy();samplers={};panels=[];registrations=[]
    side=image(E/'body-side-v1.png');sheet=image(E/'body-top-bottom-v1.png')
    for view,im in [('side',side),('top',sheet[:sheet.shape[0]//2]),('bottom',sheet[sheet.shape[0]//2:])]:
        rawmask=im[:,:,:3].max(2)>75;rawmask[:8]=False;rawmask[-8:]=False;rawmask[:,:8]=False;rawmask[:,-8:]=False;mask=largest(rawmask);mask=cv2.erode(mask.astype(np.uint8),np.ones((3,3),np.uint8))>0
        if view=='side':
            cavity_side=np.zeros(mask.shape,np.uint8)
            cv2.fillPoly(cavity_side,[np.array([[1285,626],[1310,600],[1340,588],[1376,575],[1382,613],[1330,623]],np.int32)],1)
            mask &= ~cavity_side.astype(bool)
        s=Sampler(im,mask,view);samplers[view]=s;src=extents(mask);t=extents(mask_for(P,body_tri,900,620,view));panels.append((view,s,src,t));registrations.append({'view':view,'source_x':list(src[:2]),'model_projected_x':list(t[:2]),'source_size':[im.shape[1],im.shape[0]]})
    def body_sample(p,q):
        view,s,src,t=panels[q];xy=projection(p,900,620,view);tx=np.clip(np.rint(xy[:,0]).astype(int),0,899);x=src[0]+(xy[:,0]-t[0])/(t[1]-t[0])*(src[1]-src[0]);ix=np.clip(np.rint(x).astype(int),0,len(src[2])-1)
        ratio=(xy[:,1]-t[2][tx])/np.maximum(1,t[3][tx]-t[2][tx])
        if view == 'side':
            # Match the original silhouette stations, gill, eye, and snout.
            x = np.interp(p[:,0], [-.33020014,.265,.3942,.4975743], [src[0],1100,1256,src[1]])
            ix = np.clip(np.rint(x).astype(int),0,len(src[2])-1)
        elif view == 'top':
            # The upper donor is lit from one side. Use the dorsal half on both sides.
            ratio = .5 - np.abs(ratio-.5)
        elif view == 'bottom':
            ratio = .60 + .40*np.abs(ratio-.5)*2
        y=src[2][ix]+ratio*(src[3][ix]-src[2][ix]);return s.sample(np.c_[x,y])
    front=image(E/'head-front-v1.png');fh,fw=front.shape[:2];yy,xx=np.mgrid[:fh,:fw]
    # Full frontal donor owns exterior corners and recessed mouth separately in the image.
    # Its central skin mask excludes the measured cavity; no cavity flood fill across oral primitive.
    cavity = np.zeros((fh,fw),np.uint8)
    mouth_boundary=np.array([[.343,.635],[.378,.598],[.423,.578],[.48,.574],[.54,.576],[.60,.593],[.654,.637],[.61,.615],[.54,.608],[.46,.609],[.39,.621]])
    cv2.fillPoly(cavity,[np.rint(mouth_boundary*[fw,fh]).astype(np.int32)],1)
    skin=largest(foreground(front))&~cv2.dilate(cavity,np.ones((5,5),np.uint8)).astype(bool)
    samplers['front-skin']=Sampler(front,skin,'front-skin')
    samplers['oral']=Sampler(front,largest(foreground(front)),'oral-projected-skin-and-cavity')
    mouth_tri=np.concatenate([indices[slice(*part['index_range'])].reshape(-1,3) for part in parts if part['role']=='mouth'])
    up,inv=np.unique(np.round(P,7),axis=0,return_inverse=True);tr=inv[mouth_tri]
    ed=np.concatenate([tr[:,[0,1]],tr[:,[1,2]],tr[:,[2,0]]]);ed,cnt=np.unique(np.sort(ed,axis=1),axis=0,return_counts=True);rim_edges=up[ed[cnt==1]]
    def front_xy(p):
        raw=(.5-(p[:,1]+.004/.17880773521243956)/(.068/.17880773521243956*620/900))*620
        y=np.interp(raw,[0,350,380,409,440,620],[0,565,595,623,653,fh])
        rx=(.5-p[:,2]/(.068/.17880773521243956))*900
        sx=rx/900*fw
                # Actual cavity is only a narrow ribbon; exterior lower jaw starts
        # immediately below it, so never project the painted aperture onto skin.
        tx=np.clip(np.rint(rx).astype(int),0,899)
        valid=(rx>=ot[0])&(rx<=ot[1])
        cx=os[0]+(rx-ot[0])/(ot[1]-ot[0])*(os[1]-os[0]);ci=np.clip(np.rint(cx).astype(int),0,fw-1)
        below=valid&(raw>=ot[3][tx]);above=valid&(raw<=ot[2][tx])
        y[below]=os[3][ci[below]]+65+(raw[below]-ot[3][tx[below]])*fh/620
        y[above]=os[2][ci[above]]-3+(raw[above]-ot[2][tx[above]])*fh/620
        sx[valid]=cx[valid]
        return np.c_[sx,y]
    oral_target=np.zeros((620,900),np.uint8)
    oral_screen=np.c_[(.5-P[:,2]/(.068/.17880773521243956))*900,(.5-(P[:,1]+.004/.17880773521243956)/(.068/.17880773521243956*620/900))*620]
    for tri in mouth_tri:cv2.fillConvexPoly(oral_target,np.rint(oral_screen[tri]).astype(np.int32),1)
    ot=extents(oral_target>0);os=extents(cavity>0)
    def oral_sample(points):
        xy=front_xy(points);rim=samplers['front-skin'].sample(xy)
        rawx=(.5-points[:,2]/(.068/.17880773521243956))*900
        rawy=(.5-(points[:,1]+.004/.17880773521243956)/(.068/.17880773521243956*620/900))*620
        ix=np.clip(np.rint(rawx).astype(int),0,899);ratio=np.clip((rawy-ot[2][ix])/np.maximum(1,ot[3][ix]-ot[2][ix]),0,1)
        sx=os[0]+(rawx-ot[0])/(ot[1]-ot[0])*(os[1]-os[0]);si=np.clip(np.rint(sx).astype(int),0,fw-1)
        sy=os[2][si]+ratio*(os[3][si]-os[2][si]);oral=samplers['oral'].sample(np.c_[sx,sy])
        distance=np.full(len(points),np.inf)
        for start,end in rim_edges:
            v=end-start;t=np.clip((points-start)@v/max(v@v,1e-20),0,1);distance=np.minimum(distance,np.linalg.norm(points-(start+t[:,None]*v),axis=1))
        amount=smooth((distance-.0005)/.0015)[:,None]
        return rim*(1-amount)+oral*amount
    concept = image(E/'style-concept-v3-teeth.png')
    ch, cw = concept.shape[:2]
    # In the accepted concept only the near-side fins are painted.
    # Each corresponding pair receives the same part donor, with independent registration.
    fin_polygons = {
        'Caudal':[(121,320),(206,345),(310,466),(308,586),(232,686),(140,751),(146,655),(206,533),(174,447)],
        'Dorsal':[(573,330),(624,262),(671,183),(668,164),(739,184),(799,217),(862,269),(727,294)],
        'Adipose':[(393,418),(405,390),(438,381),(476,401),(493,416),(423,450),(399,445)],
        'Anal':[(382,601),(472,622),(553,709),(665,764),(608,809),(530,858),(493,762),(436,692)],
        'Pectoral':[(890,631),(944,620),(1004,638),(1065,670),(1082,697),(1040,723),(982,711),(938,681)],
        'Pelvic':[(797,776),(885,787),(846,826),(750,871),(768,831)]}
    fin_registration = {}
    for part in parts:
        if part['role'] != 'fin' or a.stage != 'fins':
            continue
        name = part['name']
        category = next(key for key in fin_polygons if name.startswith(key+'_'))
        mask = np.zeros((ch, cw), np.uint8)
        points = np.array(fin_polygons[category]) * [cw/1511, ch/1041]
        cv2.fillPoly(mask, [np.rint(points).astype(np.int32)], 1)
        mask = (mask > 0) & foreground(concept)
        mask = cv2.erode(mask.astype(np.uint8), np.ones((5,5), np.uint8)) > 0
        target = mask_for(P, indices[slice(*part['index_range'])].reshape(-1,3), 900, 620)
        samplers[name] = Sampler(concept, mask, name)
        def bounds(pixels):
            y, x = np.nonzero(pixels)
            return np.array([x.min(), y.min()]), np.array([x.max(), y.max()])
        fin_registration[name] = (bounds(mask), bounds(target))

    def fin_sample(points, name):
        (source_min, source_max), (target_min, target_max) = fin_registration[name]
        if name.startswith('Pectoral_'):
            native=np.array([[.25299454,-.11764670,1],[.10515463,-.08669822,1],[.20179595,-.15766649,1]])
            donor=np.array([[1070,694],[895,635],[1005,714]])*[cw/1511,ch/1041]
            affine=np.linalg.solve(native,donor)
            return samplers[name].sample(np.c_[points[:,:2],np.ones(len(points))]@affine)
        xy = projection(points, 900, 620)
        fraction = (xy-target_min) / (target_max-target_min)
        return samplers[name].sample(source_min + fraction*(source_max-source_min))


    owned=np.zeros((H,W),bool);weight=np.zeros((H,W),np.float32);records=[]
    for part in parts:
        if (a.stage=='body')==(part['role']=='fin'):continue
        samples=0
        for ids in indices[slice(*part['index_range'])].reshape(-1,3):
            z=UV[ids]*[W,H]-.5;A=np.column_stack((z[1]-z[0],z[2]-z[0]));det=np.linalg.det(A)
            if abs(det)<1e-9:continue
            lo=np.maximum(np.floor(z.min(0)-2).astype(int),0);hi=np.minimum(np.ceil(z.max(0)+2).astype(int),[W-1,H-1]);xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));pts=np.c_[xx.ravel(),yy.ravel()];ab=(pts-z[0])@np.linalg.inv(A).T;beta=np.c_[1-ab.sum(1),ab];distance=np.full(len(pts),1e8)
            for p0,p1 in zip(z,np.roll(z,-1,axis=0)):
                e=p1-p0;t=np.clip(((pts-p0)*e).sum(1)/max(e@e,1e-20),0,1);distance=np.minimum(distance,np.linalg.norm(pts-(p0+t[:,None]*e),axis=1))
            take=(beta.min(1)>=-1e-7)|(distance<=1.25);pts=pts[take];beta=beta[take];dist=distance[take];priority=np.where(beta.min(1)>=-1e-7,3.,1/(1+dist));take=priority>=weight[pts[:,1],pts[:,0]];pts=pts[take];beta=np.maximum(beta[take],0);beta/=beta.sum(1)[:,None];priority=priority[take]
            if not len(pts):continue
            p=beta@P[ids];n=beta@N[ids];n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-8)
            if part['role']=='fin':color=fin_sample(p,part['name'])
            else:
                top=smooth((n[:,1]-.40)/.45);bottom=smooth((-n[:,1]-.40)/.45);color=body_sample(p,0)*(1-top-bottom)[:,None]+body_sample(p,1)*top[:,None]+body_sample(p,2)*bottom[:,None]
                if part['role']=='mouth':color=oral_sample(p)
                else:
                    blend=(1-smooth((np.abs(p[:,2])-.022)/.026))*smooth((p[:,0]-.33)/.105)
                    active=blend>0
                    color[active]=color[active]*(1-blend[active,None])+samplers['front-skin'].sample(front_xy(p[active]))*blend[active,None]
            if part['role']=='body_skin':
                # Preserve the true original exterior lower jaw UV donor; the
                # frontal generated cavity extends behind this visible skin.
                # Broad 3D falloff joins original lip/chin to new skin.
                lower=smooth((p[:,0]-.375)/.065)*smooth((-.045-p[:,1])/.009)*(1-smooth((-p[:,1]-.095)/.065))
                original=old[pts[:,1],pts[:,0],:3].astype(float)*np.array([.95,.90,.83])
                color=color*(1-lower[:,None])+original*lower[:,None]
            if out.name=='ownership-diagnostic':color=np.tile([0,40,255] if part['role']=='mouth' else [255,40,0],(len(p),1))
            if a.stage=='fins':assert not body_owned[pts[:,1],pts[:,0]].any(),'Fin footprint overlaps frozen body'
            atlas[pts[:,1],pts[:,0],:3]=np.rint(np.clip(color,0,255)).astype(np.uint8);owned[pts[:,1],pts[:,0]]=True;weight[pts[:,1],pts[:,0]]=priority;samples+=len(pts)
        records.append({'part':part['source_name'],'role':part['role'],'sampled_texels_with_overlap':samples})
    assert np.array_equal(old[:,:,3],atlas[:,:,3]);assert np.array_equal(start[~owned],atlas[~owned])
    if a.stage=='body':np.savez_compressed(out/'body-ownership.npz',owned=owned)
    else:assert np.array_equal(start[body_owned],atlas[body_owned])
    ap=out/'atlas.png';Image.fromarray(atlas).save(ap);new=copy.deepcopy(doc);payload=bytearray(blob);payload.extend(b'\0'*(-len(payload)%4));off=len(payload);png=ap.read_bytes();payload.extend(png);new['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(png)});new['images'][0]['bufferView']=len(new['bufferViews'])-1;new['buffers'][0]['byteLength']=len(payload);payload.extend(b'\0'*(-len(payload)%4));js=json.dumps(new,separators=(',',':')).encode();js+=b' '*(-len(js)%4)
    candidate=out/'fish.glb';candidate.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(js)+len(payload))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(payload),b'BIN\0')+payload)
    nd,nb=read_glb(candidate);assert nb[:len(blob)]==blob
    for i in range(len(doc['accessors'])):assert np.array_equal(arrays(doc,blob,i),arrays(nd,nb,i)) and np.isfinite(arrays(nd,nb,i)).all()
    for key in ['meshes','nodes','skins','animations','materials','textures','samplers','accessors']:assert doc.get(key)==nd.get(key)
    proof={'ok':True,'species':'piranha','stage':a.stage,'input_sha256':sha(a.input),'model_sha256':sha(candidate),'atlas_sha256':sha(ap),'nonimage_accessors_exact_finite':len(doc['accessors']),'alpha_material_sampler_rig_exact':True,'outside_stage_ownership_unchanged':True,'body_owned_texels':int(owned.sum())if a.stage=='body'else int(body_owned.sum()),'body_before_fins_rgba_sha256':hashlib.sha256(start[body_owned].tobytes()).hexdigest()if a.stage=='fins'else None,'body_after_fins_rgba_sha256':hashlib.sha256(atlas[body_owned].tobytes()).hexdigest()if a.stage=='fins'else None,'parts':records,'body_registrations':registrations,'donor_sampling':{k:s.report()for k,s in samplers.items()},'changed_rgb_texels':int(np.any(start[:,:,:3]!=atlas[:,:,:3],2).sum()),'inputs':{p.name:sha(p)for p in [E/'style-concept-v3-teeth.png',E/'body-side-v1.png',E/'body-top-bottom-v1.png',E/'head-front-v1.png']},'visual_review':'pending','formal_acceptance':False,'limits':'Supplemental generated views are artistic color donors; geometry stays frozen. Finless body first, isolated fin stage after actual review. Same-part nearest fallback is reported, not a visual pass.'}
    (out/'bake.validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'ok':True,'stage':a.stage,'changed':proof['changed_rgb_texels'],'body_texels':proof['body_owned_texels'],'nonimage_accessors':len(doc['accessors'])}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['body','fins'],required=True);p.add_argument('--body-checkpoint',type=Path);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);run(p.parse_args())
