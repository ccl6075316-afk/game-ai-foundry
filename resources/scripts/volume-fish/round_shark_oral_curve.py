"""Round the actual subterminal mouth arc, independently of the nose tip."""
import bpy,bmesh,json,sys,hashlib,math
from pathlib import Path
import numpy as np
from mathutils import Vector
HERE=Path(__file__).parent;sys.path.insert(0,str(HERE));from rim_material_transport import ordered_boundary
args=sys.argv[sys.argv.index('--')+1:];cfg=json.loads(Path(args[0]).read_text(encoding='utf8'));src=Path(cfg['baseline']);out=Path(args[1]).resolve();assert not out.exists();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Closed_body'];mesh=body.data
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
before_other={o.name:hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons])).encode()).hexdigest()for o in bpy.data.objects if o.type=='MESH'and o!=body}
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.normal_update()
def rims():
 coords=np.array([v.co[:]for v in bm.verts]);result={}
 for name,sign in [('upper',-1),('lower',1)]:
  edges=[tuple(v.index for v in e.verts)for e in bm.edges if len(e.link_faces)==2 and any(f.material_index!=1 for f in e.link_faces)and any(f.material_index==1 and f.normal.x*sign>.1 for f in e.link_faces)]
  result[name]=ordered_boundary(coords,edges)
 return result
initial=rims();old_vertices=len(bm.verts)
def even_z_samples():
 pairs={}
 for pts,arc in initial.values():
  for p in pts:pairs.setdefault(round(abs(p[1]),7),[]).append(p[2])
 return np.array(sorted(pairs)),np.array([np.mean(pairs[y])for y in sorted(pairs)])
yz,zz=even_z_samples()
chosen=[e for e in bm.edges if len(e.link_faces)==2 and any(f.material_index==1 for f in e.link_faces)and any(f.material_index!=1 for f in e.link_faces)and min(abs(v.co.y)for v in e.verts)<1e-6 and max(abs(v.co.y)for v in e.verts)<.016]
assert len(chosen)==4,len(chosen)
bmesh.ops.subdivide_edges(bm,edges=chosen,cuts=cfg['central_edge_cuts'],use_grid_fill=False);bm.verts.index_update();bm.verts.ensure_lookup_table();bm.normal_update();old=rims();coords=np.array([v.co[:]for v in bm.verts]);oral={v.index for f in bm.faces if f.material_index==1 for v in f.verts};boundary=np.concatenate([r[0]for r in old.values()]);width=max(abs(boundary[:,1]));corner=float(min(r[0][:,0].min()for r in old.values()));cx=float(np.mean([r[0][abs(r[0][:,1]).argmin(),0]for r in old.values()]));radius=cfg['mouth_only_blend_radius_native'];moved=[]
def old_mid(y):
 return float(np.mean([np.interp(y,*[r[0][np.argsort(r[0][:,1]),i]for i in[1,0]])for r in old.values()]))
for v in bm.verts:
 p=v.co.copy();delta=corner+(cx-corner)*math.sqrt(max(0,1-(min(abs(p.y)/width,1))**2))-old_mid(p.y);delta_z=float(np.interp(p.y*p.y,yz*yz,zz)-np.interp(abs(p.y),yz,zz));d=float(np.linalg.norm(boundary-np.array(p),axis=1).min());t=min(d/radius,1);gain=1 if v.index in oral else 1-t*t*(3-2*t)
 if p.x<corner-radius or p.x>cx+radius:gain=0
 if gain>0 and max(abs(delta),abs(delta_z))>1e-10:v.co.x+=delta*gain;v.co.z+=delta_z*gain;moved.append(v.index)
# Preserve actual old finite faces; triangulate only polygons introduced by
# edge subdivision. No part of the original outer nose/eye width is narrowed.
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles();assert all(len(f.vertices)==3 for f in mesh.polygons)
after_other={o.name:hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons])).encode()).hexdigest()for o in bpy.data.objects if o.type=='MESH'and o!=body};assert before_other==after_other
total=0
for o in bpy.data.objects:
 if o.type=='MESH':o.data.calc_loop_triangles();total+=len(o.data.loop_triangles)
assert total<=4000,total
author=json.loads((src/'fin-authoring.json').read_text(encoding='utf8'));author['body_triangles']=len(mesh.loop_triangles);author['whole_triangles']=total;(out/'fin-authoring.json').write_text(json.dumps(author,indent=2)+'\n',encoding='utf8')
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
report=dict(ok=True,kind='actual_subterminal_mouth_arc_rounding',source_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),body_triangles=len(mesh.loop_triangles),whole_triangles=total,new_vertices=len(mesh.vertices)-old_vertices,moved_vertices=len(moved),mouth_corner_x=corner,mouth_centerline_front_x=cx,half_width=width,transverse_coordinates_unchanged=True,all_other_meshes_unchanged=True,oral_cavity_retained=True,construction='Ellipse across actual existing mouth corners and front midpoint; old X gap retained by shared lateral displacement. Add only central lip-edge samples; body/nose and eyes have zero transverse displacement. Not a new biological width measurement.',visual_review='pending')
(out/'mouth-rounding.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
