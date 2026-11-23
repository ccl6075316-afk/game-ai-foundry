import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-r3'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(OUT/'octopus-roll.glb'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');skin=bpy.data.objects['Octopus_gray_skin']
for track in rig.animation_data.nla_tracks:track.mute=True
# Skin in GLB has split normals/UV vertices, so connected faces are compared by
# coincident rest positions rather than imported vertex indices.
key=lambda v:tuple(round(x,5) for x in v)
facekeys=[set(key(skin.data.vertices[i].co) for i in p.vertices) for p in skin.data.polygons]
reports=[]
for name,duration in [('SingleArmRoll',10),('EightArmReach',14)]:
 action=next(a for a in bpy.data.actions if name in a.name);rig.animation_data.action=action
 if action.slots:rig.animation_data.action_slot=action.slots[0]
 frames=round(duration*30);samples=[];first=None;last=None
 for frame in range(0,frames+1,5):
  bpy.context.scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get();ev=skin.evaluated_get(deps);me=ev.to_mesh();verts=[ev.matrix_world@v.co for v in me.vertices]
  if frame==0:first=verts
  if frame==frames:last=verts
  finite=all(math.isfinite(x) for v in verts for x in v)
  if frame%5==0 or frame==frames:
   tree=BVHTree.FromPolygons(verts,[list(p.vertices) for p in me.polygons],all_triangles=True)
   pairs=[(a,b) for a,b in tree.overlap(tree) if a<b and not facekeys[a].intersection(facekeys[b])]
   areas=[p.area for p in me.polygons]
   samples.append({'frame':frame,'finite':finite,'nonadjacent_surface_intersections':len(pairs),'example_pairs':pairs[:5],'min_area':min(areas),'bounds':[[min(v[k] for v in verts),max(v[k] for v in verts)] for k in range(3)]})
  ev.to_mesh_clear()
 seam=max((a-b).length for a,b in zip(first,last))
 reports.append({'clip':name,'duration':duration,'loop_max_vertex_error':seam,'samples':samples,'max_nonadjacent_intersections':max(s['nonadjacent_surface_intersections'] for s in samples)})
checks={'native_clips_present':len(reports)==2,'finite_samples':all(s['finite'] for r in reports for s in r['samples']),'loop_closed':all(r['loop_max_vertex_error']<1e-4 for r in reports),'no_sampled_nonadjacent_intersections':all(r['max_nonadjacent_intersections']==0 for r in reports)}
checks['nondegenerate_sampled_faces']=all(s['min_area']>1e-12 for r in reports for s in r['samples'])
report={'kind':'octopus_trial_native_animation_check','model_sha256':hashlib.sha256((OUT/'octopus-roll.glb').read_bytes()).hexdigest(),'checks':checks,'clips':reports,'ok':all(checks.values()),'limitations':['Sampled triangles, not continuous-time proof','Cups/accessory contact and physical dynamics not comprehensively validated']}
(OUT/'motion.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'checks':checks,'clips':[{k:v for k,v in r.items() if k!='samples'} for r in reports]}))
