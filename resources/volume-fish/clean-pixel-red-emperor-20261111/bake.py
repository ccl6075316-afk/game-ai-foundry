"""Red emperor RGB-only bake into original UV; body checkpoint precedes fins."""
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
CONFIG=json.loads((E/'manifest.json').read_text(encoding='utf8'));WIDTH=CONFIG['projection']['width'];CX=CONFIG['projection']['cx'];CY=CONFIG['projection']['cy']
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
    state=json.loads((E/'manifest.json').read_text(encoding='utf8'));assert state['user_style_acceptance']['status']=='accepted';assert sha(a.input)==state['model_sha256']
    out=a.output.resolve();assert out.is_relative_to(E) and not out.exists();out.mkdir()
    spec=json.loads((E/'parts-spec.json').read_text(encoding='utf8'));doc,blob,node,prim,parts,attrs,indices,names,expected=packed_arrays(a.input,spec)
    P,N,UV=[attrs[x]for x in ['POSITION','NORMAL','TEXCOORD_0']];v=doc['bufferViews'][doc['images'][0]['bufferView']];offset=v.get('byteOffset',0);old=np.array(Image.open(io.BytesIO(blob[offset:offset+v['byteLength']])).convert('RGBA'));atlas=old.copy();H,W=atlas.shape[:2]
    body_tri=np.concatenate([indices[slice(*p['index_range'])].reshape(-1,3)for p in parts if p['opaque_uv']]);body_owned=np.zeros((H,W),bool)
    if a.stage=='fins':
        checkpoint=a.body_checkpoint.resolve();receipt=json.loads((checkpoint/'body-review.validation.json').read_text(encoding='utf8'));assert receipt['ok'] and receipt['model_sha256']==sha(checkpoint/'fish.glb');atlas=image(checkpoint/'atlas.png');assert sha(checkpoint/'atlas.png')==json.loads((checkpoint/'bake.validation.json').read_text(encoding='utf8'))['atlas_sha256'];body_owned=np.load(checkpoint/'body-ownership.npz')['owned']
    start=atlas.copy();samplers={};panels=[];registrations=[]
    side=image(E/'body-side-v1.png');sheet=image(E/'body-top-bottom-v1.png')
    for view,im in [('side',side),('top',sheet[:sheet.shape[0]//2]),('bottom',sheet[sheet.shape[0]//2:])]:
        mask=largest(foreground(im));mask=cv2.erode(mask.astype(np.uint8),np.ones((3,3),np.uint8))>0
        s=Sampler(im,mask,view);samplers[view]=s;src=extents(mask);t=extents(mask_for(P,body_tri,900,620,view));panels.append((view,s,src,t));registrations.append({'view':view,'source_x':list(src[:2]),'model_projected_x':list(t[:2]),'source_size':[im.shape[1],im.shape[0]]})
    def body_sample(p,q):
        view,s,src,t=panels[q];xy=projection(p,900,620,view);tx=np.clip(np.rint(xy[:,0]).astype(int),0,899);x=src[0]+(xy[:,0]-t[0])/(t[1]-t[0])*(src[1]-src[0]);ix=np.clip(np.rint(x).astype(int),0,len(src[2])-1)
        ratio=(xy[:,1]-t[2][tx])/np.maximum(1,t[3][tx]-t[2][tx])
        if view == 'side':
            # Match the original silhouette stations, gill, eye, and snout.
            landmarks = CONFIG['side_landmarks']
            x = np.interp(xy[:,0], [t[0],*landmarks['model_x'],t[1]], [src[0],*landmarks['donor_x'],src[1]])
            ix = np.clip(np.rint(x).astype(int),0,len(src[2])-1)
        elif view == 'top':
            # The upper donor is lit from one side. Use the dorsal half on both sides.
            ratio = .5 - np.abs(ratio-.5)
        y=src[2][ix]+ratio*(src[3][ix]-src[2][ix]);return s.sample(np.c_[x,y])
    front=image(E/'head-front-v1.png');fh,fw=front.shape[:2];yy,xx=np.mgrid[:fh,:fw]
    # Full frontal donor owns exterior corners and recessed mouth separately in the image.
    # Its central skin mask excludes the measured cavity; no cavity flood fill across oral primitive.
    cavity = np.zeros((fh, fw), np.uint8)
    mouth_boundary = np.array(CONFIG['front_cavity_polygon'])
    cv2.fillPoly(cavity, [np.rint(mouth_boundary*[fw,fh]).astype(np.int32)], 1)
    skin=largest(foreground(front))&~cv2.dilate(cavity.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    samplers['front-skin']=Sampler(front,skin,'front-skin');samplers['oral']=Sampler(front,largest(foreground(front)),'oral-projected-skin-and-cavity')
    # The packed mouth includes external rim faces. Measure the physical mouth/skin
    # boundary before applying cavity colors, so the original pale lip survives.
    mouth_tri = np.concatenate([indices[slice(*part['index_range'])].reshape(-1,3)
                                for part in parts if part['role'] == 'mouth'])
    unique_positions, inverse = np.unique(np.round(P, 7), axis=0, return_inverse=True)
    triangles = inverse[mouth_tri]
    directed = np.concatenate([triangles[:,[0,1]], triangles[:,[1,2]], triangles[:,[2,0]]])
    edge_ids, counts = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
    rim_edges = unique_positions[edge_ids[counts == 1]]
    assert len(rim_edges) > 10
    # Source donor bands are read from the actual front view, excluding its open cavity.
    rim_y0, rim_y1 = CONFIG['front_rim_y']
    rim_mask = skin & (xx > fw*.34) & (xx < fw*.66) & (yy > fh*rim_y0) & (yy < fh*rim_y1)
    rim_mask &= front[:,:,:3].mean(2) > 124
    samplers['rim'] = Sampler(front, rim_mask, 'pale mouth rim')

    def oral_sample(points):
        xy = front_xy(points)
        cavity_color = samplers['oral'].sample(xy)
        rim_color = samplers['rim'].sample(xy)
        distance = np.full(len(points), np.inf)
        for start, end in rim_edges:
            vector = end-start
            t = np.clip((points-start) @ vector / max(vector@vector, 1e-20), 0, 1)
            distance = np.minimum(distance, np.linalg.norm(points-(start+t[:,None]*vector), axis=1))
        amount = smooth((distance-.0012)/.0045)[:,None]
        return rim_color*(1-amount)+cavity_color*amount

    lower_y0, lower_y1 = CONFIG['front_lower_lip_y']
    lower_lip_mask = skin & (xx > fw*.36) & (xx < fw*.64) & (yy > fh*lower_y0) & (yy < fh*lower_y1)
    samplers['lower-lip'] = Sampler(front, lower_lip_mask, 'outer lower lip and chin')

    def front_xy(p):
        cfg=CONFIG['front_projection'];raw=(.5-(p[:,1]-cfg['cy'])/(cfg['width']*620/900))*620
        y=np.interp(raw,[0,*cfg['target_y'],620],[0,*cfg['source_y'],fh]);return np.c_[(.5-p[:,2]/cfg['width'])*fw,y]
    concept = image(E/'style-concept-v1.png')
    ch, cw = concept.shape[:2]
    # In the accepted concept only the near-side fins are painted.
    # Each corresponding pair receives the same part donor, with independent registration.
    fin_polygons = {
        'Caudal': [(134,335),(198,383),(270,427),(332,459),(336,585),(284,627),(206,690),(131,734),(178,637),(228,521),(184,431)],
        'Dorsal': [(427,432),(427,348),(464,309),(523,292),(580,274),(652,252),(726,222),(804,194),(858,177),(904,178),(951,194),(997,223),(1030,260),(1055,301),(998,286),(935,279),(853,283),(778,293),(688,311),(604,338),(529,373),(466,409)],
        'Anal': [(461,614),(506,636),(564,661),(629,683),(691,700),(668,754),(612,789),(568,772),(512,763),(471,718),(444,656)],
        'Pectoral': [(754,470),(801,485),(855,498),(924,522),(1008,550),(993,577),(988,611),(953,626),(912,634),(865,610),(821,570),(784,516)],
        'Pelvic': [(873,719),(928,708),(993,703),(978,742),(943,786),(906,814),(860,839),(814,858),(836,816),(844,766)],
    }
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
                top=smooth((n[:,1]-.49)/.43);bottom=smooth((-n[:,1]-.45)/.42);color=body_sample(p,0)*(1-top-bottom)[:,None]+body_sample(p,1)*top[:,None]+body_sample(p,2)*bottom[:,None]
                if part['role']=='mouth':color=oral_sample(p)
                else:
                    blend=(1-smooth((np.abs(p[:,2])-.017)/.026))*smooth((p[:,0]-.31)/.115)
                    active=blend>0
                    color[active]=color[active]*(1-blend[active,None])+samplers['front-skin'].sample(front_xy(p[active]))*blend[active,None]
                    # The direct frontal projection overlaps the real projecting lower jaw
                    # and open cavity. Select lower exterior skin in model coordinates.
                    lower_rim = np.interp(p[:,0], [.392,.405,.42,.44,.46,.48,.498],
                                          [-.079,-.075,-.068,-.061,-.0545,-.0507,-.0487])
                    jaw = smooth((p[:,0]-.39)/.035) * smooth((-n[:,1]-.19)/.24)
                    jaw *= smooth((lower_rim-p[:,1])/.005)
                    jaw *= 1-smooth((np.abs(p[:,2])-.039)/.015)
                    lower = jaw > 0
                    lip_xy = front_xy(p[lower])
                    lip_xy[:,1] = fh*(lower_y0 + (lower_y1-lower_y0)*np.clip((-.049-p[lower,1])/.048,0,1))
                    color[lower] = color[lower]*(1-jaw[lower,None]) + samplers['lower-lip'].sample(lip_xy)*jaw[lower,None]
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
    proof={'ok':True,'species':'red_emperor','stage':a.stage,'input_sha256':sha(a.input),'model_sha256':sha(candidate),'atlas_sha256':sha(ap),'nonimage_accessors_exact_finite':len(doc['accessors']),'alpha_material_sampler_rig_exact':True,'outside_stage_ownership_unchanged':True,'body_owned_texels':int(owned.sum())if a.stage=='body'else int(body_owned.sum()),'body_before_fins_rgba_sha256':hashlib.sha256(start[body_owned].tobytes()).hexdigest()if a.stage=='fins'else None,'body_after_fins_rgba_sha256':hashlib.sha256(atlas[body_owned].tobytes()).hexdigest()if a.stage=='fins'else None,'parts':records,'body_registrations':registrations,'donor_sampling':{k:s.report()for k,s in samplers.items()},'changed_rgb_texels':int(np.any(start[:,:,:3]!=atlas[:,:,:3],2).sum()),'inputs':{p.name:sha(p)for p in [E/'style-concept-v1.png',E/'body-side-v1.png',E/'body-top-bottom-v1.png',E/'head-front-v1.png']},'visual_review':'pending','formal_acceptance':False,'limits':'Supplemental generated views are artistic color donors; geometry stays frozen. Finless body first, isolated fin stage after actual review. Same-part nearest fallback is reported, not a visual pass.'}
    (out/'bake.validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'ok':True,'stage':a.stage,'changed':proof['changed_rgb_texels'],'body_texels':proof['body_owned_texels'],'nonimage_accessors':len(doc['accessors'])}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['body','fins'],required=True);p.add_argument('--body-checkpoint',type=Path);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);run(p.parse_args())
