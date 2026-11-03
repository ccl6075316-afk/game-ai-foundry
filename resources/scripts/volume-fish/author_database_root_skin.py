"""Author an explicit complete-bank minimax skin fit into the packed source."""
import argparse,json,hashlib,sys
from pathlib import Path
import bpy,numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from source_snapshot import rig_action_snapshot
from export_packed_fish_source import export_packed_source,float_uv_signature,part_signature,material_signature
from restore_fin_source_normals import geometry_signature,normal_attribute_signature
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);fit=json.loads(a.fit.read_text());source=Path(fit['source_blend']);model=Path(fit['model']);assert sha(source)==fit['source_blend_sha256'] and sha(model)==fit['model_sha256'];out=a.output.resolve();assert not out.exists() and out.is_relative_to(ROOT/'projects/fishing-2d/experiments/five-fish-database-20261103');d,b=read_glb(model);p=d['meshes'][0]['primitives'][0];pos=arrays(d,b,p['attributes']['POSITION']);joints=[d['nodes'][j]['name']for j in d['skins'][0]['joints']];bpy.ops.wm.open_mainfile(filepath=str(source));ob=next(o for o in bpy.data.objects if o.type=='MESH');mesh=ob.data
def invariant():return (rig_action_snapshot(),float_uv_signature(mesh),part_signature(mesh),material_signature(mesh.materials[0]),normal_attribute_signature(ob),[tuple(v.co)for v in mesh.vertices],[tuple(p.vertices)for p in mesh.polygons])
before=invariant();proposals={};changes=[]
for row in fit['changes']:
 i=row['vertex'];part=next(p for p in d['extras']['geometry_parts']if p['vertex_start']<=i<p['vertex_start']+p['vertex_count']);assert part['role']=='fin' and part['logical_name']==row['fin'];new={joints[j]:w for j,w in zip(row['new_joints'],row['new_weights'])if w>1e-8};lo=part['vertex_start'];hi=lo+part['vertex_count'];copies=np.flatnonzero(np.linalg.norm(pos[lo:hi]-pos[i],axis=1)<1e-8)+lo
 for v in copies:
  v=int(v)
  if v in proposals:assert proposals[v]==new;continue
  old={ob.vertex_groups[g.group].name:g.weight for g in mesh.vertices[v].groups if g.weight>0};expected={joints[j]:w for j,w in zip(row['old_joints'],row['old_weights'])if w>0};assert old.keys()==expected.keys() and max(abs(old[k]-expected[k])for k in old)<1e-6
  for g in list(mesh.vertices[v].groups):ob.vertex_groups[g.group].remove([v])
  for name,w in new.items():ob.vertex_groups[name].add([v],w,'REPLACE')
  proposals[v]=new;changes.append({'vertex':v,'fin':row['fin'],'old_named_weights':old,'new_named_weights':new})
assert before==invariant();mesh['foundry_normal_geometry_sha256']=geometry_signature(ob);out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));proof=export_packed_source(out/'fish.glb');report={'ok':True,'kind':'complete_bank_root_skin_source_authoring','fit':{'path':str(a.fit.resolve()),'sha256':sha(a.fit)},'original_model_sha256':sha(model),'original_blend_sha256':sha(source),'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'changed_root_vertices':changes,'geometry_UV_normals_RGB_rig_actions_unchanged':True,'export':proof,'formal_acceptance':False};(out/'source-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'skin-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'changed_root_vertices':len(changes)}))
