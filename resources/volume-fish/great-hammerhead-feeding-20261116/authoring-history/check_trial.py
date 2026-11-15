"""Finite preview checks; native loop phases plus isolated feeding controls, not 490 runtime acceptance."""
exec((__import__('pathlib').Path(__file__).parent/'check_local.py').read_text().split('rows=[]')[0])
from mathutils import Vector
plan_path=R/'projects/fishing-2d/plans/reviews/hammer-pair-release-20261106/great/fin.plan.json'
plan=json.loads(plan_path.read_text())['items'][0]
roots={}
for name,spec in plan['fins'].items():
 obj=bpy.data.objects[name];pts=np.array([list(v.co)for v in obj.data.vertices]);ids=[]
 for p in spec['rest_points_gltf']:
  d=np.linalg.norm(pts-np.array([p[0],-p[2],p[1]]),axis=1);i=int(np.argmin(d));assert d[i]<1e-5,(name,d[i]);ids.append(i)
 roots[name]=sorted(set(ids))
import os
from motion_math import cfg,config_file
times=sorted(set([round(float(t),5)for t in np.linspace(0,4.2,43)]+[k[0]for k in cfg['bend_keys']]+[1.2,1.38,1.56,1.66,1.8,2.18,2.85]))
rows=[];scale=4000/plan['length_native']
toothfaces=[tuple(p.vertices)for p in ob.data.polygons if p.material_index==4]
for frame in [1,9,17,25]:
 for t in times:
  scene.frame_set(frame);apply(rig,curve(t));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);m=ev.to_mesh();v=np.array([list(x.co)for x in m.vertices]);ev.to_mesh_clear();tree=BVHTree.FromPolygons(v.tolist(),faces,all_triangles=True);bad=[]
  for i,j in sorted(set(tree.overlap(tree))):
   if i<j and intersect(v[list(faces[i])],v[list(faces[j])]):bad.append([i,j])
  finrows={}
  for name,ids in roots.items():
   ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();signed=[]
   for i in ids:
    p=m.vertices[i].co;loc,normal,idx,dist=tree.find_nearest(p);signed.append(float(dist)*(1 if (p-loc).dot(normal)>=0 else -1)*scale)
   ev.to_mesh_clear();finrows[name]={'min_mm':min(signed),'max_mm':max(signed),'points':len(ids),'ok':min(signed)>=-6 and max(signed)<=1}
  rows.append({'native_frame':frame,'time':t,'body_contacts':len(bad),'first_body_pairs':bad[:3],'roots':finrows})
 print('phase',frame,'samples',len(times),'max contacts',max(x['body_contacts']for x in rows),flush=True)
report={'scope':'32 feeding times x 4 native animation phases; complete frozen basal points on actual skinned body. Not Godot four-action/transition or 490 gate. Tooth opposing-wall contacts not covered. Fin free membrane not covered.','model_sha256':hashlib.sha256((W/'candidate/fish.glb').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((W/'candidate/fish.blend').read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'root_ids':roots,'samples':rows,'max_body_contacts':max(x['body_contacts']for x in rows),'all_sampled_roots_ok':all(f['ok']for x in rows for f in x['roots'].values()),'body_closed_manifold':True}
report['ok']=report['max_body_contacts']==0 and report['all_sampled_roots_ok']
report['scope']='Current feeding times including all bend extrema x 4 native phases; complete frozen293 root vertices. Not full490/free membrane/continuous contact proof.'
report['motion_sha256']=hashlib.sha256((W/config_file).read_bytes()).hexdigest();report['controller_reference_sha256']=hashlib.sha256((W/'motion_math.py').read_bytes()).hexdigest()
(W/('trial-small.validation.json' if config_file=='motion-small.json' else 'trial.validation.json')).write_text(json.dumps(report,indent=2));print('TRIAL',report['ok'],report['max_body_contacts'],report['all_sampled_roots_ok'])
bpy.ops.export_scene.gltf(filepath=str(W/'candidate/cold-export.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
