import bpy,json,sys,math,hashlib
import numpy as np
from pathlib import Path
from collections import Counter
from mathutils.bvhtree import BVHTree
W=Path(__file__).resolve().parent;R=W.parents[1];sys.path.insert(0,str(R/'resources/scripts/volume-fish/blacktip-20261105'));sys.path.insert(0,str(W))
from finite_edge_kernel import intersect
from motion_math import curve,apply
bpy.ops.wm.open_mainfile(filepath=str(W/'candidate/fish.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');ob=bpy.data.objects['Reference_head_body'];scene=bpy.context.scene
faces=[tuple(p.vertices)for p in ob.data.polygons if p.material_index!=4];edge=Counter(tuple(sorted((a,b)))for f in faces for a,b in zip(f,f[1:]+f[:1]));assert set(edge.values())=={2}
rows=[]
for t in [0,1.2,1.38,1.66,2.18,2.85,4.2]:
 scene.frame_set(1);state=curve(t);apply(rig,state);bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.array([list(x.co)for x in m.vertices]);ev.to_mesh_clear();tree=BVHTree.FromPolygons(v.tolist(),faces,all_triangles=True);bad=[]
 for i,j in sorted(set(tree.overlap(tree))):
  if i>=j:continue
  hit=intersect(v[list(faces[i])],v[list(faces[j])])
  if hit:bad.append({'faces':[i,j],'materials':[ob.data.polygons[i].material_index,ob.data.polygons[j].material_index],'points':[v[list(faces[k])].tolist()for k in [i,j]],'kind':hit['kind']})
 rows.append({'t':t,'contacts':len(bad),'examples':bad[:12]})
report={'model_sha256':hashlib.sha256((W/'candidate/fish.glb').read_bytes()).hexdigest(),'samples':rows,'closed_body_edges_two_faces':True,'max_contacts':max(r['contacts']for r in rows)}
(W/'local.validation.json').write_text(json.dumps(report,indent=2));print([(r['t'],r['contacts'])for r in rows])
