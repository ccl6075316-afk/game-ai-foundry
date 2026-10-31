"""Source-reviewed three-view ornament hulls with explicit semantic cavities.

Original art drives outside shape and all paint. Reusable cavity operations
express known hollow construction that three silhouettes alone cannot recover.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from skimage.measure import marching_cubes
import fast_simplification
from build_from_art import Glb
from build_from_three_views import sample_sdf

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def source_image(path):
    rgba=Image.open(path).convert('RGBA');a=np.array(rgba);image=rgba.convert('RGB');rgb=np.array(image)
    mask=(a[:,:,3]>128) if (a[:,:,3]<255).any() else (rgb.min(2)<236)
    labels,_=ndi.label(mask);counts=np.bincount(labels.ravel());counts[0]=0
    mask=labels==counts.argmax()
    holes=ndi.binary_fill_holes(mask)&~mask;labels,_=ndi.label(holes);sizes=np.bincount(labels.ravel());small=sizes<max(64,int(mask.sum()*.0005));small[0]=False;mask|=small[labels]
    yy,xx=np.nonzero(mask)
    box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    return image.crop(box),mask[box[1]:box[3],box[0]:box[2]],box

def source_for(root,id,view,projects=None):
    project=root/(projects[view] if projects else ('projects/aquascape-decor-fronts-v1' if view=='front' else f'projects/aquascape-decor-{id}-views-v1'))
    asset=read(project/'output/assets-manifest.json')['assets'][id+'_'+view]
    if asset.get('review',{}).get('status')!='accepted':raise ValueError('Unreviewed source: '+id+' '+view)
    stage=next(s for s in asset['stages'] if s['stage']=='image.raw' and s['status']=='done')
    return root/stage['path_repo']

def save_donor(path,output):
    image,mask,box=source_image(path);rgb=np.array(image)
    distance=ndi.distance_transform_edt(np.pad(mask,1))[1:-1,1:-1]
    trusted=mask&(distance>3)
    if not trusted.any():trusted=mask
    nearest=ndi.distance_transform_edt(~trusted,return_distances=False,return_indices=True)
    rgb[~trusted]=rgb[nearest[0],nearest[1]][~trusted]
    Image.fromarray(np.dstack([rgb,np.where(mask,255,0).astype('uint8')])).save(output)
    return {'source':str(path),'source_sha256':sha(path),'output':str(output),'sha256':sha(output),'native_crop':list(image.size),'source_bbox':list(box)}

def profile_radius(mask,y,height,span,axis,wall_ratio=.055):
    # Visible row envelope supplies the jar's outside radius at each height.
    row=np.clip(np.rint((1-y/height)*(mask.shape[0]-1)).astype(int),0,mask.shape[0]-1)
    widths=np.array([np.ptp(np.flatnonzero(r))+1 if r.any() else 0 for r in mask])
    radii=widths[row]*span/mask.shape[1]*.5
    return np.maximum(radii-span*wall_ratio,span*.035).reshape(axis)

def carve(field,X,Y,Z,width,height,depth,spec,fm,rm):
    kind=spec['cavity'];w=width;h=height;d=depth
    params=spec.get('cavity_parameters',{})
    if kind=='pipe':
        center=params.get('center_y',.5)*h
        cavity=(1-np.sqrt(((Y-center)/(h*.335))**2+(Z/(d*.335))**2))*min(h,d)*.335
        field=np.minimum(field,-cavity)
    elif kind=='jar':
        outer_x=profile_radius(fm,Y[0,:,0],h,w,(1,-1,1),0);outer_z=profile_radius(rm,Y[0,:,0],h,d,(1,-1,1),0)
        # The painted mouth ellipse is a view of an open rim, not a solid
        # cap whose circular cross-section collapses near its upper pixels.
        lip=(Y>=h*.86)&(Y<=h)
        outer_x=np.where(Y>=h*.86,float(outer_x[lip].max()),outer_x)
        outer_z=np.where(Y>=h*.86,float(outer_z[lip].max()),outer_z)
        outer=(1-np.sqrt((X/outer_x)**2+(Z/outer_z)**2))*np.minimum(outer_x,outer_z)
        field=np.minimum(outer,np.minimum(Y,h-Y))
        rx=np.maximum(outer_x-w*.055,w*.035);rz=np.maximum(outer_z-d*.055,d*.035)
        radial=(1-np.sqrt((X/rx)**2+(Z/rz)**2))*np.minimum(rx,rz)
        cavity=np.minimum(radial,Y-h*params.get('floor_y',.12))
        field=np.minimum(field,-cavity)
    elif kind=='coconut':
        inner=(1-np.sqrt((X/(w*.43))**2+(Y/(h*.84))**2+(Z/(d*.43))**2))*min(w,h,d)*.43
        doorway=(1-np.sqrt((X/(w*.20))**2+(Y/(h*.56))**2))*min(w*.20,h*.56)
        doorway=np.minimum(doorway,Z+d*.08)
        field=np.minimum(field,-np.maximum(inner,doorway))
    elif kind=='lantern':
        cy=params.get('center_y',.56)*h
        tunnel_z=np.minimum(w*.155-np.abs(X),h*.11-np.abs(Y-cy))
        tunnel_x=np.minimum(d*.155-np.abs(Z),h*.11-np.abs(Y-cy))
        field=np.minimum(field,-np.maximum(tunnel_z,tunnel_x))
    elif kind=='cargo_well':
        well=np.minimum(np.minimum(w*.235-np.abs(X+w*.035),d*.285-np.abs(Z)),Y-h*params.get('floor_y',.20))
        mast=np.minimum(w*.038-np.abs(X),d*.08-np.abs(Z))
        well=np.minimum(well,-mast)
        field=np.minimum(field,-well)
    elif kind=='box_tunnel':
        cavity=np.minimum(w*.32-np.abs(X),h*.23-np.abs(Y-h*.35))
        field=np.minimum(field,-cavity)
    elif kind=='arched_tunnel':
        # Vertical sides and a round crown; passage continues through Z.
        arch=np.minimum(w*.20-np.abs(X),Y-h*.02)
        cap=(1-np.sqrt((X/(w*.20))**2+((Y-h*.33)/(h*.23))**2))*min(w*.20,h*.23)
        arch=np.minimum(arch,np.where(Y<=h*.33,h,cap))
        field=np.minimum(field,-arch)
    return field.astype('float32')

def ray_hits(vertices,faces,origin,direction,length):
    tri=vertices[faces];o=np.asarray(origin);d=np.asarray(direction,dtype=float);d/=np.linalg.norm(d)
    e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];p=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,p)
    good=np.abs(det)>1e-12;inv=np.zeros_like(det);inv[good]=1/det[good];tvec=o-tri[:,0];u=np.einsum('ij,ij->i',tvec,p)*inv;q=np.cross(tvec,e1);v=q@d*inv;t=np.einsum('ij,ij->i',e2,q)*inv
    hits=np.sort(t[good&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)&(t>1e-6)&(t<length)])
    return [float(t) for i,t in enumerate(hits) if i==0 or t-hits[i-1]>1e-5]

def semantic_checks(v,f,w,h,d,spec,fm):
    kind=spec['cavity'];tests=[]
    def test(name,origin,direction,length,expected):
        hits=ray_hits(v,f,origin,direction,length);okay=len(hits)==0 if expected=='empty' else len(hits)>=2
        tests.append({'name':name,'origin_m':origin,'direction':direction,'length_m':length,'expected':expected,'surface_hits_m':hits,'ok':okay})
    if kind=='pipe':test('open_end_to_end_tunnel',[-w,.5*h,0],[1,0,0],w*2,'empty')
    if kind=='arch':test('open_front_to_back_passage',[0,.25*h,d],[0,0,-1],d*2,'empty')
    if kind in ['box_tunnel','arched_tunnel']:
        test('open_front_to_back_passage',[0,.30*h,d],[0,0,-1],d*2,'empty')
        test('solid_roof',[0,h*1.2,0],[0,-1,0],h*.95,'solid')
    if kind=='jar':
        test('open_top_to_inside',[0,h*1.2,0],[0,-1,0],h*.7,'empty')
        test('solid_jar_bottom',[0,h*1.2,0],[0,-1,0],h*1.5,'solid')
    if kind=='coconut':
        test('open_front_door',[0,h*.22,d],[0,0,-1],d,'empty')
        test('rear_shell_wall',[0,h*.22,d],[0,0,-1],d*2,'solid')
    if kind=='cargo_well':
        test('open_cargo_well',[w*.13,h*1.2,0],[0,-1,0],h*.86,'empty')
        test('solid_hold_floor',[w*.13,h*1.2,0],[0,-1,0],h*1.5,'solid')
    if kind=='lantern':
        cy=spec.get('cavity_parameters',{}).get('center_y',.56)*h
        test('open_lamp_chamber_front_back',[0,cy,d],[0,0,-1],d*2,'empty')
        test('open_lamp_chamber_left_right',[-w,cy,0],[1,0,0],w*2,'empty')
    if kind=='anchor':
        holes=ndi.binary_fill_holes(fm)&~fm;labels,n=ndi.label(holes);sizes=np.bincount(labels.ravel());sizes[0]=0
        if n:
            yy,xx=np.nonzero(labels==sizes.argmax());px=(xx.mean()/(fm.shape[1]-1)-.5)*w;py=(1-yy.mean()/(fm.shape[0]-1))*h
            test('open_anchor_eye',[float(px),float(py),d],[0,0,-1],d*2,'empty')
        else:tests.append({'name':'open_anchor_eye','ok':False,'message':'No actual white eye aperture in source front mask.'})
    return tests

def build(root,spec,out):
    id=spec['id'];paths={view:source_for(root,id,view,spec.get('source_projects')) for view in ['front','right','top']};refs={view:source_image(path) for view,path in paths.items()};fm,rm,tm=[refs[v][1] for v in ['front','right','top']]
    if spec.get('fill_silhouette_holes',False):fm,rm,tm=[ndi.binary_fill_holes(m) for m in [fm,rm,tm]]
    w=spec['width_m'];h=w*fm.shape[0]/fm.shape[1];d_right=h*rm.shape[1]/rm.shape[0];d_top=w*tm.shape[0]/tm.shape[1];d=(d_right+d_top)*.5
    step=w/spec.get('resolution',150);x=np.arange(-w/2-3*step,w/2+3.1*step,step);y=np.arange(-3*step,h+3.1*step,step);z=np.arange(-d/2-3*step,d/2+3.1*step,step);X=x[:,None,None];Y=y[None,:,None];Z=z[None,None,:]
    front=sample_sdf(fm,(X+w/2)/w,1-Y/h,w/fm.shape[1]);right=sample_sdf(rm,(d/2-Z)/d,1-Y/h,h/rm.shape[0]);top=sample_sdf(tm,(X+w/2)/w,(Z+d/2)/d,w/tm.shape[1]);field=np.minimum(np.minimum(front,right),top).astype('float32')
    field=ndi.gaussian_filter(field,spec.get('smoothing_voxels',.65));field=carve(field,X,Y,Z,w,h,d,spec,fm,rm)
    labels,n=ndi.label(field>0);counts=np.bincount(labels.ravel());counts[0]=0;threshold=max(8,int(counts.max()*.0003));keep=counts>=threshold;keep[0]=False
    if spec.get('largest_component_only',False):keep[:]=False;keep[counts.argmax()]=True
    discarded=int(counts[~keep].sum());field[(labels>0)&~keep[labels]]=-step
    verts,faces,_,_=marching_cubes(field,0,spacing=(step,)*3,allow_degenerate=False);verts+=np.array([x[0],y[0],z[0]])
    volume=np.einsum('ij,ij->i',verts[faces[:,0]],np.cross(verts[faces[:,1]],verts[faces[:,2]])).sum()/6
    if volume<0:faces=faces[:,[0,2,1]]
    original_triangles=len(faces)
    if len(faces)>spec.get('triangle_budget',18000):
        verts,faces=fast_simplification.simplify(verts.astype(float),faces.astype(np.int32),target_count=spec.get('triangle_budget',18000),agg=5)
    edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(verts),len(verts))).tocsr()
    mesh_components=connected_components(graph,directed=False,return_labels=False)
    # Test exactly the float32 coordinates that will be serialized.
    verts=verts.astype(np.float32).astype(float);semantic=semantic_checks(verts,faces,w,h,d,spec,fm)
    donors={v:save_donor(path,out/(id+'-'+v+'.png')) for v,path in paths.items()}
    g=Glb();fallback=Image.open(out/(id+'-front.png')).convert('RGB').convert('RGBA');material=g.material(fallback,'generated_front_fallback');uv=np.clip(np.c_[(verts[:,0]+w/2)/w,1-verts[:,1]/h],0,1);g.mesh(verts,faces,uv,material,id+'_three_view_ornament')
    # Smooth surface normals preserve coherent three-view projection planes.
    cross=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]]);normal=np.zeros_like(verts)
    for corner in range(3):np.add.at(normal,faces[:,corner],cross)
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-15)
    good=np.linalg.norm(cross,axis=1)>1e-20;prim=g.doc['meshes'][0]['primitives'][0];prim['attributes']['NORMAL']=g.accessor(normal[faces[good]].reshape(-1,3),'VEC3');model=out/(id+'.glb');g.save(model)
    components=int(mesh_components);okay=int(keep.sum())==1 and components==1 and all(t['ok'] for t in semantic)
    return {'id':id,'name_zh':spec['name_zh'],'ok':okay,'output':str(model),'sha256':sha(model),'triangles':g.triangles,'dense_triangles':original_triangles,'simplifier':'fast-simplification 0.2.0 QEM agg=5; validate exported topology and openings after reduction','projection_bounds':{'width':w,'height':h,'depth':d},'actual_bounds_m':[verts.min(0).tolist(),verts.max(0).tolist()],'source_depth_estimates_m':{'right':d_right,'top':d_top},'connected_components':components,'discarded_tiny_voxels':discarded,'semantic_checks':semantic,'materials':donors,'cavity_method':spec['cavity'],'limitations':['Outside shape is inferred from independent three-view art with normalized extents; landmarks are not dense registered.','Known construction cavities are modeled from source silhouettes plus explicit profile constraints; hidden geometry remains inferred.','Opposite faces reuse corresponding front/right/top donors.','Discrete ray probes certify these sampled apertures/floors, not general fish navigation or collision freedom.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--id');a=p.parse_args();root=a.root.resolve();specs=read(root/'resources/aquascape/decor-10-v1.json')['assets'];a.output.mkdir(parents=True,exist_ok=True);rows=[]
    for spec in specs:
        if a.id and spec['id']!=a.id:continue
        row=build(root,spec,a.output);rows.append(row);print(json.dumps({'id':row['id'],'ok':row['ok'],'triangles':row['triangles'],'components':row['connected_components'],'failed_semantics':[t['name'] for t in row['semantic_checks'] if not t['ok']]}),flush=True)
    okay=bool(rows) and all(r['ok'] for r in rows);name='build.validation.json' if not a.id else a.id+'-build.validation.json';(a.output/name).write_text(json.dumps({'schema_version':1,'command':'aquascape.build-decor-ten','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':rows,'failures':[r['id'] for r in rows if not r['ok']],'visual_review':'pending','user_acceptance':'pending'},ensure_ascii=False,indent=2),encoding='utf-8');return 0 if okay else 1

if __name__=='__main__':raise SystemExit(main())
