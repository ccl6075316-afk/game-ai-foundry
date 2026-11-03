"""Blender: fit complete original grass-carp pectoral seam to its real rest body."""
import sys,json,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/grass_carp';model=r/'width-r3/fish.glb';out=r/'width-r5';assert not out.exists();out.mkdir();d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);idx=arrays(d,b,pr['indices']);normal=arrays(d,b,pr['attributes']['NORMAL']);new=v.copy();body=np.concatenate([idx[q['index_start']:q['index_start']+q['index_count']]for q in d['extras']['geometry_parts']if q['role']in ['body_skin','mouth']]).reshape(-1,3);tree=BVHTree.FromPolygons(v.tolist(),body.tolist(),all_triangles=True);plan=json.loads((r/'gates-r1/fin.plan.json').read_text());scale=json.loads((r/'gates-r1/delivery-config.json').read_text())['model_scale']if False else .0
spec=json.loads((r/'gates-r1/spec.json').read_text());scale=spec['viewer']['model_scale'];records=[]
for name in ['Pectoral_left_mesh','Pectoral_right_mesh']:
 q=next(p for p in d['extras']['geometry_parts']if p['source_node']==name);ids=np.arange(q['vertex_start'],q['vertex_start']+q['vertex_count']);points=v[ids];roots=np.array(plan['items'][0]['fins'][name]['rest_points_gltf']);dist=np.linalg.norm(points[:,None]-roots,axis=2).min(1);rootids=np.flatnonzero(dist<2e-6);assert len(rootids)>=len(roots);side=np.sign(points[:,2].mean());shifts={}
 for i in rootids:
  x,y,z=points[i];hit=tree.ray_cast(Vector((x,y,side*2)),Vector((0,0,-side)),4)[0];assert hit is not None;delta=float(hit.z+side*.15/(1000*scale)-z);key=tuple(np.round(uv[ids[i]],6));shifts.setdefault(key,[]).append(delta)
 shifts={k:float(np.mean(z))for k,z in shifts.items()};delta=np.zeros(len(ids));root_uv=uv[ids[rootids]]
 for i in range(len(ids)):
  ds=np.linalg.norm(root_uv-uv[ids[i]],axis=1);j=int(np.argmin(ds));base=shifts[tuple(np.round(root_uv[j],6))];weight=max(0,1-float(ds[j])/.018);weight=weight*weight*(3-2*weight);delta[i]=base*weight
 # All seam duplicates share the same displacement, including wall UV rows.
 for i in rootids:
  copies=np.flatnonzero(np.linalg.norm(points-points[i],axis=1)<1e-8);delta[copies]=shifts[tuple(np.round(uv[ids[i]],6))]
 _,weld=np.unique(np.round(points,7),axis=0,return_inverse=True)
 for group in np.unique(weld):
  members=np.flatnonzero(weld==group);rs=np.intersect1d(members,rootids);delta[members]=float(np.mean(delta[rs if len(rs)else members]))
 new[ids,2]+=delta;records.append({'name':name,'original_complete_root_vertices':len(rootids),'maximum_transverse_displacement_mm':float(abs(delta).max()*scale*1000),'rest_target_outward_mm':.15,'source_uv_blend_distance':.018})
result={'kind':'single_fish_transverse_width_trial','species':'grass_carp','stage':'complete_pectoral_root_rest_fit','inputs':{k:{'path':str(p),'sha256':sha(p)}for k,p in [('model',model),('blend',model.with_suffix('.blend')),('original_root_plan',r/'gates-r1/fin.plan.json')]},'old_positions_gltf':v.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':normal.tolist(),'fit':records,'reason':'Original static root gap1.1156mm,490 left1.5015/right1.3390mm; complete seam fitted to actual own body by transverse ray, paired native UV displacement averaged. Complete original bank/tolerances retained. No geometry pass inferred.'};(out/'deformation.plan.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(records))
