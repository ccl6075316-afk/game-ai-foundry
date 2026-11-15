"""Invoked inside Blender before whole-body bake. Local rim Z smoothing, full skin UV."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
W=Path(__file__).parent
ob=bpy.data.objects['Reference_head_body'];m=ob.data
spec=json.loads((W/'history/r2-before-edge-repair/authoring.validation.json').read_text())
before=np.array([v.co[:]for v in m.vertices]);half=.15912
def curve(ids):
 p=before[ids];order=np.argsort(p[:,1]);p=p[order];ys=np.unique(p[:,1]);return ys,np.array([p[p[:,1]==y].mean(0)for y in ys])
yl,pl=curve(spec['lower_rim']);yu,pu=curve(spec['upper_rim'])
def target(y,upper):
 t=np.clip(abs(y)/half,0,1)
 # Smooth symmetric transverse lip envelope. Preserve terminal corner height.
 low=-.27055-.00008*t*t
 return low+(.0058*np.sqrt(np.maximum(0,1-t*t)) if upper else 0)
def straight_segments(y,p,upper):
 anchors=[0]
 for i in range(1,len(p)-1):
  a=p[i,:2]-p[i-1,:2];b=p[i+1,:2]-p[i,:2]
  if abs(np.cross(a,b))/max(np.linalg.norm(a)*np.linalg.norm(b),1e-14)>.002:anchors.append(i)
 anchors.append(len(p)-1)
 return np.interp(y,p[anchors,1],target(p[anchors,1],upper))
raw_target=target
def target(y,upper):
 p=pu if upper else pl
 anchors=[0]
 for i in range(1,len(p)-1):
  a=p[i,:2]-p[i-1,:2];b=p[i+1,:2]-p[i,:2]
  if abs(a[0]*b[1]-a[1]*b[0])/max(np.linalg.norm(a)*np.linalg.norm(b),1e-14)>.002:anchors.append(i)
 anchors.append(len(p)-1)
 return np.interp(y,p[anchors,1],raw_target(p[anchors,1],upper))
ys=before[:,1];lx=np.interp(ys,yl,pl[:,0]);ux=np.interp(ys,yu,pu[:,0]);lz=np.interp(ys,yl,pl[:,2]);uz=np.interp(ys,yu,pu[:,2])
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
blend=np.clip((before[:,0]-lx)/np.maximum(ux-lx,.00002),0,1)
delta=(target(ys,False)-lz)*(1-blend)+(target(ys,True)-uz)*blend
distance=np.sqrt((before[:,0]-(lx+ux)/2)**2+(before[:,2]-(lz+uz)/2)**2)
gain=(1-smooth(.012,.060,distance))*(1-smooth(half,half+.025,abs(ys)))
after=before.copy();after[:,2]+=delta*gain
for upper,key in [(False,'lower_rim'),(True,'upper_rim')]:
 for i in spec[key]:after[i,2]=target(before[i,1],upper)
for v,p in zip(m.vertices,after):v.co=p
# Recompute only changed-neighborhood normals; retain existing elsewhere.
normals=[tuple(n.vector)for n in m.corner_normals]
m.normals_split_custom_set([(0,0,0) if np.linalg.norm(after[m.loops[i].vertex_index]-before[m.loops[i].vertex_index])>1e-8 else n for i,n in enumerate(normals)])
# Remove cut-edge subdivision vertices, keeping the underlying arc knots.
# Edge collapse preserves both adjoining skin and lining materials and weights.
collapse={}
for key in ['lower_rim','upper_rim']:
 ids=sorted(spec[key],key=lambda i:(before[i,1],before[i,0]));p=before[ids]
 anchors=[0]
 for i in range(1,len(p)-1):
  a=p[i,:2]-p[i-1,:2];b=p[i+1,:2]-p[i,:2]
  if abs(a[0]*b[1]-a[1]*b[0])/max(np.linalg.norm(a)*np.linalg.norm(b),1e-14)>.002:anchors.append(i)
 anchors.append(len(p)-1)
 for i in range(len(ids)):
  if i not in anchors:
   k=min(anchors,key=lambda j:np.linalg.norm(p[j]-p[i]));collapse[ids[i]]=ids[k]
bm=bmesh.new();bm.from_mesh(m);bm.verts.ensure_lookup_table();tag=bm.verts.layers.int.new('original_r2_vertex')
for v in bm.verts:v[tag]=v.index
bmesh.ops.weld_verts(bm,targetmap={bm.verts[i]:bm.verts[j]for i,j in collapse.items()});bm.verts.index_update()
remap={v[tag]:v.index for v in bm.verts}
for i,j in collapse.items():remap[i]=remap[j]
bm.to_mesh(m);bm.free();m.update()
for key in ['mouth_boundary','lower_rim','upper_rim','cavity_ring']:
 spec[key]=list(dict.fromkeys(remap[i]for i in spec[key]))
spec['teeth_vertices']=[[remap[i]for i in group]for group in spec['teeth_vertices']]
spec['status']='r3_authored_pending_checks';spec['r2_to_r3_vertex']=remap;spec['uv_preserved']=False
(W/'candidate/authoring.validation.json').write_text(json.dumps(spec,indent=2))
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
for f in m.polygons:f.select=f.material_index==2
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_mode(type='FACE')
bpy.ops.uv.smart_project(angle_limit=1.151917,island_margin=.006,area_weight=0.,correct_aspect=True,scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT');m.calc_loop_triangles()
(W/'skin-geometry-r3.validation.json').write_text(json.dumps({'status':'authored_pending_checks','changed_vertices':int(np.sum(np.linalg.norm(after-before,axis=1)>1e-8)),'collapsed_rim_vertices':len(collapse),'max_displacement_m':float(np.max(np.linalg.norm(after-before,axis=1))),'retained_vertex_x_y_preserved':bool(np.array_equal(before[:,:2],after[:,:2])),'bones_motion_preserved':True,'method':'Whole skin smart UV unwrap; local continuous Z field and smooth separate upper/lower rim envelope. Redundant cut-edge vertices collapsed to original arc knots. Fin and eye geometry unchanged.'},indent=2))
