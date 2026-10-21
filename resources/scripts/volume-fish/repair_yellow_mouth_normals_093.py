"""Diagnostic normal-only correction for the frozen 093 mouth trial.

Area weighted face normals, welded by coincident POSITION within each primitive.
No cross-primitive lip blending. Original posterior normals are preserved.
"""
from pathlib import Path
import sys,json,hashlib,copy
import numpy as np
R=next(p for p in Path(__file__).resolve().parents if (p/'cli/gamefactory.py').exists())
sys.path.insert(0,str(R/'resources/scripts/volume-fish'))
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
W=R/'projects/fishing-2d/experiments/blender-fish/yellow-mouth-093'
source=W/'yellow_croaker.glb';target=W/'candidate-normal.glb'
d,b=read_glb(source);before=copy.deepcopy(d);binary=bytearray(b)
mi=next(n['mesh']for n in d['nodes']if n.get('name')=='Closed_body')
reports=[]
for pi,p in enumerate(d['meshes'][mi]['primitives']):
 v=accessor(d,b,p['attributes']['POSITION']);n=accessor(d,b,p['attributes']['NORMAL']);f=accessor(d,b,p['indices']).reshape(-1,3);t=v[f]
 area=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);summed=np.zeros(v.shape,dtype=float)
 for corner in range(3):np.add.at(summed,f[:,corner],area)
 # Rounded at 1e-7 native length: only close duplicate seams, not distinct lips.
 unique,inv=np.unique(np.round(v,7),axis=0,return_inverse=True);joined=np.zeros(unique.shape,dtype=float);np.add.at(joined,inv,summed)
 smooth=joined[inv];smooth/=np.maximum(np.linalg.norm(smooth,axis=1)[:,None],1e-15)
 bad=np.linalg.norm(smooth,axis=1)<.5;smooth[bad]=n[bad]
 blend=np.clip((v[:,0]-.29)/.025,0,1);blend=blend*blend*(3-2*blend)
 revised=n*(1-blend[:,None])+smooth*blend[:,None];revised/=np.maximum(np.linalg.norm(revised,axis=1)[:,None],1e-15)
 revised[v[:,0]<=.29]=n[v[:,0]<=.29];revised=revised.astype('<f4')
 head=v[:,0]>.29;angle=np.degrees(np.arccos(np.clip((n*smooth).sum(1),-1,1)))
 binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(revised.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=revised.nbytes,target=34962));ac=len(d['accessors']);d['accessors'].append(dict(bufferView=vi,componentType=5126,count=len(revised),type='VEC3',min=revised.min(0).tolist(),max=revised.max(0).tolist()));p['attributes']['NORMAL']=ac
 reports.append(dict(surface=pi,changed_normal_vertices=int(np.any(revised!=n,axis=1).sum()),head_old_normal_face_normal_angle_degrees_percentiles_50_90_99_100=np.percentile(angle[head],[50,90,99,100]).tolist(),posterior_normals_exact=bool(np.array_equal(revised[~head],n[~head]))))
write(target,d,binary)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(ok=True,input_sha256=sha(source),model_sha256=sha(target),normal_only=True,position_uv_indices_rig_weights_images_unchanged=True,method='Area weighted actual deformed triangles; equal-position welding within each primitive; smooth 0.29-0.315 normal transition; skin/oral boundary remains separate',surfaces=reports,limits='Numerical normal discrepancy alone does not prove positions visually smooth. Compare native-pose grey renders; no formal model replacement or acceptance.')
(W/'normal-repair.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
