import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;O=R/'motion-r4';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(O/'octopus-actions.glb'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');skin=bpy.data.objects['Octopus_gray_skin'];cups=next(o for o in bpy.data.objects if o.name.startswith('Paired_sucker'))
for tr in rig.animation_data.nla_tracks:tr.mute=True
meshes=[skin,cups];faces=[[list(p.vertices) for p in o.data.polygons]for o in meshes];centers=[[sum((o.data.vertices[v].co for v in f),Vector())/len(f)for f in ff]for o,ff in zip(meshes,faces)];reports=[]
for clip,frames in [('TightRoll',range(0,301,15)),('ProbeTouch',range(0,481,15)),('AlternatingTouch',range(0,481,15))]:
 a=bpy.data.actions[clip];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
 for f in frames:
  bpy.context.scene.frame_set(f);deps=bpy.context.evaluated_depsgraph_get();trees=[]
  for o,ff in zip(meshes,faces):
   ev=o.evaluated_get(deps);me=ev.to_mesh();trees.append(BVHTree.FromPolygons([ev.matrix_world@v.co for v in me.vertices],ff,all_triangles=True));ev.to_mesh_clear()
  remote=[(a,b)for a,b in trees[0].overlap(trees[1])if(centers[0][a]-centers[1][b]).length>.15]
  cc=[(a,b)for a,b in trees[1].overlap(trees[1])if a<b and (centers[1][a]-centers[1][b]).length>.15]
  reports.append({'clip':clip,'frame':f,'nonlocal_cup_skin_intersections':len(remote),'nonlocal_cup_cup_intersections':len(cc),'examples_skin':remote[:5],'examples_cups':cc[:5]})
d={'model_sha256':hashlib.sha256((O/'octopus-actions.glb').read_bytes()).hexdigest(),'ok':all(s['nonlocal_cup_skin_intersections']==0 and s['nonlocal_cup_cup_intersections']==0 for s in reports),'method':'Cold GLB posed triangles. Report cup/skin and cup/cup triangle intersections only when rest triangle centers are >0.15 ML apart; attached local cup/skin overlap deliberately excluded','samples':reports,'limitations':['87 poses, not continuous collision proof','Local overlaps within 0.15 ML excluded; does not validate all cup attachment margins or suction dynamics']};(O/'contacts.validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'ok':d['ok'],'failed':[s for s in reports if s['nonlocal_cup_skin_intersections'] or s['nonlocal_cup_cup_intersections']]}))
