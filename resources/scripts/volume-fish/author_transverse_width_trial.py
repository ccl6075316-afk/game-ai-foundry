"""Apply a frozen per-vertex transverse field to an existing packed editable fish.

Single-fish experiment: no part splitting, topology/UV/skin/rig/animation edits.
Positions and exact source normals are authored into a fresh blend. Cold export
and physical/visual review are separate operations; this is not asset acceptance.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'portable'))
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
from export_packed_fish_source import float_uv_signature,part_signature,material_signature,SOURCE_VERTEX
from source_snapshot import rig_action_snapshot

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['plan','output','report']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);plan=json.loads(a.plan.read_text(encoding='utf8'))
 root=HERE.parents[2];out=a.output.resolve();report=a.report.resolve()
 assert out.is_relative_to(root/'projects/fishing-2d/experiments') and report.parent==out.parent
 assert not out.exists()and not report.exists();out.parent.mkdir(parents=True,exist_ok=True)
 for row in plan['inputs'].values():assert sha(row['path'])==row['sha256']
 bpy.ops.wm.open_mainfile(filepath=plan['inputs']['blend']['path'])
 obs=[o for o in bpy.data.objects if o.type=='MESH'];assert len(obs)==1
 ob=obs[0];m=ob.data;assert len(m.vertices)==len(plan['old_positions_gltf'])
 rig_before=rig_action_snapshot();uv_before=float_uv_signature(m);part_before=part_signature(m);mat_before=material_signature(m.materials[0])
 counts=(len(m.vertices),len(m.polygons),len(m.loops));old=np.array(plan['old_positions_gltf']);new=np.array(plan['new_positions_gltf']);norm=np.array(plan['new_normals_gltf'])
 assert np.array_equal(old[:,:2],new[:,:2])
 assert np.isfinite(new).all()and np.isfinite(norm).all()
 for v in m.vertices:
  i=int(round(m.attributes[SOURCE_VERTEX].data[v.index].value));assert i==v.index
  expected=(old[i,0],-old[i,2],old[i,1]);assert max(abs(v.co[k]-expected[k])for k in range(3))<1e-7
  v.co=(new[i,0],-new[i,2],new[i,1])
 loop_norm=[]
 for loop in m.loops:
  n=norm[loop.vertex_index];m.attributes[EXACT_NORMAL_ATTRIBUTE].data[loop.index].vector=n
  loop_norm.append((n[0],-n[2],n[1]))
 m.normals_split_custom_set(loop_norm);m.update()
 assert rig_action_snapshot()==rig_before
 assert (len(m.vertices),len(m.polygons),len(m.loops))==counts
 assert float_uv_signature(m)==uv_before and part_signature(m)==part_before and material_signature(m.materials[0])==mat_before
 # Fresh authoring signatures describe the deliberately edited source, not a validation bypass.
 # The exporter still verifies these and every unchanged UV/part/material/rig dependency.
 m['foundry_normal_geometry_sha256']=geometry_signature(ob)
 m['foundry_exact_normal_sha256']=normal_attribute_signature(ob)
 m['foundry_transverse_trial_plan_sha256']=sha(a.plan)
 bpy.ops.wm.save_as_mainfile(filepath=str(out),check_existing=False)
 result={'ok':True,'kind':'packed_fish_transverse_authoring','plan_sha256':sha(a.plan),'blend':str(out),'blend_sha256':sha(out),'mesh_count':1,'vertices':counts[0],'triangles':counts[1],'same_XY':True,'same_topology_UV_part_ownership_material_skin_rig_actions':True,'new_mesh_parts':0,'formal_acceptance':False}
 report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
