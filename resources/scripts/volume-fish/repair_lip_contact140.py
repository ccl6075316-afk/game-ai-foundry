"""Blender: lift only small curved-strip chords buried in the final body."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build as closed_sign_index
root=Path(sys.argv[sys.argv.index('--')+1]);records=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for s in ['bluegill','zander','grass_carp','nile_tilapia']:
 body=root/s/'geometry/body.bound.json';source=root/s/'lips/aligned-lips.mesh.json';d=json.loads(body.read_text());v=[];n=[];t=[];offset=0
 for p in d['parts']:
  v.extend(p['vertices']);n.extend(p['normals']);t.extend((np.array(p['triangles']).reshape(-1,3)[:,[0,2,1]]+offset).tolist());offset+=len(p['vertices'])
 v=np.array(v);n=np.array(n);t=np.array(t)
 volume=np.einsum('ij,ij->i',v[t[:,0]],np.cross(v[t[:,1]],v[t[:,2]])).sum()/6
 if volume<0:t=t[:,[0,2,1]]
 tree=BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True);lips=json.loads(source.read_text());metrics=[];ray=Vector((.231,.371,.899)).normalized()
 inside=closed_sign_index(v,t)
 def contact(point):
  hit,normal,face,distance=tree.find_nearest(Vector(point));contained=inside(point)
  # Offset along the actual oriented geometric face. A transported shading
  # normal at the oral seam can point across the neighbouring skin surface.
  return float(-distance if contained else distance),np.array(normal)
 def outside_projection(point,relief):
  hit,normal,_,_=tree.find_nearest(Vector(point));margin=max(relief,.000045);candidates=[]
  for sign in [1,-1]:
   q=np.array(hit)+np.array(normal)*margin*sign
   if not inside(q):candidates.append(q)
  if not candidates:
   for direction in [normal,-normal,ray,-ray,Vector((1,0,0)),Vector((0,-1,0))]:
    origin=Vector(point)
    for _ in range(8):
     q,_,_,distance=tree.ray_cast(origin,direction,.003)
     if q is None:break
     candidate=np.array(q)+np.array(direction)*margin
     if not inside(candidate):candidates.append(candidate);break
     origin=q+direction*1e-7
  assert candidates,('No nearby exterior lip projection',s,point.tolist())
  return min(candidates,key=lambda q:np.linalg.norm(q-point))
 for part in lips['parts']:
  if s in ['bluegill','grass_carp','nile_tilapia'] and part['name']=='lower':
   prior=root.parent/'mouth-rollout-136'/s/'lips/bound/lips.bound.json';baseline=next(p for p in json.loads(prior.read_text())['parts'] if p['name']=='lower');part.clear();part.update(baseline)
   metrics.append({'part':'lower','retained_139_unchanged':True,'source':str(prior),'source_sha256':sha(prior),'reason':'User accepted the lower lip;140 issue is the upper band/head. Complete original geometry/material/binding retained, outside the head deformation support.'});continue
  original=np.array(part['vertices']);p=original.copy();faces=np.array(part['triangles']).reshape(-1,3);before=0;original_count=len(p);adjusted=0
  for i,point in enumerate(p):
   distance,_=contact(point)
   if distance<-.000025:
    p[i]=outside_projection(point,.000045);adjusted+=1
  displacement=np.linalg.norm(p-original,axis=1);assert displacement.max()<.0002,('Excessive original strip contact correction',s,part['name'],displacement.max())
  trial=json.loads((root/s/'lips/trial.plan.json').read_text());L,R=trial['join_rows'][part['name']]
  for row in [L,R]:assert np.all(displacement[1+row*17:1+(row+1)*17]<1e-10),'Contact correction moves an original source join'
  part['vertices']=p.tolist()
  for iteration in range(4):
   bad=0;worst=0
   for face in faces:
    probes=[p[face].mean(0),(p[face[0]]+p[face[1]])*.5,(p[face[1]]+p[face[2]])*.5,(p[face[2]]+p[face[0]])*.5];depth=min(contact(q)[0] for q in probes);worst=min(worst,depth)
    if depth<-.000025:bad+=1
   if iteration==0:before=worst
   if not bad:break
   if iteration==2:
    # Sharp oral creases can keep a few new chords below the surface. Fair
    # only the inserted points outward; retain original vertices/source joins.
    start=p.copy()
    for turn in range(16):
     lift=np.zeros(len(p));remaining=0
     for face in faces:
      probes=[p[face].mean(0),(p[face[0]]+p[face[1]])*.5,(p[face[1]]+p[face[2]])*.5,(p[face[2]]+p[face[0]])*.5];depth=min(contact(q)[0] for q in probes)
      if depth<-.000025:
       remaining+=1;ids=face[face>=original_count];assert len(ids),'An original source edge needs structural revision';lift[ids]=np.maximum(lift[ids],-depth+.000045)
     if not remaining:break
     assert turn<15,('Local contact fairing did not converge',s,part['name'],remaining)
     for idx in np.flatnonzero(lift):
      current,_=contact(p[idx]);p[idx]=outside_projection(p[idx],max(0,current)+lift[idx])
     assert np.linalg.norm(p-start,axis=1).max()<.00025,'Contact fairing exceeds the declared shallow strip scope'
    worst=min(contact(q)[0] for face in faces for q in [p[face].mean(0),(p[face[0]]+p[face[1]])*.5,(p[face[1]]+p[face[2]])*.5,(p[face[2]]+p[face[0]])*.5])
    break
   assert iteration<3,('Strip contact subdivision did not converge',s,part['name'],bad,worst)
   # Uniform conforming refinement of this strip avoids T-junction cracks.
   # New points inherit exact source coordinates and four-weight binding,
   # while their position follows the body with interpolated declared relief.
   edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0);lookup={};positions=list(p);attributes={k:list(part[k]) for k in ['normals','uv','uv2','colors','joints','weights']}
   for a,b in edges:
    edge=(int(a),int(b));idx=len(positions);lookup[edge]=idx;middle=(p[a]+p[b])*.5;hit,_,face,_=tree.find_nearest(Vector(middle));_,normal=contact(middle);relief=max(0.,(contact(p[a])[0]+contact(p[b])[0])*.5)
    positions.append(outside_projection(middle,relief).tolist())
    for key in ['uv','uv2','colors']:attributes[key].append(((np.array(part[key][a])+np.array(part[key][b]))*.5).tolist())
    attributes['normals'].append(normal.tolist());accum={}
    for at in [a,b]:
     for j,w in zip(part['joints'][at],part['weights'][at]):accum[j]=accum.get(j,0)+w*.5
    ordered=sorted(accum.items(),key=lambda q:-q[1])[:4];total=sum(w for j,w in ordered);ordered+=[(0,0)]*(4-len(ordered));attributes['joints'].append([j for j,w in ordered]);attributes['weights'].append([w/total for j,w in ordered])
   children=[]
   for a,b,c in faces:
    ab=lookup[tuple(sorted((int(a),int(b))))];bc=lookup[tuple(sorted((int(b),int(c))))];ca=lookup[tuple(sorted((int(c),int(a))))];children.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
   p=np.array(positions);faces=np.array(children);part.update(attributes);part['vertices']=p.tolist();part['triangles']=faces.ravel().tolist()
  part['vertices']=p.tolist();metrics.append({'part':part['name'],'prior_worst_chord_distance':before,'final_worst_chord_distance':worst,'original_vertices_projected_outward':adjusted,'maximum_original_vertex_shift':float(displacement.max()),'added_vertices':len(p)-original_count,'subdivision_levels':iteration,'source_join_rows_unchanged':True})
 target=root/s/'lips/contact-lips.mesh.json';target.write_text(json.dumps(lips,separators=(',',':')));report={'ok':True,'species':s,'source_sha256':sha(source),'body_sha256':sha(body),'target_sha256':sha(target),'parts':metrics,'scope':'Conforming strip refinement follows actual curved skin. Small pre-existing vertex burial reprojected; original source join geometry/UV preserved; new points interpolate UV and normalized rig weights. Closed-body ray classification; no tolerance changes.'};(root/s/'lip-contact-repair.validation.json').write_text(json.dumps(report,indent=2));records.append(report);print('LIP_CONTACT_REPAIR',s,metrics,flush=True)
(root/'lip-contact-repair140.validation.json').write_text(json.dumps({'ok':True,'records':records},indent=2))
