import bpy,json,sys,math,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
root=Path('E:/game-ai-foundry');W=Path(__file__).resolve().parent;out=W;P=W.parent/'r2'
sys.path.insert(0,str(root/'resources/scripts/volume-fish/blacktip-20261105'))
from finite_edge_kernel import intersect
cfg=json.loads((W/'motion.json').read_text(encoding='utf-8-sig'));keys=cfg['keyframes']
sys.path.insert(0,str(W))
from motion_math import curve,apply
bpy.ops.wm.open_mainfile(filepath=str(P/'fish.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');ob=bpy.data.objects['Closed_body'];scene=bpy.context.scene
lo=rig.pose.bones['jaw_lower'];up=rig.pose.bones['jaw_upper'];lo.rotation_mode='QUATERNION'
local_shift=up.bone.matrix_local.to_3x3().inverted()@Vector(cfg['upper_translation_native'])
author=json.loads((P/'authoring.validation.json').read_text());loidx=author['lower_rim'][7];upidx=author['upper_rim'][7]
head=rig.pose.bones['feeding_head'];head.rotation_mode='QUATERNION';floor=rig.pose.bones['oral_floor'];floor_shift=floor.bone.matrix_local.to_3x3().inverted()@Vector(cfg['floor_translation_native'])
faces=[tuple(p.vertices)for p in ob.data.polygons if p.material_index!=3];edges=Counter(tuple(sorted((a,b)))for f in faces for a,b in zip(f,f[1:]+f[:1]));assert set(edges.values())=={2}
tooth_faces=[tuple(p.vertices)for p in ob.data.polygons if p.material_index==3]
tooth_upper=[any(g.group==ob.vertex_groups['jaw_upper'].index and g.weight>.9 for g in ob.data.vertices[f[0]].groups)for f in tooth_faces]
first_oral=next(p.index for p in ob.data.polygons if p.material_index==1);roof_begin=first_oral+42
start,end=rig.animation_data.action.frame_range;rows=[]
# Full cycle + crossed extremes, using actual skin at several native swim phases.
states=[{'t':float(t),**curve(t)}for t in np.linspace(0,cfg['duration'],73)]
states +=[{**curve(bt),'t':bt,'gape':g,'protrusion':p,'head':h,'shake':sh}for g in [0,.45,1]for p in [0,1]for h in [0,1]for sh in [-1,0,1]for bt in [2.02,2.25,2.52]]
for phase in [0,.23,.51,.77]:
 for state in states:
  at=start+(end-start)*phase;scene.frame_set(math.floor(at),subframe=at-math.floor(at));apply(rig,state);bpy.context.view_layer.update()
  ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.array([list(x.co)for x in m.vertices]);ev.to_mesh_clear();tree=BVHTree.FromPolygons(v.tolist(),faces,all_triangles=True);contacts=[]
  for i,j in sorted(set(tree.overlap(tree))):
   if i>=j:continue
   hit=intersect(v[list(faces[i])],v[list(faces[j])])
   if hit:contacts.append({'faces':[i,j],'kind':hit['kind']})
  tooth_bad=[];ttree=BVHTree.FromPolygons(v.tolist(),tooth_faces,all_triangles=True)
  for ti,bi in ttree.overlap(tree):
   material=ob.data.polygons[bi].material_index
   opposite=(bi<roof_begin if tooth_upper[ti] else bi>=roof_begin)
   if material!=1 or opposite:
    hit=intersect(v[list(tooth_faces[ti])],v[list(faces[bi])])
    if hit:tooth_bad.append({'tooth_face':ti,'body_face':bi,'material':material,'kind':hit['kind']})
  rows.append({'tooth_wrong_wall_contacts':tooth_bad,'swim_phase':phase,**state,'self_contacts':contacts,'central_rim_gap':float(np.linalg.norm(v[loidx]-v[upidx]))})
report={'model_sha256':hashlib.sha256((P/'fish.glb').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((P/'fish.blend').read_bytes()).hexdigest(),'motion_sha256':hashlib.sha256((W/'motion.json').read_bytes()).hexdigest(),'samples':rows,'max_body_self_contacts':max(len(r['self_contacts'])for r in rows),'max_tooth_wrong_wall_contacts':max(len(r['tooth_wrong_wall_contacts'])for r in rows),'scope':'4 native swim phases x (73 cycle samples +36 crossed gape/protrusion/head/shake controls). Actual body and oral wall excluding separate embedded teeth; not full fin/Godot/continuous time proof.'}
(out/'motion.validation.json').write_text(json.dumps(report,indent=2));print('FEEDING_CHECK',len(rows),report['max_body_self_contacts'],'teeth wrong wall',report['max_tooth_wrong_wall_contacts'],flush=True)

