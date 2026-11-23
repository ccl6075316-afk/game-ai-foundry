import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'motion-r5'
def snapshot():
 data={}
 for o in bpy.data.collections['GRAY_REVIEW'].objects:
  if o.type=='MESH':data[o.name]={'positions':[list(v.co)for v in o.data.vertices],'faces':[list(f.vertices)for f in o.data.polygons],'weights':[[(o.vertex_groups[g.group].name,g.weight)for g in v.groups]for v in o.data.vertices],'uv':[[list(x.uv)for x in layer.data]for layer in o.data.uv_layers],'materials':[m.name for m in o.data.materials]}
  elif o.type=='ARMATURE':data[o.name]={'bones':[(b.name,b.parent.name if b.parent else None,[list(row)for row in b.matrix_local])for b in o.data.bones]}
 return data
bpy.ops.wm.open_mainfile(filepath=str(R/'motion-r4/octopus-actions.blend'));old=snapshot()
bpy.ops.wm.open_mainfile(filepath=str(O/'octopus-actions.blend'));new=snapshot();skin=bpy.data.objects['Octopus_gray_skin'];coll=bpy.data.collections['GRAY_REVIEW'];rig=next(o for o in coll.objects if o.type=='ARMATURE')
paths=json.loads((R/'motion-r3/rest/gray-build.validation.json').read_text())['control_paths'];roots=[Vector(p[0])for p in paths];dirs=[(Vector(p[-1])-Vector(p[0])).normalized()for p in paths];lengths=[(Vector(p[-1])-Vector(p[0])).length for p in paths]
protected=[];changed=[]
for k,(a,b)in enumerate(zip(old[skin.name]['positions'],new[skin.name]['positions'])):
 v=Vector(a);i=min(range(8),key=lambda j:(v-roots[j]-(v-roots[j]).dot(dirs[j])*dirs[j]).length);f=(v-roots[i]).dot(dirs[i])/lengths[i]
 if f<=.35:protected.append((Vector(a)-Vector(b)).length)
 if a!=b:changed.append(k)
checks={'topology_uv_weights_rest_bones_preserved':all({k:v for k,v in d.items()if k!='positions'}=={k:v for k,v in new[n].items()if k!='positions'}for n,d in old.items()),'head_body_web_proximal_skin_unchanged':max(protected)==0,'non_arm_accessories_unchanged':all(d==new[n]for n,d in old.items()if n not in ['Octopus_gray_skin','Paired_sucker_rows_512_cups']),'all_vertices_weighted':all(len(v.groups)>0 for o in coll.objects if o.type=='MESH'for v in o.data.vertices),'weights_normalized':all(abs(sum(g.weight for g in v.groups)-1)<1e-5 for o in coll.objects if o.type=='MESH'for v in o.data.vertices),'maximum_four_weights':all(len(v.groups)<=4 for o in coll.objects if o.type=='MESH'for v in o.data.vertices)}
bm=bmesh.new();bm.from_mesh(skin.data);checks['closed_skin']=all(e.is_manifold for e in bm.edges);checks['rest_nonzero_faces']=min(f.calc_area()for f in bm.faces)>1e-12;bm.free()
tri=sum(len(p.vertices)-2 for o in coll.objects if o.type=='MESH'for p in o.data.polygons);checks['budget']=tri<=50000
bpy.ops.object.select_all(action='DESELECT')
for o in coll.objects:o.select_set(True)
bpy.context.view_layer.objects.active=rig;cold=O/'octopus-actions.cold.glb';bpy.ops.export_scene.gltf(filepath=str(cold),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks['source_cold_export_identical']=sha(cold)==sha(O/'octopus-actions.glb')
d={'ok':all(checks.values()),'checks':checks,'changed_skin_vertices':len(changed),'protected_skin_vertices':len(protected),'triangles':tri,'bones':len(rig.data.bones),'source_sha256':sha(O/'octopus-actions.blend'),'model_sha256':sha(O/'octopus-actions.glb'),'cold_sha256':sha(cold),'baseline_source_sha256':sha(R/'motion-r4/octopus-actions.blend')};(O/'source.validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
