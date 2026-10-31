"""Budgeted scenery rebuild. Original paintings, poses and native rigs are retained.

Leaves recover the source parametric surface and rebuild a coarse closed polygon,
with internal longitudinal samples. Solids use welded QEM and original three-view
paint. Every final exported complete instance is measured against a shared budget.
"""
import argparse, copy, hashlib, io, json, math
from pathlib import Path
import numpy as np
import pymeshlab
from PIL import Image
from build_from_art import Glb, split_leaves, foreground
from rig_plant_current import read_glb, array, append
from clean_plant_material_edges import source_parts
from leaf_polygon import polygon, ears, cross
from repair_plant_contours import features

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def budget_type(row,policy):
    if row.get('animated') or row.get('category')=='plant':
        return 'ribbon_plant' if row['id'] in policy['ribbon_plants'] else 'broadleaf_plant'
    return row.get('category','decor') if row.get('category') in ['rock','wood'] else 'decor'

def compact(g):
    """Remove superseded dense buffers; keep every live animation/skin/image byte."""
    old=copy.deepcopy(g.doc);binary=bytes(g.bin);g.bin=bytearray()
    g.doc['bufferViews']=[];g.doc['accessors']=[];views={};accessors={}
    def view(i):
        if i not in views:
            v=old['bufferViews'][i];offset=v.get('byteOffset',0)
            views[i]=g.view(binary[offset:offset+v['byteLength']],v.get('target'))
        return views[i]
    def acc(i):
        if i not in accessors:
            a=copy.deepcopy(old['accessors'][i]);a['bufferView']=view(a['bufferView'])
            accessors[i]=len(g.doc['accessors']);g.doc['accessors'].append(a)
        return accessors[i]
    for mesh in g.doc['meshes']:
        for p in mesh['primitives']:
            p['attributes']={k:acc(v) for k,v in p['attributes'].items()}
            if 'indices' in p:p['indices']=acc(p['indices'])
    for skin in g.doc.get('skins',[]):skin['inverseBindMatrices']=acc(skin['inverseBindMatrices'])
    for animation in g.doc.get('animations',[]):
        for s in animation['samplers']:s['input']=acc(s['input']);s['output']=acc(s['output'])
    for im in g.doc.get('images',[]):im['bufferView']=view(im['bufferView'])

def primitive(g,v,f,uv,mat,attrs=None):
    tri=np.asarray(v,dtype='float32')[f];n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm=np.linalg.norm(n,axis=1)
    if np.any(norm<1e-20):raise ValueError('Collapsed final triangle')
    a={'POSITION':g.accessor(tri.reshape(-1,3),'VEC3'),'NORMAL':g.accessor(np.repeat(n/norm[:,None],3,axis=0),'VEC3'),'TEXCOORD_0':g.accessor(uv[f].reshape(-1,2),'VEC2')}
    for k,(values,kind,component) in (attrs or {}).items():a[k]=append(g,values[f].reshape(-1,values.shape[1]),kind,component,34962)
    return {'attributes':a,'material':mat,'mode':4}

def low_polygon(mask,max_boundary,interior_count):
    tolerance=.65;original=polygon(mask,.3)
    while True:
        p=polygon(mask,tolerance)
        if len(p)<=max_boundary:break
        tolerance*=1.16
        if tolerance>max(mask.shape)*.25:raise ValueError('Cannot keep a usable leaf boundary')
    # The narrow basal stem and tip are mandatory motion landmarks, even when
    # a large silhouette tolerance would otherwise remove their last pixels.
    p[np.argmin(p[:,1])]=original[np.argmin(original[:,1])]
    p[np.argmax(p[:,1])]=original[np.argmax(original[:,1])]
    f=ears(p).tolist()
    # Insert interior points along the leaf's longitudinal center without
    # multiplying every contour triangle by dozens of horizontal strips.
    for frac in np.linspace(.18,.82,interior_count):
        y=p[:,1].min()+np.ptp(p[:,1])*frac
        hits=[]
        for a,b in zip(p,np.roll(p,-1,axis=0)):
            if (a[1]<=y<b[1]) or (b[1]<=y<a[1]):hits.append(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]))
        if len(hits)<2:continue
        q=np.array([(min(hits)+max(hits))*.5,y])
        for j,face in enumerate(f):
            a,b,c=p[face];sign=np.array([cross(b-a,q-a),cross(c-b,q-b),cross(a-c,q-c)])
            if (sign>1e-6).all():
                k=len(p);p=np.vstack([p,q]);f[j]=[face[0],face[1],k];f.extend([[face[1],face[2],k],[face[2],face[0],k]])
                break
    return p,np.asarray(f),tolerance

def welded(v,f=None):
    if f is None:f=np.arange(len(v)).reshape(-1,3)
    v,ids=np.unique(v,axis=0,return_inverse=True)
    return v,ids[f]

def simplified(v,f,count):
    if len(f)>count:
        ms=pymeshlab.MeshSet();ms.add_mesh(pymeshlab.Mesh(v.astype(float),f.astype('int32')))
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=int(count),preservetopology=True,preservenormal=True,qualitythr=.3,autoclean=True)
        v=ms.current_mesh().vertex_matrix();f=ms.current_mesh().face_matrix()
    v,f=welded(v.astype('float32'),f)
    tri=v[f];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    return v,f[area>1e-20]

def build_plant(root,row,source,out,policy):
    doc,binary=read_glb(source);g=Glb();g.doc=copy.deepcopy(doc);g.bin=bytearray(binary)
    images=split_leaves(source_parts(root,row['id']));leaves=[m for m in doc['meshes'] if m['name'].startswith('traced_leaf_')]
    others=len(doc['meshes'])-len(leaves);reports=[]
    kind=budget_type(row,policy);target=int(policy['types'][kind]['hard_limit']*.94)
    # Each closed leaf: 4*boundary + 4*interior - 4 triangles.
    per_leaf=(target-others*10-12)//len(leaves);internal=0
    boundary=max(6,min(30,(per_leaf+4)//4))
    for mi,mesh in enumerate(g.doc['meshes']):
        old=doc['meshes'][mi]['primitives'][0];attrs=old['attributes'];uv=array(doc,binary,attrs['TEXCOORD_0']);v=array(doc,binary,attrs['POSITION'])
        if mesh['name'].startswith('traced_leaf_'):
            leaf_id=int(mesh['name'].rsplit('_',1)[1])-1;mask=foreground(images[leaf_id%len(images)]);h,w=mask.shape
            tuv=uv.reshape(-1,3,2);signed=cross(tuv[:,1]-tuv[:,0],tuv[:,2]-tuv[:,0]);front=np.repeat(signed<-1e-8,3);back=np.repeat(signed>1e-8,3)
            fit_front=np.linalg.lstsq(features(uv[front]),v[front],rcond=None)[0];fit_back=np.linalg.lstsq(features(uv[back]),v[back],rcond=None)[0]
            # V7 geometry was fitted using edge UVs, but serialized with pixel
            # centers. Recover the exact serialized surface in serialized UVs.
            p,f,tol=low_polygon(mask,boundary,internal);count=len(p)
            tex=(p+.5)/[w,h];F=features(tex)
            positions=np.vstack([F@fit_front,F@fit_back]).astype('float32');uvs=np.tile(tex,(2,1))
            fs=[*map(tuple,f[:,[0,2,1]]),*map(tuple,f+count)]
            edge={}
            for face in f:
                for a,b in zip(face,np.roll(face,-1)):edge.setdefault(tuple(sorted((a,b))),[]).append((a,b))
            for used in edge.values():
                if len(used)==1:
                    a,b=used[0];fs.extend([(a,b,b+count),(a,b+count,a+count)])
            fs=np.asarray(fs)
            old_j=array(doc,binary,attrs['JOINTS_0']);old_w=array(doc,binary,attrs['WEIGHTS_0']);joints=np.unique(old_j[old_w>0])
            t=np.clip(1-uvs[:,1],0,1);knots=np.array([.08,.28,.48,.68,.88]);lo=np.clip(np.searchsorted(knots,t,side='right')-1,0,3);alpha=np.clip((t-knots[lo])/.2,0,1)
            ids=np.zeros((len(positions),4),dtype=np.uint16);weights=np.zeros((len(positions),4),dtype=np.float32)
            ids[:,0]=joints[lo];ids[:,1]=joints[lo+1];weights[:,0]=1-alpha;weights[:,1]=alpha
            reports.append({'mesh':mesh['name'],'boundary_vertices':count-internal,'contour_tolerance_px':tol,'triangles':len(fs)})
        else:
            # Rebuild the existing tubular root along its exact original rings.
            # These tiny tubes have inconsistent legacy cap winding, which can
            # prevent QEM collapse. Three sides preserve their centerline.
            positions=[];uvs=[];fs=[];rings=np.unique(uv[:,0])
            if mesh['name'].startswith('attachment_root_'):rings=rings[[0,-1]]
            for ring in rings:
                for angle in [0,.3,.7]:
                    ix=np.flatnonzero(np.isclose(uv[:,0],ring))
                    j=ix[np.argmin(abs(uv[ix,1]-angle))]
                    positions.append(v[j]);uvs.append(uv[j])
            for k in range(len(rings)-1):
                for j in range(3):
                    a=k*3+j;b=k*3+(j+1)%3;c=b+3;dd=a+3
                    fs.extend([(a,dd,c),(a,c,b)])
            fs.extend([(0,1,2),((len(rings)-1)*3,(len(rings)-1)*3+2,(len(rings)-1)*3+1)])
            positions=np.asarray(positions);uvs=np.asarray(uvs);fs=np.asarray(fs)
            ids=np.zeros((len(positions),4),dtype=np.uint16);weights=np.zeros((len(positions),4),dtype=np.float32);weights[:,0]=1
        mesh['primitives']=[primitive(g,positions,fs,uvs,old['material'],{'JOINTS_0':(ids,'VEC4',5123),'WEIGHTS_0':(weights,'VEC4',5126)})]
    g.doc['asset']['generator']='Foundry budgeted closed leaf shells; original native rig and artwork'
    compact(g);g.save(out)
    return {'leaves':reports,'budget_type':kind}

def build_solid(row,source,out,policy):
    doc,binary=read_glb(source);vertices=[]
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            v=array(doc,binary,p['attributes']['POSITION'])
            if 'indices' in p:v=v[array(doc,binary,p['indices']).ravel()]
            vertices.append(v)
    v,f=welded(np.vstack(vertices));kind=budget_type(row,policy);v,f=simplified(v,f,policy['types'][kind]['preferred'])
    topology_cleanup=None
    if len(f)>policy['types'][kind]['hard_limit'] and kind=='rock':
        # Some old rock hulls contain scores of accidental microscopic tunnels
        # traced from bright painted pits. Rocks have no intentional apertures.
        # Reuse the same reviewed outer silhouettes, filling their tiny holes.
        from build_from_three_views import silhouette,sample_sdf
        from scipy import ndimage as ndi
        from skimage.measure import marching_cubes
        root=Path(__file__).resolve().parents[3]
        spec=next(s for s in load(root/'projects/fishing-2d/game/assets/aquascape-v5/solid-profiles.json')['assets'] if s['id']==row['id'])
        masks=[silhouette(root/spec['materials'][view],True)[1] for view in ['front','right','top']]
        b=row['projection_bounds'];w,h,depth=b['width'],b['height'],b['depth'];step=w/100
        x=np.arange(-w/2-3*step,w/2+3.1*step,step);y=np.arange(-3*step,h+3.1*step,step);z=np.arange(-depth/2-3*step,depth/2+3.1*step,step)
        X=x[:,None,None];Y=y[None,:,None];Z=z[None,None,:]
        fields=[sample_sdf(masks[0],(X+w/2)/w,1-Y/h,w/masks[0].shape[1]),sample_sdf(masks[1],(depth/2-Z)/depth,1-Y/h,h/masks[1].shape[0]),sample_sdf(masks[2],(X+w/2)/w,(Z+depth/2)/depth,w/masks[2].shape[1])]
        field=ndi.gaussian_filter(np.minimum(np.minimum(fields[0],fields[1]),fields[2]),1.2)
        v,f,_,_=marching_cubes(field.astype('float32'),0,spacing=(step,)*3,allow_degenerate=False);v+=np.array([x[0],y[0],z[0]])
        volume=np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()/6
        if volume<0:f=f[:,[0,2,1]]
        v,f=simplified(v,f,policy['types'][kind]['preferred']);topology_cleanup='Removed unintended tiny painted-pit tunnels using the same three outer source silhouettes; no new artwork.'
    g=Glb();g.doc=copy.deepcopy(doc);g.bin=bytearray(binary)
    material=doc['meshes'][0]['primitives'][0]['material'];b=row['projection_bounds']
    uv=np.clip(np.c_[(v[:,0]+b['width']/2)/b['width'],1-v[:,1]/b['height']],0,1)
    p=primitive(g,v,f,uv,material)
    # Original three-view shader uses smooth object-space surface normals.
    normals=np.zeros_like(v);tri=v[f];n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    for i in range(3):np.add.at(normals,f[:,i],n)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-15)
    p['attributes']['NORMAL']=g.accessor(normals[f].reshape(-1,3),'VEC3')
    g.doc['meshes']=[{'name':row['id'],'primitives':[p]}];g.doc['nodes']=[{'name':row['id'],'mesh':0}];g.doc['scenes']=[{'nodes':[0]}];g.doc['scene']=0
    compact(g);g.save(out)
    return {'budget_type':kind,'topology_cleanup':topology_cleanup}

def metrics(path):
    d,b=read_glb(path);tri=0;verts=0
    for node in d['nodes']:
        if 'mesh' not in node:continue
        for p in d['meshes'][node['mesh']]['primitives']:
            if p.get('mode',4)!=4:raise ValueError('Only triangle primitives are supported')
            verts+=d['accessors'][p['attributes']['POSITION']]['count']
            tri+=d['accessors'][p.get('indices',p['attributes']['POSITION'])]['count']//3
    return {'triangles':tri,'vertices':verts,'bytes':path.stat().st_size,'sha256':sha(path)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--input',type=Path);p.add_argument('--id');p.add_argument('--deploy',action='store_true',help='Validate and update the specified live catalog(s); visual review stays pending');a=p.parse_args()
    root=a.root.resolve();game=root/'projects/fishing-2d/game';out=a.output.resolve()
    if not out.is_relative_to(game/'assets'):raise ValueError('Output must be inside game/assets')
    policy=load(root/'resources/aquascape/geometry-budgets.json');rows=[]
    catalogs=[a.input] if a.input else [game/'assets/aquascape-v5/catalog.json',game/'assets/aquascape-decor-v1/catalog.json']
    deployed=[]
    for catpath in catalogs:
        catalog=load(catpath)
        for row in catalog['assets']:
            if a.id and row['id']!=a.id:continue
            src=game/row.get('pre_budget_model',row['model']).removeprefix('res://');dest=out/('plants' if row.get('animated') else 'solids')/(row['id']+'.glb');dest.parent.mkdir(parents=True,exist_ok=True)
            detail=build_plant(root,row,src,dest,policy) if row.get('animated') else build_solid(row,src,dest,policy)
            before=metrics(src);after=metrics(dest);budget=policy['types'][detail['budget_type']]
            if after['triangles']>budget['hard_limit']:raise ValueError(row['id']+' exceeds hard budget')
            row.update(pre_budget_model=row.get('pre_budget_model',row['model']),model='res://'+dest.relative_to(game).as_posix(),geometry_budget={**budget,'type':detail['budget_type']},geometry_revision='budgeted-v9')
            result={'id':row['id'],'name_zh':row.get('name_zh'),'source':str(src),'output':str(dest),'before':before,'after':after,**detail};rows.append(result)
            print(json.dumps({'id':row['id'],'before':before['triangles'],'after':after['triangles'],'hard_limit':budget['hard_limit']}),flush=True)
        candidate=out/(catpath.parent.name+'-catalog.json');save(candidate,catalog);deployed.append((catpath,candidate))
    save(a.report,{'schema_version':1,'command':'aquascape.optimize-scenery','ok':True,'status':'done','next_action':'human_review','inputs':{'policy_sha256':sha(root/'resources/aquascape/geometry-budgets.json')},'outputs':rows,'failures':[],'visual_review':'pending','user_acceptance':'pending'})
    if a.deploy:
        from validate_scenery_budget import validate
        report=validate(root,[candidate for _,candidate in deployed],a.report.with_name('deployment.validation.json'))
        if not report['ok']:raise ValueError('Deployment blocked: '+str(report['failures']))
        for live,candidate in deployed:save(live,load(candidate))

if __name__=='__main__':main()
