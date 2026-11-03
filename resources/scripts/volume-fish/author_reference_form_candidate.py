"""Author a frozen reference-form plan into a fresh packed editable source.

The plan supplies all geometry; this writer does not infer species anatomy.
Unchanged topology/UV/material/weights/rig/action guards remain enforced.
"""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy,numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
from export_packed_fish_source import float_uv_signature,part_signature,material_signature,SOURCE_VERTEX,export_packed_source
from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);plan=json.loads(a.plan.read_text());out=a.plan.resolve().parent
assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not(out/'fish.blend').exists()and not(out/'fish.glb').exists()
for r in plan['inputs'].values():assert sha(r['path'])==r['sha256']
bpy.ops.wm.open_mainfile(filepath=plan['inputs']['blend']['path']);obs=[o for o in bpy.data.objects if o.type=='MESH'];assert len(obs)==1;ob=obs[0];m=ob.data
before=(rig_action_snapshot(),float_uv_signature(m),part_signature(m),material_signature(m.materials[0]),[[(w.group,w.weight)for w in v.groups]for v in m.vertices]);old=np.array(plan['old_positions_gltf']);new=np.array(plan['new_positions_gltf']);norm=np.array(plan['new_normals_gltf']);assert len(m.vertices)==len(old)==len(new)==len(norm)
for v in m.vertices:
 i=int(round(m.attributes[SOURCE_VERTEX].data[v.index].value));assert i==v.index
 assert np.max(np.abs(np.array(v.co)-old[i,[0,2,1]]*np.array([1,-1,1])))<1e-7
 v.co=(new[i,0],-new[i,2],new[i,1])
ns=[]
for loop in m.loops:
 n=norm[loop.vertex_index];m.attributes[EXACT_NORMAL_ATTRIBUTE].data[loop.index].vector=n;ns.append((n[0],-n[2],n[1]))
m.normals_split_custom_set(ns);m.update();after=(rig_action_snapshot(),float_uv_signature(m),part_signature(m),material_signature(m.materials[0]),[[(w.group,w.weight)for w in v.groups]for v in m.vertices]);assert before==after
m['foundry_normal_geometry_sha256']=geometry_signature(ob);m['foundry_exact_normal_sha256']=normal_attribute_signature(ob);m['foundry_reference_form_plan_sha256']=sha(a.plan)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));proof=export_packed_source(out/'fish.glb')
result={'ok':True,'kind':'frozen_reference_form_source_authoring','plan_sha256':sha(a.plan),'blend_sha256':sha(out/'fish.blend'),'model_sha256':sha(out/'fish.glb'),'same_topology_UV_pixels_weights_rig_actions':True,'proof':proof,'formal_acceptance':False};(out/'source-authoring.validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':True,'stage':plan['stage'],'triangles':proof['triangles'],'model':str(out/'fish.glb')}))
xy=np.flatnonzero(np.any(old[:,:2]!=new[:,:2],axis=1))
if len(xy):
 receipt={'ok':True,'kind':'explicit_finite_fin_XY_delta','model_sha256':sha(out/'fish.glb'),'plan':{'path':str(a.plan.resolve()),'sha256':sha(a.plan)},'vertices':[{'vertex':int(i),'old_XY':old[i,:2].tolist(),'new_XY':new[i,:2].tolist()}for i in xy],'scope':'Enumerated source-owned subpixel fin correction; not XY-exact. Whole current source/physical/visual rechecks remain mandatory.','formal_acceptance':False};(out/'xy-authoring.validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
else:
 for filename in ['xy-authoring.validation.json','xy-preservation.validation.json']:
  parent=Path(plan['inputs']['model']['path']).parent/filename
  if parent.exists():
   inherited=json.loads(parent.read_text());assert inherited['model_sha256']==plan['inputs']['model']['sha256'];receipt={'ok':True,'kind':'inherited_enumerated_XY_delta_not_new_authoring','model_sha256':sha(out/'fish.glb'),'parent_XY_receipt':{'path':str(parent),'sha256':sha(parent)},'geometry_authoring':{'path':str(out/'source-authoring.validation.json'),'sha256':sha(out/'source-authoring.validation.json')},'vertices':inherited['vertices'],'scope':'This step leaves every XY row exact to its parent; previous explicitly enumerated source-owned XY correction preserved, no new acceptance.'};(out/'xy-preservation.validation.json').write_text(json.dumps(receipt,indent=2)+'\n');break
for filename in ['skin-authoring.validation.json','skin-preservation.validation.json']:
 parent=Path(plan['inputs']['model']['path']).parent/filename
 if parent.exists():
  inherited=json.loads(parent.read_text());assert inherited['model_sha256']==plan['inputs']['model']['sha256']
  report={'ok':True,'kind':'inherited_enumerated_skin_delta_not_new_skin_fit','model_sha256':sha(out/'fish.glb'),'parent_skin_receipt':{'path':str(parent),'sha256':sha(parent)},'geometry_authoring':{'path':str(out/'source-authoring.validation.json'),'sha256':sha(out/'source-authoring.validation.json')},'changed_root_vertices':inherited['changed_root_vertices'],'scope':'Exact same weight guard in this geometry author preserves the previously enumerated root fit. No new fit or acceptance inferred.'};(out/'skin-preservation.validation.json').write_text(json.dumps(report,indent=2)+'\n');break
