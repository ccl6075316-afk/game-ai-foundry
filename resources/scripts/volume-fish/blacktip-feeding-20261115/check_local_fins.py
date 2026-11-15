"""Local full-root signed-distance regression, not final 490 / four-action validation."""
import bpy,json,math,hashlib,sys
from pathlib import Path
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W));from motion_math import curve,apply
P=W.parent/'r2';root=Path('E:/game-ai-foundry')
domain=json.loads((root/'resources/volume-fish/top-body-repair-20261105/group-a/final/blacktip_reef_shark/source-domain.json').read_text())
cfg=json.loads((W/'motion.json').read_text(encoding='utf-8-sig'));rows=[]
bpy.ops.wm.open_mainfile(filepath=str(P/'fish.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');body=bpy.data.objects['Closed_body'];scene=bpy.context.scene
start,end=rig.animation_data.action.frame_range
def mesh(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=[x.co.copy()for x in m.vertices];fs=[tuple(p.vertices)for p in m.polygons if o!=body or p.material_index!=3];ev.to_mesh_clear();return v,fs
for phase in [0,.23,.51,.77]:
 for time in [0,1.2,1.38,1.56,1.8,2.02,2.10,2.25,2.40,2.52,2.71,2.83,3.15,3.3,3.8,4.2]:
  state=curve(time);gape=state['gape'];prot=state['protrusion'];head=state['head']
  at=start+(end-start)*phase;scene.frame_set(math.floor(at),subframe=at%1)
  apply(rig,state)
  bpy.context.view_layer.update();v,faces=mesh(body);tree=BVHTree.FromPolygons(v,faces,all_triangles=True)
  for fin in domain['fins']:
   verts,_=mesh(bpy.data.objects[fin['name']]);ds=[]
   for i in fin['root_ids']:
    p,n,_,d=tree.find_nearest(verts[i]);ds.append(float((verts[i]-p).dot(n))*domain['model_scale']*1000)
   rows.append({'fin':fin['name'],'phase':phase,'gape':gape,'protrusion':prot,'head':head,'time':time,'shake':state['shake'],'count':len(ds),'min_signed_mm':min(ds),'max_signed_mm':max(ds)})
summary={name:{'root_count':next(r['count']for r in rows if r['fin']==name),'min_signed_mm':min(r['min_signed_mm']for r in rows if r['fin']==name),'max_signed_mm':max(r['max_signed_mm']for r in rows if r['fin']==name)}for name in [f['name']for f in domain['fins']]}
report={'model_sha256':hashlib.sha256((P/'fish.glb').read_bytes()).hexdigest(),'domain_sha256':hashlib.sha256((root/'resources/volume-fish/top-body-repair-20261105/group-a/final/blacktip_reef_shark/source-domain.json').read_bytes()).hexdigest(),'scope':'All 453 frozen root vertices, 48 native Swim/feeding/headshake representative poses. Nearest finite skinned body signed normal distance. Does not replace complete 490, free fin, Godot action or continuous-time tests.','summary':summary,'samples':rows}
(W/'local-fin-roots.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(summary,indent=2))

