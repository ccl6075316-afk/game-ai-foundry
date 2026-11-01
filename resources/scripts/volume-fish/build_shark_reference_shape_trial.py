"""Sparse closed head/body with a finite rounded oral recess, static trial only.

Explicit same-species contours drive X/Y/Z envelopes. Cross-section interiors
and head thickness are declared engineering representations, never metrology.
No old mesh, runtime static builder or animal-wide acceptance is imported.
"""
import bpy,bmesh,json,sys,math,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:];config=Path(args[0]).resolve();out=Path(args[1]).resolve();assert '/experiments/'in out.as_posix()and not out.exists();out.mkdir();cfg=json.loads(config.read_text(encoding='utf8'))
for row in cfg['inputs'].values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
bpy.ops.wm.read_factory_settings(use_empty=True)
def recalc(ob):
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bad=[dict(faces=len(e.link_faces),points=[list(v.co)for v in e.verts])for e in bm.edges if len(e.link_faces)!=2]
 if bad:(out/'topology-failure.validation.json').write_text(json.dumps(dict(ok=False,object=ob.name,edges=bad),indent=2)+'\n')
 assert not bad,ob.name+' not closed';bm.to_mesh(ob.data);bm.free();ob.data.calc_loop_triangles()
def mesh(name,vertices,faces):
 m=bpy.data.meshes.new(name);m.from_pydata(vertices,[],faces);m.update();ob=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(ob);recalc(ob);return ob
def loft(name,rings):
 n=len(rings[0]);verts=[p for row in rings for p in row];faces=[]
 for r in range(len(rings)-1):
  for i in range(n):j=(i+1)%n;faces.append((r*n+i,r*n+j,(r+1)*n+j,(r+1)*n+i))
 faces.extend([tuple(range(n-1,-1,-1)),tuple((len(rings)-1)*n+i for i in range(n))]);return mesh(name,verts,faces)
def color(name,rgba):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=rgba;p.inputs['Roughness'].default_value=1;p.inputs['Specular IOR Level'].default_value=0;return m
skin=color('Diagnostic gray only; production native skin pending',(.52,.57,.60,1));oral=color('Diagnostic actual cavity surfaces',(.08,.085,.09,1))
# One embedded constant texel permits the ordinary cold-export image contract;
# it is a diagnostic material, not a replacement native skin chart.
im=bpy.data.images.new('Diagnostic constant',width=1,height=1);im.pixels=[.38,.42,.45,1];im.pack();tex=skin.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Closest';skin.node_tree.links.new(tex.outputs['Color'],next(n for n in skin.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])
rows=cfg['body_stations'];axis=cfg['reference_body_axis_m'];head_z=float(np.mean([(r['top_z_m']+r['bottom_z_m'])/2 for r in rows if r['t']<.15]));headhalf=cfg['head_span_m']*cfg['cross_section_and_head_thickness']['head_projected_full_thickness_over_span']/2
core=[]
for r in rows:
 if r['t']<.125:continue
 mid=(r['top_z_m']+r['bottom_z_m'])/2;h=max((r['top_z_m']-r['bottom_z_m'])/2,.00005);w=max(r['full_width_m']/2,.00005)
 core.append([(r['x_m'],w*math.sin(i*math.tau/12),mid+h*math.cos(i*math.tau/12))for i in range(12)])
body=loft('Reference_body_core',core);body.data.materials.append(skin);body.data.materials.append(oral)
qs=[0,.25,.5,.8,1];xy=[];zs=[];ts=[r['t']for r in rows]
raw_head=cfg['head_transverse_stations'];selected={0,len(raw_head)-1};tolerance=cfg['reference_body_axis_m']/cfg['body_mask_axis_pixels']['ventral']
def retain(a,b):
 if b<=a+1:return
 ya,yb=raw_head[a]['y_m'],raw_head[b]['y_m'];errors=[]
 for i in range(a+1,b):
  t=(raw_head[i]['y_m']-ya)/(yb-ya);errors.append((max(abs(raw_head[i][key]-(raw_head[a][key]*(1-t)+raw_head[b][key]*t))for key in['front_x_m','rear_x_m']),i))
 error,i=max(errors)
 if error>tolerance:selected.add(i);retain(a,i);retain(i,b)
retain(0,len(raw_head)-1);head_rows=[raw_head[i]for i in sorted(selected)]
for row in head_rows:
 for q in qs:
  x=row['front_x_m']+(row['rear_x_m']-row['front_x_m'])*q;y=row['y_m'];h=max(.00005,headhalf*math.sin(math.pi*q));top=head_z+h;bottom=head_z-h
  t=(axis/2-x)/axis;w=float(np.interp(t,ts,[r['full_width_m']/2 for r in rows]))
  if w>1e-8 and abs(y)<w:
   bt=float(np.interp(t,ts,[r['top_z_m']for r in rows]));bb=float(np.interp(t,ts,[r['bottom_z_m']for r in rows]));mid=(bt+bb)/2;bh=(bt-bb)/2*math.sqrt(max(0,1-(y/w)**2));u=max(0,min(1,(q-.4)/.4));gain=u*u*(3-2*u)
   top+=(max(top,mid+bh+.0001)-top)*gain;bottom+=(min(bottom,mid-bh-.0001)-bottom)*gain
  xy.append((x,y));zs.append((top,bottom))
n=len(xy);v=[(x,y,z[layer])for layer in[0,1]for(x,y),z in zip(xy,zs)];faces=[];ny=len(head_rows);nx=len(qs)
from collections import Counter
edge_count=Counter()
for r in range(ny-1):
 for j in range(nx-1):
  face=(r*nx+j,r*nx+j+1,(r+1)*nx+j+1,(r+1)*nx+j);faces.append(face);faces.append(tuple(n+i for i in face[::-1]))
  for a,b in zip(face,face[1:]+face[:1]):edge_count[tuple(sorted((a,b)))]+=1
for(a,b),count in edge_count.items():
 if count==1:faces.append((a,b,n+b,n+a))
head=mesh('Reference_cephalofoil',v,faces);head.data.materials.append(skin)
bpy.context.view_layer.objects.active=body;mod=body.modifiers.new('Posterior core attachment only','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=head;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(head,do_unlink=True);body.name='Reference_head_body';recalc(body)
body.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co.copy()for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True)
mouth=cfg['mouth_trial'];span=cfg['head_span_m']*mouth['full_width_over_head_span'];half=span/2;depth=mouth['recess_depth_m'];frontoffset=cfg['head_axial_extent_m']*mouth['center_front_offset_over_head_depth'];corneroffset=cfg['head_axial_extent_m']*mouth['corner_offset_over_head_depth'];center=axis/2-frontoffset;corner=axis/2-corneroffset;gap=mouth['maximum_gap_m'];outline=[]
for sign,phases in[(1,np.linspace(-math.pi/2,math.pi/2,17)),(-1,np.linspace(math.pi/2,-math.pi/2,17))]:
 for a in phases:
  y=half*math.sin(a);gain=max(.02,math.cos(a));x=corner+(center-corner)*math.cos(a)+sign*gap*gain/2;outline.append((x,y))
# Distinct endpoint seam samples retain a small finite commissure; no coincident
# zero-volume cutter endpoints or artificial pointed anterior central vertex.
n=len(outline);vertices=[];bottom_hits=[]
for x,y in outline:
 hit,_,_,_=tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),2);assert hit is not None,(x,y);bottom_hits.append(hit.z)
roof=max(bottom_hits)+depth
for z in[-.25,roof]:vertices.extend((x,y,z)for x,y in outline)
faces=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,n+(i+1)%n,n+i)for i in range(n)]
cutter=mesh('Temporary finite oral subtraction',vertices,faces);cutter.data.materials.append(skin);cutter.data.materials.append(oral)
for f in cutter.data.polygons:f.material_index=1
bpy.context.view_layer.objects.active=body;mod=body.modifiers.new('Actual underside rounded opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True);recalc(body)
for f in body.data.polygons:f.use_smooth=True
body.data.calc_loop_triangles();tris=len(body.data.loop_triangles);assert tris<=4000
tree=BVHTree.FromPolygons([v.co.copy()for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True);probes=[]
for a in np.linspace(-1.2,1.2,9):
 y=half*math.sin(a);x=corner+(center-corner)*math.cos(a);hit,_,fi,_=tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),2);assert hit is not None;mat=body.data.polygons[body.data.loop_triangles[fi].polygon_index].material_index;probes.append(dict(x=x,y=y,actual_hit_z=hit.z,roof_z=roof,material=mat,roof_hit=mat==1 and abs(hit.z-roof)<1e-5))
assert all(p['roof_hit']for p in probes),probes
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'fin-authoring.json').write_text(json.dumps(dict(fins=[],body_triangles=tris,whole_triangles=tris,scope='Head/body/oral geometry trial only; complete fin stage is pending.'))+'\n')
r=dict(ok=True,kind='static_shark_reference_head_body_oral_trial',input_sha256=sha(config),model_sha256=sha(out/'fish.glb'),triangles=tris,watertight=True,actual_oral_roof_probes=probes,head_span_m=cfg['head_span_m'],reference_body_axis_m=axis,head_outline_retention=dict(original_rows=len(raw_head),adopted_rows=len(head_rows),maximum_omitted_station_error_m=tolerance,criterion='One reference pixel; measured head span and contour endpoints retained.'),rigged=False,fin_stage='not_started_until_current_mouth_geometry_review',scope=cfg['scope'],formal_acceptance=False)
(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=True,triangles=tris,oral_roof_hits=sum(p['roof_hit']for p in probes),scope='Static reference-scale head/body/oral trial, not complete fish.')))
