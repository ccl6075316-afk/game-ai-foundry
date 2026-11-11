"""Two-pass diffuse bake over the existing multi-mesh UV domains."""
from pathlib import Path
import argparse, hashlib, io, json, sys
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
W=Path(__file__).resolve().parent
ROOT=W.parents[1]
sys.path[:0]=[str(ROOT/'resources/scripts/volume-fish/portable'),str(ROOT/'resources/scripts/volume-fish')]
from glb_io import arrays,read_glb,sha
from patch_existing_fin_meshes import write
BASE=ROOT/'projects/fishing-2d/game/assets/models/fish/peacock_bass.glb'
def digest(a):
    return hashlib.sha256(a.tobytes()).hexdigest()
def rgba(path):
    return np.asarray(Image.open(path).convert('RGBA'))
def read(path):
    return json.loads(path.read_text())
def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)
def foreground(a):
    c=a[:,:,:3].astype(float)
    background=np.median(np.concatenate((c[:30].reshape(-1,3),c[-30:].reshape(-1,3))),axis=0)
    return np.linalg.norm(c-background,axis=2)>34
def fill(a):
    contours,_=cv2.findContours(a.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    mask=np.zeros(a.shape,np.uint8)
    cv2.drawContours(mask,[max(contours,key=cv2.contourArea)],-1,1,-1)
    return mask>0
def erosion(a,k=3):
    return cv2.erode(a.astype(np.uint8),np.ones((k,k),np.uint8))>0
def extents(mask):
    h,w=mask.shape
    x=np.where(np.any(mask,axis=0))[0]
    return x[0],x[-1],np.interp(np.arange(w),x,np.argmax(mask[:,x],axis=0)),np.interp(np.arange(w),x,h-1-np.argmax(mask[::-1,x],axis=0))
def screen(p,view):
    y=-p[:,1] if view=='side' else p[:,2]
    return np.c_[450+900*p[:,0]/1.18,310+900*y/1.18]
def mask_for(points,tri,view):
    out=np.zeros((620,900),np.uint8)
    xy=np.rint(screen(points,view)).astype(np.int32)
    for ids in tri:
        cv2.fillConvexPoly(out,xy[ids],1)
    return out>0
class RadialDonor:
    def __init__(self, im, mask, target, source_root, target_root):
        self.rgb=im[:,:,:3]
        self.dist,self.near=distance_transform_edt(~mask,return_indices=True)
        self.source_root=np.asarray(source_root)
        self.target_root=np.asarray(target_root)
        self.source_polar=self.polar(mask,self.source_root)
        self.target_polar=self.polar(target,self.target_root)
        self.samples=self.fallback=0
        self.max_distance=0.
    @staticmethod
    def polar(mask,root):
        y,x=np.nonzero(mask)
        angle=np.arctan2(y-root[1],root[0]-x)
        radius=np.hypot(x-root[0],y-root[1])
        angle_min,angle_max=angle.min(),angle.max()
        bins=np.floor((angle-angle_min)/(angle_max-angle_min)*179).astype(int)
        lo=np.full(180,np.inf);hi=np.full(180,-np.inf)
        np.minimum.at(lo,bins,radius);np.maximum.at(hi,bins,radius)
        ix=np.where(np.isfinite(lo))[0];axis=np.arange(180)
        # Small angular average rejects quantization changes in the projected silhouette.
        def smooth_shell(shell):
            return np.convolve(np.pad(np.interp(axis,ix,shell[ix]),(4,4),mode='edge'),np.ones(9)/9,mode='valid')
        return angle_min,angle_max,smooth_shell(lo),smooth_shell(hi)
    def sample(self,points,_view):
        xy=screen(points,'side')
        angle=np.arctan2(xy[:,1]-self.target_root[1],self.target_root[0]-xy[:,0])
        radius=np.hypot(xy[:,0]-self.target_root[0],xy[:,1]-self.target_root[1])
        a,b,near,far=self.target_polar
        u=np.clip((angle-a)/(b-a),0,1);idx=np.rint(179*u).astype(int)
        v=np.clip((radius-near[idx])/np.maximum(1,far[idx]-near[idx]),0,1)
        a,b,near,far=self.source_polar
        angle=a+u*(b-a);radius=near[idx]+v*(far[idx]-near[idx])
        x=np.clip(np.rint(self.source_root[0]-radius*np.cos(angle)).astype(int),0,self.rgb.shape[1]-1)
        y=np.clip(np.rint(self.source_root[1]+radius*np.sin(angle)).astype(int),0,self.rgb.shape[0]-1)
        dist=self.dist[y,x]
        self.samples+=len(x);self.fallback+=int(np.count_nonzero(dist));self.max_distance=max(self.max_distance,float(dist.max(initial=0.)))
        return self.rgb[tuple(self.near[:,y,x])].astype(float)
    def report(self):
        return {'samples':self.samples,'fallback':self.fallback,'maximum_donor_fallback_pixels':self.max_distance,'root_direction_registration':'smooth polar registration around physical root','source_root':self.source_root.tolist(),'target_root':self.target_root.tolist()}
class Donor:
    def __init__(self,im,mask,target,knots=(),allowed=None):
        self.rgb=im[:,:,:3]
        self.mask=mask
        self.x0,self.x1,self.top,self.bottom=extents(mask)
        self.t0,self.t1,self.target_top,self.target_bottom=extents(target)
        self.dist,self.near=distance_transform_edt(~(mask if allowed is None else allowed),return_indices=True)
        self.knots=knots
        self.samples=0
        self.fallback=0
        self.max_distance=0.
    def sample(self,points,view,axial_mirror=False,top_half=False):
        xy=screen(points,view)
        tx=np.clip(np.rint(xy[:,0]).astype(int),0,899)
        if self.knots:
            xt,xs=np.asarray(self.knots).T
            x=np.interp(xy[:,0],np.r_[self.t0,xt,self.t1],np.r_[self.x0,xs,self.x1])
        else:
            x=self.x0+(xy[:,0]-self.t0)*(self.x1-self.x0)/max(1,self.t1-self.t0)
        x=np.clip(np.rint(x).astype(int),0,len(self.top)-1)
        v=np.clip((xy[:,1]-self.target_top[tx])/np.maximum(1,self.target_bottom[tx]-self.target_top[tx]),0,1)
        if axial_mirror:
            v=.5-np.abs(v-.5) if top_half else .5+np.abs(v-.5)
        y=np.clip(np.rint(self.top[x]+v*(self.bottom[x]-self.top[x])).astype(int),0,self.mask.shape[0]-1)
        distance=self.dist[y,x]
        self.samples+=len(x)
        self.fallback+=int(np.count_nonzero(distance))
        self.max_distance=max(self.max_distance,float(distance.max(initial=0.)))
        return self.rgb[tuple(self.near[:,y,x])].astype(float)
    def report(self):
        return {'samples':self.samples,'fallback':self.fallback,'maximum_donor_fallback_pixels':self.max_distance,'donor_x':[int(self.x0),int(self.x1)],'projection_x':[int(self.t0),int(self.t1)]}

def parts(doc,blob):
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        for surface,prim in enumerate(doc['meshes'][node['mesh']]['primitives']):
            fields={k:arrays(doc,blob,prim['attributes'][k]) for k in ('POSITION','NORMAL','TEXCOORD_0')}
            tex=doc['materials'][prim['material']]['pbrMetallicRoughness']['baseColorTexture']['index']
            yield (node['name'],surface),doc['textures'][tex]['source'],fields,arrays(doc,blob,prim['indices']).reshape(-1,3)
def png(doc,blob,index):
    view=doc['bufferViews'][doc['images'][index]['bufferView']]
    off=view.get('byteOffset',0)
    return rgba(io.BytesIO(blob[off:off+view['byteLength']])).copy()
def replace_images(doc,blob,files,out):
    blob=bytearray(blob)
    for index,path in files.items():
        blob.extend(bytes((-len(blob))%4))
        data=path.read_bytes()
        doc['images'][index]['bufferView']=len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':len(blob),'byteLength':len(data)})
        blob.extend(data)
    write(out,doc,blob)

def raster(arr,fields,tri,sample,priority=None,skip=None):
    h,w=arr.shape[:2]
    owned=np.zeros((h,w),bool)
    weight=np.zeros((h,w),np.float32) if priority is None else priority
    for ids in tri:
        uv=fields['TEXCOORD_0'][ids]*[w,h]-.5
        mat=np.column_stack((uv[1]-uv[0],uv[2]-uv[0]))
        if abs(np.linalg.det(mat))<1e-9:
            continue
        lo=np.maximum(0,np.floor(uv.min(0)-2).astype(int))
        hi=np.minimum([w-1,h-1],np.ceil(uv.max(0)+2).astype(int))
        xy=np.stack(np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1)),axis=-1).reshape(-1,2)
        ab=(xy-uv[0])@np.linalg.inv(mat).T
        bc=np.c_[1-ab.sum(1),ab]
        inside=bc.min(1)>=-1e-7
        dist=np.full(len(xy),np.inf)
        for a,b in zip(uv,np.roll(uv,-1,axis=0)):
            edge=b-a
            t=np.clip((xy-a)@edge/max(edge@edge,1e-12),0,1)
            dist=np.minimum(dist,np.linalg.norm(xy-a-t[:,None]*edge,axis=1))
        rank=np.where(inside,3,1/(1+dist))
        take=(inside|(dist<=1.25))&(rank>=weight[xy[:,1],xy[:,0]])
        if skip is not None:
            take &= ~skip[xy[:,1],xy[:,0]]
        x,y=xy[take].T
        if not len(x):
            continue
        bc=np.maximum(bc[take],0)
        bc/=bc.sum(1)[:,None]
        points=bc@fields['POSITION'][ids]
        normals=bc@fields['NORMAL'][ids]
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-7)
        arr[y,x,:3]=np.clip(np.rint(sample(points,normals,x,y)),0,255).astype(np.uint8)
        weight[y,x]=rank[take]
        owned[y,x]=True
    return owned
def body(doc,blob,all_parts,out):
    _,_,main,tris=next(p for p in all_parts if p[0]==('Closed_body',0))
    _,_,oral,oral_tris=next(p for p in all_parts if p[0]==('Closed_body',1))
    original=png(doc,blob,2)
    new=original.copy()
    donor_files={k:W/name for k,name in [('side','body-side-v1.png'),('top','body-top-v2.png'),('bottom','body-bottom-v2.png')]}
    knots={'side':[(363,548),(482,773),(605,994),(659,1100),(738,1229),(794,1326)],
           'top':[(363,567),(482,765),(605,983),(739,1220)], 'bottom':[(363,519),(482,751),(605,979)]}
    donors={}
    for view,path in donor_files.items():
        img=rgba(path)
        if view=='bottom':
            # Generation is nose-left. All physical x stations stay peduncle-left.
            img=img[:,::-1].copy()
        silhouette=erosion(fill(foreground(img)),5)
        target=mask_for(main['POSITION'],tris,view)
        donors[view]=Donor(img,silhouette,target,knots.get(view,()))
        valid=np.zeros_like(img)
        valid[silhouette]=img[silhouette]
        Image.fromarray(valid).save(out/f'donor-{view}-domain.png')
    def sample(p,n,x,y):
        side=donors['side'].sample(p,'side')
        dorsal=donors['top'].sample(p,'top',True,True)
        ventral=donors['bottom'].sample(p,'bottom',True,False)
        top=smooth((n[:,1]-.43)/.49)
        bottom=smooth((-n[:,1]-.43)/.47)
        new=side*(1-top-bottom)[:,None]+dorsal*top[:,None]+ventral*bottom[:,None]
        # Original front chart is anatomically registered to the actual eye relief and
        # the folded upper/lower lips. Preserve their true pixels and dim oral gap.
        eye=np.linalg.norm((p[:,:2]-[.378,.025])/[.048,.036],axis=1)
        eye_weight=(1-smooth((eye-.83)/.7))*smooth((np.abs(p[:,2])-.032)/.018)
        mouth=smooth((p[:,0]-.380)/.063)*(1-smooth((p[:,1]+.015)/.026))
        mouth=np.maximum(mouth,smooth((p[:,0]-.444)/.042))
        protect=np.maximum(eye_weight,mouth)
        return new*(1-protect[:,None])+original[y,x,:3]*protect[:,None]
    mask_color=original.copy()
    oral_owned=raster(mask_color,oral,oral_tris,lambda p,n,x,y:original[y,x,:3])
    body_owned=raster(new,main,tris,sample,skip=oral_owned)
    assert np.array_equal(new[oral_owned],original[oral_owned])
    owned=body_owned|oral_owned
    assert np.array_equal(new[:,:,3],original[:,:,3])
    Image.fromarray(new).save(out/'image2.png')
    np.savez_compressed(out/'body-ownership.npz',owned=owned,oral_owned=oral_owned)
    return {2:out/'image2.png'},dict(body_owned=int(owned.sum()),body_RGBA_sha256=digest(new[owned]),oral_protected=int(oral_owned.sum()),changed_RGB=int(np.any(new[:,:,:3]!=original[:,:,:3],axis=2).sum()),donors={view:donor.report()|{'sha256':sha(donor_files[view])} for view,donor in donors.items()})

FIN_POLYGONS={
 'Caudal':[(124,475),(141,389),(167,338),(191,340),(255,387),(293,418),(321,437),(312,471),(319,549),(283,576),(250,619),(216,655),(201,660),(172,639),(145,590),(129,533)],
 'Dorsal_soft':[(394,359),(415,326),(449,295),(500,271),(548,271),(601,290),(645,320),(574,339),(512,364),(443,407),(417,400),(402,385)],
 'Dorsal_spiny':[(638,318),(650,297),(675,307),(675,282),(699,294),(692,266),(727,281),(716,249),(751,270),(742,234),(776,254),(777,217),(810,244),(809,210),(846,232),(849,204),(880,224),(890,201),(916,226),(935,206),(962,244),(980,223),(1000,266),(1014,244),(1024,287),(924,287),(835,289),(752,300),(687,317)],
 'Anal':[(389,618),(397,588),(418,564),(465,579),(520,600),(574,618),(616,635),(580,666),(537,688),(488,695),(446,681),(414,657)],
 'Pectoral':[(832,489),(866,485),(915,496),(968,514),(1018,531),(1016,551),(993,574),(959,593),(931,605),(901,590),(878,563),(850,526)],
 'Pelvic':[(849,749),(863,725),(873,695),(883,668),(899,646),(949,638),(1005,628),(991,658),(978,687),(957,710),(927,729),(890,743)]
}
def fins(doc,blob,all_parts,out,checkpoint):
    proof=read(checkpoint/'bake.validation.json')
    visual=read(checkpoint/'body-review.validation.json')
    assert visual['ok'] and visual['model_sha256']==sha(checkpoint/'fish.glb')==proof['model_sha256']
    bodyfile=checkpoint/'image2.png'
    ownership=np.load(checkpoint/'body-ownership.npz')['owned']
    assert digest(rgba(bodyfile)[ownership])==proof['body_RGBA_sha256']
    files={2:bodyfile}
    fin_records={}
    concept=rgba(W/'style-concept-v1.png')
    for image_id in [0,1,3,4,5,6]:
        rows=[p for p in all_parts if p[1]==image_id]
        assert rows
        key=rows[0][0][0]
        if key.startswith(('Pectoral','Pelvic')):
            key=key.split('_')[0]
        donor_mask=np.zeros(concept.shape[:2],np.uint8)
        cv2.fillPoly(donor_mask,[np.array(FIN_POLYGONS[key],np.int32)],1)
        support=erosion(donor_mask.astype(bool)&foreground(concept),3)
        (name,_),_,fields,tris=rows[0]
        target=mask_for(fields['POSITION'],tris,'side')
        roots={'Pectoral':([1050,542],[630,348]),'Pelvic':([1030,625],[625,394])}
        donor=RadialDonor(concept,support,target,*roots[key]) if key in roots else Donor(concept,support,target)
        old=png(doc,blob,image_id)
        new=old.copy()
        priority=np.zeros(old.shape[:2],np.float32)
        all_owned=np.zeros(old.shape[:2],bool)
        def sample(p,n,x,y):
            return donor.sample(p,'side')
        for _,_,f,t in rows:
            all_owned |= raster(new,f,t,sample,priority)
        assert np.array_equal(new[:,:,3],old[:,:,3])
        path=out/f'image{image_id}.png'
        Image.fromarray(new).save(path)
        files[image_id]=path
        fin_records[key]=dict(names=[p[0][0] for p in rows],pixels=int(all_owned.sum()),sha256=sha(path),**donor.report())
    assert digest(rgba(files[2])[ownership])==proof['body_RGBA_sha256']
    return files,dict(body_before_fins_RGBA_sha256=proof['body_RGBA_sha256'],body_after_fins_RGBA_sha256=proof['body_RGBA_sha256'],body_owned=int(ownership.sum()),concept_sha256=sha(W/'style-concept-v1.png'),fins=fin_records)
def main():
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=['body','fins'])
    p.add_argument('output',type=Path)
    p.add_argument('--checkpoint',type=Path)
    a=p.parse_args()
    assert a.output.resolve().is_relative_to(W) and not a.output.exists()
    manifest=read(W/'manifest.json')
    assert sha(BASE)==manifest['baseline']['model_sha256']
    assert manifest['source_generation']['user_acceptance']=='accepted'
    doc,blob=read_glb(BASE)
    all_parts=list(parts(doc,blob))
    a.output.mkdir()
    if a.stage=='body':
        files,details=body(doc,blob,all_parts,a.output)
    else:
        assert a.checkpoint
        files,details=fins(doc,blob,all_parts,a.output,a.checkpoint)
    replace_images(doc,blob,files,a.output/'fish.glb')
    save(a.output/'bake.validation.json',dict(ok=True,stage=a.stage,model_sha256=sha(a.output/'fish.glb'),baseline_sha256=sha(BASE),images={str(k):{'path':str(v.resolve()),'sha256':sha(v)} for k,v in files.items()},**details))
if __name__=='__main__':
    main()
