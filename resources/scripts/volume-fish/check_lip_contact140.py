"""Blender: verify complete raised-strip contact, relief, binding and triangles."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build as closed_sign_index
root=Path(sys.argv[sys.argv.index('--')+1]);rows=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for s in ['bluegill','zander','grass_carp','nile_tilapia','peacock_bass']:
 body=root/s/'geometry/body.bound.json';lips=root/s/('geometry/upper-lip.bound.json' if s=='peacock_bass' else 'lips/contact-lips.mesh.json');cfg=json.loads((root/s/'geometry.plan.json').read_text());d=json.loads(body.read_text());v=[];n=[];t=[];offset=0
 for p in d['parts']:
  v.extend(p['vertices']);n.extend(p['normals']);t.extend((np.array(p['triangles']).reshape(-1,3)[:,[0,2,1]]+offset).tolist());offset+=len(p['vertices'])
 v=np.array(v);n=np.array(n);t=np.array(t)
 volume=np.einsum('ij,ij->i',v[t[:,0]],np.cross(v[t[:,1]],v[t[:,2]])).sum()/6
 if volume<0:t=t[:,[0,2,1]]
 tree=BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True);parts=[];ray=Vector((.231,.371,.899)).normalized();inside=closed_sign_index(v,t)
 for p in json.loads(lips.read_text())['parts']:
  if s in ['bluegill','grass_carp','nile_tilapia'] and p['name']=='lower':
   prior=root.parent/'mouth-rollout-136'/s/'lips/bound/lips.bound.json';baseline=next(q for q in json.loads(prior.read_text())['parts'] if q['name']=='lower');assert p==baseline,'Accepted lower lip changed'
   old=json.loads(Path(cfg['body']).read_text())['parts'];current=d['parts']
   for aa,bb in zip(old,current):
    av=np.array(aa['vertices'],dtype='f4');bv=np.array(bb['vertices'],dtype='f4');mask=av[:,1]<=-.005;assert np.array_equal(av[mask],bv[mask]),'Retained lower lip support moved'
   assert max(q[1] for q in p['vertices'])<-.005
   parts.append({'part':'lower','status':'retained_139_exact','source_sha256':sha(prior),'body_support_positions_unchanged':True,'scope':'Accepted lower lip preserved; not claimed to pass the new raised-upper-strip contact test.'});continue
  points=np.array(p['vertices']);faces=np.array(p['triangles']).reshape(-1,3);areas=np.linalg.norm(np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]]),axis=1)*.5
  weights=np.array(p['weights']);assert np.isfinite(points).all() and np.min(weights)>=0 and np.max(abs(weights.sum(1)-1))<1e-6
  assert np.min(areas)>1e-17,('Collapsed lip triangle',s,p['name'],float(areas.min()))
  probes=np.concatenate([points,points[faces].mean(1),(points[faces[:,0]]+points[faces[:,1]])*.5,(points[faces[:,1]]+points[faces[:,2]])*.5,(points[faces[:,2]]+points[faces[:,0]])*.5]);dist=[]
  for point in probes:
   hit,normal,face,distance=tree.find_nearest(Vector(point));assert hit is not None
   # Match the076 full-fin gate: a closed-body oriented ray classifies inside;
   # nearest interpolated normals are not valid at mouth edges/corners.
   signed=float(-distance if inside(point) else distance);dist.append(signed)
  peak=cfg.get('relief_native',cfg.get('upper_lip_cap_relief',0))+cfg.get('surface_offset_native',0)
  assert min(dist)>=-.00003,('Lip penetrates actual body',s,p['name'],min(dist))
  assert max(dist)<=peak+.00025,('Lip floats above declared relief',s,p['name'],max(dist),peak)
  parts.append({'part':p['name'],'vertices':len(points),'triangles':len(faces),'minimum_triangle_area':float(areas.min()),'probes':len(probes),'signed_distance_native_min_max':[min(dist),max(dist)],'declared_peak_native':peak})
 result={'ok':True,'species':s,'body_sha256':sha(body),'lips_sha256':sha(lips),'parts':parts,'scope':'Static final lip vertices/edge midpoints/face centres against actual body; body/fin/action gates and visual readability remain separate.'};(root/s/'lip-contact.validation.json').write_text(json.dumps(result,indent=2));rows.append(result);print('LIP_CONTACT140',s,'passed',flush=True)
(root/'lip-contact140.validation.json').write_text(json.dumps({'ok':True,'records':rows},indent=2))
