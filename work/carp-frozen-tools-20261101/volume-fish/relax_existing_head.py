"""Blender: preserve rig/topology, relax a frozen forehead and unify cap UVs."""
import sys,json,hashlib,struct
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from collections import Counter
sys.path.insert(0,str(Path(__file__).parent))
def read_glb(path):
 raw=path.read_bytes();size=struct.unpack_from('<I',raw,12)[0]
 return json.loads(raw[20:20+size]),raw[28+size:]
def accessor(d,b,index):
 a=d['accessors'][index];v=d['bufferViews'][a['bufferView']];dt=np.dtype('<'+{5126:'f4',5125:'u4',5123:'u2',5121:'u1'}[a['componentType']]);c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
 return np.ndarray((a['count'],c),dtype=dt,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',c*dt.itemsize),dt.itemsize)).copy()

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
path=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(path.read_text());assert sha(plan['model'])==plan['model_sha256']
d,b=read_glb(Path(plan['model']));node=next(n for n in d['nodes'] if n.get('name')=='Closed_body');parts=[]
for si,prim in enumerate(d['meshes'][node['mesh']]['primitives']):
 a=prim['attributes'];v=accessor(d,b,a['POSITION']).astype(float);n=accessor(d,b,a['NORMAL']).astype(float)
 parts.append({'source_surface':si,'vertices':v,'normals':n,'reference_positions':v.copy(),'reference_normals':n.copy(),
 'uv':accessor(d,b,a['TEXCOORD_0']).astype(float),'uv2':accessor(d,b,a['TEXCOORD_1']).astype(float) if 'TEXCOORD_1' in a else np.zeros((len(v),2)),
 'joints':accessor(d,b,a['JOINTS_0']).astype(int),'weights':accessor(d,b,a['WEIGHTS_0']).astype(float),'triangles':accessor(d,b,prim['indices']).reshape(-1,3).astype(int)})
allp=np.concatenate([p['vertices'] for p in parts]);_,first,inverse=np.unique(np.round(allp,7),axis=0,return_index=True,return_inverse=True);original=allp[first].copy();p=original.copy();tri=[];at=0
for part in parts:
 tri.append(inverse[part['triangles']+at]);at+=len(part['vertices'])
tri=np.concatenate(tri);edges=np.unique(np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0)
aa=np.r_[edges[:,0],edges[:,1]];bb=np.r_[edges[:,1],edges[:,0]];degree=np.bincount(aa,minlength=len(p))
cfg=plan['relax'];weight=smooth((p[:,0]-cfg['start_x'])/(cfg['full_x']-cfg['start_x']))*smooth((p[:,1]-cfg['lower_y'])/(cfg['full_y']-cfg['lower_y']))
eye=plan['eye_protection'];radius=np.linalg.norm((p[:,:2]-eye['center'])/eye['radius'],axis=1);weight*=smooth((radius-1)/.4)
for _ in range(cfg['iterations']):
 total=np.zeros_like(p);np.add.at(total,aa,p[bb]);target=total/np.maximum(degree[:,None],1)
 # Keep the transverse envelope and axial source positions. Correct only
 # the observed upper-head height oscillation within a fixed displacement.
 p[:,1]+=cfg['factor']*weight*(target[:,1]-p[:,1]);delta=np.clip(p[:,1]-original[:,1],-cfg['maximum_displacement_native'],cfg['maximum_displacement_native']);p[:,1]=original[:,1]+delta
assert np.array_equal(p[:,[0,2]],original[:,[0,2]])
norm=np.zeros_like(p);cross=np.cross(p[tri[:,2]]-p[tri[:,0]],p[tri[:,1]]-p[tri[:,0]])
for k in range(3):np.add.at(norm,tri[:,k],cross)
norm/=np.maximum(np.linalg.norm(norm,axis=1),1e-20)[:,None]
source=parts[0];source_positions=source['reference_positions'].copy();source_uv=source['uv'].copy();st=source['triangles'].copy();bvh=BVHTree.FromPolygons(source['vertices'].tolist(),st.tolist(),all_triangles=True)
def uv_at(point):
 point,_,face,distance=bvh.find_nearest(Vector(point));a,b,c=source_positions[st[face]];u=b-a;v=c-a;w=np.asarray(point)-a;uu=u@u;uv=u@v;vv=v@v;den=uu*vv-uv*uv
 assert den>1e-25
 y=(vv*(w@u)-uv*(w@v))/den;z=(uu*(w@v)-uv*(w@u))/den
 return source_uv[st[face]].T@np.array([1-y-z,y,z]),distance
offset=0;uv_errors=[];retired_uv_vertices=0
for part in parts:
 ids=inverse[offset:offset+len(part['vertices'])];offset+=len(ids)
 part['vertices']=p[ids]
 geometric=norm[ids].copy()
 # glTF source winding and the Godot imported winding differ. Align each
 # recomputed orientation with the original outward side before interpolation;
 # blending opposite normals otherwise creates an artificial shading cliff.
 geometric[np.sum(geometric*part['normals'],axis=1)<0]*=-1
 newnormal=part['normals']*(1-weight[ids,None])+geometric*weight[ids,None]
 newnormal/=np.maximum(np.linalg.norm(newnormal,axis=1),1e-20)[:,None];part['normals']=newnormal
 if part['source_surface']==0 and plan.get('retire_eye_uv_shift'):
  reference=part['reference_positions'];w,h=plan['source_size'];preferred=np.c_[reference[:,0]+.5,.5-reference[:,1]*w/h]
  shifted=np.linalg.norm(part['uv']-preferred-np.asarray(plan['retire_eye_uv_shift']),axis=1)<1e-5
  retired_uv_vertices=int(shifted.sum());assert retired_uv_vertices>0
  part['uv'][shifted]=preferred[shifted]
 if part['source_surface'] in plan['unify_cap_surfaces']:
  values=[uv_at(v) for v in part['reference_positions']];part['uv']=np.array([v[0] for v in values]);uv_errors.extend(v[1] for v in values)
 for key in part:
  if isinstance(part[key],np.ndarray):part[key]=part[key].ravel().tolist() if key=='triangles' else part[key].tolist()
out=Path(plan['output']);out.mkdir(parents=True,exist_ok=True);body=out/'body.bound.json';body.write_text(json.dumps({'parts':parts},separators=(',',':')))
names=[d['nodes'][i]['name'] for i in d['skins'][node['skin']]['joints']]
report={'ok':True,'species':plan['species'],'plan_sha256':sha(path),'maximum_displacement_native':float(abs(p-original).max()),'protected_eye_points_moved':int(np.count_nonzero(np.linalg.norm(p[radius<=1]-original[radius<=1],axis=1)>0)),
 'caps_nearest_exterior_uv_max_distance':float(max(uv_errors)),'retired_old_eye_uv_shift_vertices':retired_uv_vertices,'transverse_and_axial_positions_unchanged':True,'topology_and_skinning_unchanged':True,'source_aliases':plan['unify_cap_surfaces'],'outputs':{'body':sha(body)},'summary':{'species':plan['species'],'skin_joint_names':names},'scope':'Candidate forehead relaxation and continuous existing exterior-source UV transport onto adjacent cap surfaces. Independent jaw, eyes, fins and source pixels unchanged. Visual/body/fin/motion gates required.'}
(out/'skinning.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
