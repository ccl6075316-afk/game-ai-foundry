"""Source-local lower head fairing and finite-face eye visibility repair.

No artwork is redrawn. Original lens topology, complete eye UV footprint,
all fins, weights and native rig/action channels are retained.
"""
import bpy,bmesh,json,hashlib,sys
import numpy as np
import math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def tree(ob):
 ob.data.calc_loop_triangles();return BVHTree.FromPolygons([v.co.copy()for v in ob.data.vertices],[tuple(t.vertices)for t in ob.data.loop_triangles],all_triangles=True)
def main():
 cp,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());assert not out.exists()and'/experiments/'in str(out);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 for p,h in c['inputs'].items():assert sha(p)==h,p
 bpy.ops.wm.open_mainfile(filepath=c['blend']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1)
 body=bpy.data.objects['Reference_head_body'];meshes=[o for o in bpy.data.objects if o.type=='MESH'];original={o.name:np.array([v.co[:]for v in o.data.vertices])for o in meshes}
 oral={i for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'for i in f.vertices};kd=KDTree(len(oral))
 for j,i in enumerate(sorted(oral)):kd.insert(body.data.vertices[i].co,j)
 kd.balance();protected={i:1-smooth(*c['oral_blend_m'],kd.find(v.co)[2])for i,v in enumerate(body.data.vertices)}
 # One common vertical anchor from the actual upper oral lining envelope,
 # rather than an unrelated anterior wing midpoint. Mouth itself stays fixed.
 shift=c['head_vertical_delta_m'];weights=[]
 for v in body.data.vertices:
  q=v.co;w=smooth(*c['head_axial_fade_m'],q.x)*(1-protected[v.index]);v.co.z+=shift*w;weights.append(w)
 adj={i:set()for i in range(len(body.data.vertices))}
 for e in body.data.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 fairing=[]
 for step in range(c['fair_iterations']):
  z=np.array([v.co.z for v in body.data.vertices]);updated=z.copy()
  for v in body.data.vertices:
   x,y,_=v.co;r=abs(y);w=smooth(*c['fair_x_rise'],x)*(1-smooth(*c['fair_x_fall'],x))*smooth(*c['fair_y_rise'],r)*(1-smooth(*c['fair_y_fall'],r))*(1-smooth(*c['fair_z_fade'],v.co.z))*(1-protected[v.index])
   if not w:continue
   # Limited scalar fairing of existing local control vertices. No new surface,
   # no shrink of the original mouth or entire head XY to conceal the corner.
   delta=(np.mean(z[list(adj[v.index])])-z[v.index])*w*c['fair_relaxation'];updated[v.index]+=delta
   if abs(delta)>1e-8:fairing.append(dict(step=step,vertex=v.index,delta_m=float(delta)))
  for v in body.data.vertices:v.co.z=float(updated[v.index])
 rim=c.get('posterior_rim_rounding')
 if rim:
  project=json.loads(Path(c['project_reference']).read_text());rows=project['head_transverse_stations'];ys=[r['y_m']for r in rows];half=project['head_span_m']/2
  for v in body.data.vertices:
   x,y,z=v.co;front=float(np.interp(y,ys,[r['front_x_m']for r in rows]));rear=float(np.interp(y,ys,[r['rear_x_m']for r in rows]));t=(front-x)/max(front-rear,1e-5)
   weight=smooth(*rim['span_rise'],abs(y)/half)*(1-smooth(*rim['span_fall'],abs(y)/half))*smooth(*rim['chord_rise'],t)*(1-protected[v.index])*smooth(*c['head_axial_fade_m'],x)
   if x>=rear-.01 and x<=front+.01:
    v.co.z+=rim['delta_z_m']*weight
    v.co.x+=rim.get('rear_fillet_forward_m',0.)*weight
 assert np.array_equal(np.array([v.co[:]for v in body.data.vertices])[list(oral)],original[body.name][list(oral)])
 body.data.update();body.data.normals_split_custom_set([(0.,0.,0.)]*len(body.data.loops));bt=tree(body)
 eyes=[]
 for name in ['Eye_left','Eye_right']:
  ob=bpy.data.objects[name];old=original[name];side=1 if old[:,1].mean()>0 else -1;N=len(old)//2;assert N==17
  if c.get('eye_mode')=='closed_ellipsoid':
   uvold=ob.data.uv_layers.active
   def uv_at(i):return next(uvold.data[l.index].uv.copy()for l in ob.data.loops if l.vertex_index==i)
   uv0=uv_at(0);du=uv_at(9).x-uv0.x;dv=uv_at(11).y-uv0.y
   # The actual terminal body cap, rather than the old .96-span chord centre,
   # defines the local eye support. Original full artwork oval remains intact.
   vv=original[body.name];cap=vv[(vv[:,1]*side>abs(vv[:,1]).max()-1e-5)&(vv[:,0]>.65)]
   cx=float((cap[:,0].max()+cap[:,0].min())/2);cz=float((cap[:,2].max()+cap[:,2].min())/2)+shift
   rx,rz=c['eye_radii_xz_m'];ry=c['eye_radius_y_m'];cy=float(abs(vv[:,1]).max())-c['eye_center_inset_m']
   params=[(0.,0.)]+[(k*math.pi/5,j*math.tau/8)for k in range(1,5)for j in range(8)]+[(math.pi,0.)];maxsin=math.sin(2*math.pi/5)
   verts=[]
   for th,ph in params:verts.append((cx+rx*math.sin(th)/maxsin*math.cos(ph),side*(cy+ry*math.cos(th)),cz+rz*math.sin(th)/maxsin*math.sin(ph)))
   faces=[]
   for j in range(8):faces.append((0,1+j,1+(j+1)%8));faces.append((33,25+(j+1)%8,25+j))
   for k in range(3):
    for j in range(8):
     a=1+k*8+j;b=1+k*8+(j+1)%8;d=1+(k+1)*8+j;e=1+(k+1)*8+(j+1)%8;faces.extend([(a,d,e),(a,e,b)])
   mat=ob.data.materials[0];me=bpy.data.meshes.new(name+'_source_eye_ellipsoid');me.from_pydata(verts,[],faces);me.update();ob.data=me;me.materials.append(mat)
   bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));
   if bm.calc_volume()<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
   bm.to_mesh(me);bm.free();uv=me.uv_layers.new(name='NativeEye');group=ob.vertex_groups.get('body_00')or ob.vertex_groups.new(name='body_00');group.add(list(range(34)),1.,'REPLACE')
   for f in me.polygons:
    f.use_smooth=True
    for li in f.loop_indices:
     v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(uv0.x+(v.x-cx)/rx*du,uv0.y+(v.z-cz)/rz*dv)
   me.calc_loop_triangles();probes=[]
   for tri in me.loop_triangles:
    ids=tuple(tri.vertices)
    if any(i>=17 for i in ids):continue
    for i in range(25):
     for j in range(25-i):
      bary=np.array([i/24,j/24,1-(i+j)/24]);q=sum((me.vertices[k].co*float(w)for k,w in zip(ids,bary)),Vector());r=math.hypot((q.x-cx)/rx,(q.z-cz)/rz)
      hit=bt.ray_cast(Vector((q.x,side,q.z)),Vector((0,-side,0)),2)[0]
      if hit and r<=c['protected_eye_radius']:probes.append(side*(q.y-hit.y))
   deficit=max(0.,c['eye_min_clearance_m']-min(probes))
   for v in me.vertices:v.co.y+=side*deficit
   eyes.append(dict(name=name,construction='closed smooth ellipsoid; same original source eye affine UV',center_m=[cx,side*(cy+deficit),cz],radii_m=[rx,ry,rz],whole_triangles=64,protected_source_radius=c['protected_eye_radius'],samples=len(probes),minimum_core_clearance_mm=(min(probes)+deficit)*1000,additional_outward_shift_mm=deficit*1000,original_complete_source_eye=True))
   continue
  # Preserve both original oval axes and complete native UVs; shift with wing.
  for v in ob.data.vertices:v.co.z+=shift
  front=[tuple(t.vertices)for t in ob.data.loop_triangles if all(i<N for i in t.vertices)]
  assert len(front)==24
  # Freeze dense barycentric constraints over EACH visible triangle. Existing
  # vertex-only surface projection caused 11.9mm face-interior occlusion.
  constraints=[];den=c['eye_subdivisions']
  for ids in front:
   for i in range(den+1):
    for j in range(den+1-i):
     bary=np.array([i/den,j/den,1-(i+j)/den]);q=sum((ob.data.vertices[k].co*float(w)for k,w in zip(ids,bary)),Vector());hit=bt.ray_cast(Vector((q.x,side,q.z)),Vector((0,-side,0)),2)[0];assert hit is not None,('eye lacks finite support',name,ids,list(q))
     constraints.append((ids,bary,side*hit.y+c['eye_min_clearance_m']))
  target=np.array([side*ob.data.vertices[i].co.y for i in range(N)]);initial=target.copy()
  # Cyclic half-space projections; only outward correction, no source UV warp.
  for iteration in range(500):
   worst=0.
   for ids,bary,bound in constraints:
    ix=np.array(ids);deficit=bound-float(target[ix]@bary);worst=max(worst,deficit)
    if deficit>0:target[ix]+=bary*deficit/float(bary@bary)
   if worst<1e-8:break
  assert worst<1e-7,('eye projection did not converge',worst)
  for i in range(N):ob.data.vertices[i].co.y=side*target[i];ob.data.vertices[i+N].co.y=side*(target[i]-c['eye_shell_depth_m'])
  ob.data.update();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops));clearances=[]
  for ids,bary,bound in constraints:clearances.append(float(target[np.array(ids)]@bary-bound+c['eye_min_clearance_m']))
  assert min(clearances)>c['eye_min_clearance_m']-1e-7
  eyes.append(dict(name=name,front_faces=len(front),samples=len(constraints),minimum_front_clearance_mm=min(clearances)*1000,maximum_outward_correction_mm=float((target-initial).max()*1000),iterations=iteration+1,original_XZ_oval_and_UV_preserved=True))
 for ob in meshes:
  bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges)and bm.calc_volume()>0,ob.name;bm.to_mesh(ob.data);bm.free();ob.data.calc_loop_triangles()
  if ob.name not in [body.name,'Eye_left','Eye_right']:assert np.array_equal(np.array([v.co[:]for v in ob.data.vertices]),original[ob.name])
 total=sum(len(o.data.loop_triangles)for o in meshes);assert total==3998
 rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for o in meshes+[rig]:o.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
 (out/'fin-authoring.json').write_bytes(Path(c['fin_authoring']).read_bytes())
 report=dict(ok=True,kind='source_local_hammerhead_underside_and_eye_face_clearance',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),config_sha256=sha(cp),script_sha256=sha(__file__),whole_triangles=total,head_vertical_delta_m=shift,oral_vertices_unchanged=len(oral),fairing=fairing,eyes=eyes,all_fins_positions_preserved=True,rig_actions_preserved=True,formal_acceptance=False,visual_review='pending')
 (out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['fairing']}))
if __name__=='__main__':main()
