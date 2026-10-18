"""Blender: freeze full authored root bands from current volume handoff blends.

Usage: -- output.plan.json handoff.json [handoff.json ...]
Only supports authored source-t attributes, never guesses projected coordinates.
"""
import bpy,json,sys,hashlib
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 args=sys.argv[sys.argv.index('--')+1:];items=[]
 for filename in args[1:]:
  handoff=json.loads(Path(filename).read_text(encoding='utf8'));p=json.loads(Path(handoff['profile']).read_text(encoding='utf8'));bpy.ops.wm.open_mainfile(filepath=handoff['outputs']['blend']);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.view_layer.update();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices];length=max(v.x for v in points)-min(v.x for v in points);fins={}
  for f in p['fins']:
   assert f.get('source_baseline') and f.get('root_attachment'),'Every new fin needs a frozen full baseline and projected attachment'
   for suffix in (['_left','_right'] if f['paired'] else ['']):
    o=bpy.data.objects[f['name']+suffix];attr=o.data.attributes.get('foundry_fin_source_t');assert attr and attr.domain=='POINT';ids=[v.index for v in o.data.vertices if attr.data[v.index].value<=f['root_attachment']['root_band']+1e-7];assert len(ids)>=2,(o.name,len(ids));coords=[o.matrix_world@o.data.vertices[i].co for i in ids]
    fins[o.name]={'ids':ids,'rest_points_gltf':[[q.x,q.z,-q.y] for q in coords],'vertices':len(o.data.vertices),'rule':'Complete authored source_baseline distance band, persisted before projection in foundry_fin_source_t','source_baseline':f['source_baseline'],'source_t_max':f['root_attachment']['root_band']}
  items.append({'species':p['species'],'model':handoff['outputs']['glb'],'model_sha256':sha(handoff['outputs']['glb']),'body':'Closed_body','body_bones':[f'body_{i:02d}' for i in range(len(p['rig']['spine']))],'length_native':length,'scale_cm':p['real_length_cm']/length,'fins':fins,'handoff':str(Path(filename).resolve()),'profile':handoff['profile'],'profile_sha256':sha(handoff['profile']),'source_sha256':handoff['source']['sha256']})
 Path(args[0]).write_text(json.dumps({'kind':'authored_fin_completion_plan','items':items},indent=2));print('FROZEN_ROOTS',[(e['species'],len(e['fins'])) for e in items])
if __name__=='__main__':main()
