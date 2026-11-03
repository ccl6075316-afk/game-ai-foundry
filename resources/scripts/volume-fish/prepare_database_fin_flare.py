"""Prepare measured free-fin flare from its own preserved source_t domains.

Full original root vertices and root bands stay fixed; no collar/tolerance edits.
This is a proposal only; requires current source/volume and full posed rechecks.
"""
import argparse,json,hashlib,sys
from pathlib import Path
import bpy,numpy as np
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE/'portable')]
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__)
for k in ['model','projection','fin-plan','failure','output']:p.add_argument('--'+k,type=Path,required=True)
p.add_argument('--parts',nargs='+',required=True);p.add_argument('--outward-mm',type=float,required=True);p.add_argument('--full-at-t',type=float,required=True);p.add_argument('--root-band',type=float,required=True);p.add_argument('--model-scale',type=float,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve();assert not out.exists() and out.is_relative_to(ROOT/'projects/fishing-2d/experiments/five-fish-database-20261103');failure=json.loads(a.failure.read_text());assert not failure['ok'] and failure['model_sha256']==sha(a.model);plan=json.loads(a.fin_plan.read_text())['items'][0];d,b=read_glb(a.model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);n=arrays(d,b,pr['attributes']['NORMAL']);new=v.copy();nn=n.copy();bpy.ops.wm.open_mainfile(filepath=str(a.projection.resolve()));records=[]
for name in a.parts:
 ob=bpy.data.objects[name];sv=np.array([[q.co.x,q.co.z,-q.co.y]for q in ob.data.vertices]);attr=ob.data.attributes['foundry_fin_source_t'];st=np.array([q.value for q in attr.data]);tree=KDTree(len(sv))
 for i,q in enumerate(sv):tree.insert(q,i)
 tree.balance();part=next(x for x in d['extras']['geometry_parts']if x['logical_name']==name);ids=np.arange(part['vertex_start'],part['vertex_start']+part['vertex_count']);matches=[tree.find(v[i])for i in ids];assert max(x[2]for x in matches)<2e-6;t=st[[x[1]for x in matches]]
 root=np.array(plan['fins'][name]['rest_points_gltf']);fixed=np.array([np.min(np.linalg.norm(root-q,axis=1))<2e-6 for q in v[ids]]);u=np.clip((t-a.root_band)/(a.full_at_t-a.root_band),0,1);weight=u*u*(3-2*u);weight[fixed]=0;side=np.sign(np.mean(v[ids,2]));amount=side*a.outward_mm/(1000*a.model_scale);new[ids,2]+=amount*weight
 # source_t is curved on these fins. Recompute finite face normals rather than
 # pretending its gradient is planar. Preserve the original facing hemisphere.
 tris=arrays(d,b,pr['indices']).reshape(-1)[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3);acc=np.zeros_like(v)
 for tri in tris:
  face=np.cross(new[tri[1]]-new[tri[0]],new[tri[2]]-new[tri[0]])
  for i in tri:
   if face@n[i]>0:acc[i]+=face
 lengths=np.linalg.norm(acc[ids],axis=1);assert np.all(lengths>1e-15);nn[ids]=acc[ids]/lengths[:,None]
 records.append({'name':name,'original_root_vertices_held':int(fixed.sum()),'normals':'Finite current face area averages within original facing hemisphere; curved source_t not treated as planar.','maximum_outward_mm':float(np.max(np.abs(new[ids,2]-v[ids,2]))*a.model_scale*1000)})
result={'kind':'single_fish_transverse_width_trial','species':a.model.parent.parent.name,'stage':'measured-free-fin-flare','inputs':{k:{'path':str(q.resolve()),'sha256':sha(q)}for k,q in [('model',a.model),('blend',a.model.with_suffix('.blend')),('projection',a.projection),('fin_plan',a.fin_plan),('failure',a.failure)]},'old_positions_gltf':v.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':nn.tolist(),'flare':{'outward_mm':a.outward_mm,'full_at_source_t':a.full_at_t,'root_band':a.root_band,'records':records,'original_full_root_domain_and_thresholds_unchanged':True},'formal_acceptance':False};out.mkdir();(out/'deformation.plan.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['flare']))
