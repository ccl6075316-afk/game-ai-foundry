"""Sparse shared cephalofoil/neck surface, finite integrated oral cut.

Experimental author, not a complete fish. All static work is stored in blend.
"""
import bpy,bmesh,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve()
assert not out.exists() and '/experiments/' in out.as_posix();out.mkdir()
c=json.loads(cp.read_text(encoding='utf8'));cfg=c['source_input']
assert hashlib.sha256(Path(c['reference']).read_bytes()).hexdigest()==c['reference_sha256']
for item in cfg['inputs'].values():assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
bpy.ops.wm.read_factory_settings(use_empty=True)

def recalc(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bad=[tuple(tuple(v.co) for v in e.verts) for e in bm.edges if len(e.link_faces)!=2]
    if bad:(out/'topology-failure.validation.json').write_text(json.dumps(dict(ok=False,bad=bad),indent=2)+'\n')
    assert not bad,(ob.name,len(bad));bm.to_mesh(ob.data);bm.free();ob.data.calc_loop_triangles()

def obj(name,v,f):
    m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.update();o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);recalc(o);return o

def mat(name,rgba):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=rgba;p.inputs['Roughness'].default_value=1;p.inputs['Specular IOR Level'].default_value=0;return m

skin=mat('Diagnostic gray; native skin not yet applied',(.52,.57,.6,1));oral=mat('Actual finite oral lining',(.08,.085,.09,1))
im=bpy.data.images.new('Diagnostic constant',1,1);im.pixels=[.38,.42,.45,1];im.pack();tex=skin.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Closest';skin.node_tree.links.new(tex.outputs['Color'],next(n for n in skin.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])
xy=np.array(c['points_xy']);nb=c['boundary_count'];boundary=list(range(nb))
cv,ce,cf,_,_,_=delaunay_2d_cdt([Vector(p) for p in xy],[],[boundary],2,1e-9,False)
v=[];faces=[];maps=[{},{}];dedup={};max_cdt_error=0
for i,p in enumerate(cv):
    d=np.linalg.norm(xy-np.array(p),axis=1);source=int(d.argmin());max_cdt_error=max(max_cdt_error,float(d[source]));assert d[source]<5e-8,(tuple(p),float(d[source])) # Vector/CDT uses float32.
    for layer in [0,1]:
        co=(float(p.x),float(p.y),c['layers_z'][source][layer]);key=tuple(round(x,10) for x in co)
        if key not in dedup:dedup[key]=len(v);v.append(co)
        maps[layer][i]=dedup[key]
from collections import Counter
edge_counts=Counter(tuple(sorted((a,b))) for f in cf for a,b in zip(f,f[1:]+f[:1]))
bad_diagonals={e for e,count in edge_counts.items() if count==2 and all(maps[0][i]==maps[1][i] for i in e)}
def interior(p,z):
    hr=cfg['head_transverse_stations'];hy=[r['y_m'] for r in hr];front=np.interp(p[1],hy,[r['front_x_m'] for r in hr]);rear=np.interp(p[1],hy,[r['rear_x_m'] for r in hr]);q=np.clip((front-p[0])/(front-rear),0,1);half=cfg['head_span_m']*cfg['cross_section_and_head_thickness']['head_projected_full_thickness_over_span']/2;h=half*math.sin(math.pi*q)**c['head_thickness_power'];assert h>1e-6
    ids=[]
    for sign in [1,-1]:ids.append(len(v));v.append((float(p[0]),float(p[1]),z+sign*h))
    return ids
split={}
for a,b in bad_diagonals:
    p=(np.array(cv[a])+np.array(cv[b]))/2;z=(v[maps[0][a]][2]+v[maps[0][b]][2])/2;split[(a,b)]=interior(p,z)
for f in cf:
    assert len(f)==3
    if any(tuple(sorted((a,b))) in split for a,b in zip(f,f[1:]+f[:1])) or all(maps[0][i]==maps[1][i] for i in f):
        # Shared silhouette chords otherwise pinch both layers onto one edge.
        # Resolve that exact topology with finite interior supports on both sides.
        p=np.array([tuple(cv[i]) for i in f]).mean(0);center=interior(p,sum(v[maps[0][i]][2] for i in f)/3)
        for layer in [0,1]:
            order=[]
            for a,b in zip(f,f[1:]+f[:1]):
                order.append(maps[layer][a]);e=tuple(sorted((a,b)))
                if e in split:order.append(split[e][layer])
            if layer:order=order[::-1]
            for a,b in zip(order,order[1:]+order[:1]):faces.append((a,b,center[layer]))
    else:
        for layer in [0,1]:faces.append(tuple(maps[layer][i] for i in (f if layer==0 else f[::-1])))
join_x=c['join_x_m']
for(a,b),count in edge_counts.items():
    if count!=1 or(abs(cv[a].x-join_x)<5e-8 and abs(cv[b].x-join_x)<5e-8):continue
    ids=list(dict.fromkeys([maps[0][a],maps[0][b],maps[1][b],maps[1][a]]))
    if len(ids)>=3:faces.append(tuple(ids))
rows=cfg['body_stations'];join_row=min(rows,key=lambda r:abs(r['t']-c['join_t']));mid=(join_row['top_z_m']+join_row['bottom_z_m'])/2;h=(join_row['top_z_m']-join_row['bottom_z_m'])/2;w=join_row['full_width_m']/2;n=c['join_radial_segments'];previous=[]
for i in range(n):
    co=np.array((join_x,w*math.sin(i*math.tau/n),mid+h*math.cos(i*math.tau/n)))
    d=np.linalg.norm(np.array(v)-co,axis=1);j=int(d.argmin());assert d[j]<1e-7,(co,d[j]);previous.append(j)
rear_rows=[row for row in rows if row['t']>=c['join_t']-1e-9];keep={0,len(rear_rows)-1}
for t in [.3333333333,.5,.65,.70,.8]:keep.add(min(range(len(rear_rows)),key=lambda i:abs(rear_rows[i]['t']-t)))
body_tolerance=cfg['reference_body_axis_m']/cfg['body_mask_axis_pixels']['ventral']
def retain_body(a,b):
    if b<=a+1:return
    errors=[]
    for i in range(a+1,b):
        t=(rear_rows[i]['t']-rear_rows[a]['t'])/(rear_rows[b]['t']-rear_rows[a]['t']);error=max(abs(rear_rows[i][key]-(rear_rows[a][key]*(1-t)+rear_rows[b][key]*t))for key in['top_z_m','bottom_z_m','full_width_m']);errors.append((error,i))
    error,i=max(errors)
    if error>body_tolerance:keep.add(i);retain_body(a,i);retain_body(i,b)
anchors=sorted(keep)
for a,b in zip(anchors,anchors[1:]):retain_body(a,b)
for index in sorted(keep):
    row=rear_rows[index]
    if row['t']<=c['join_t']+1e-9:continue
    mid=(row['top_z_m']+row['bottom_z_m'])/2;h=max((row['top_z_m']-row['bottom_z_m'])/2,.00005);w=max(row['full_width_m']/2,.00005);ring=[]
    for i in range(n):ring.append(len(v));v.append((row['x_m'],w*math.sin(i*math.tau/n),mid+h*math.cos(i*math.tau/n)))
    for i in range(n):j=(i+1)%n;faces.append((previous[i],previous[j],ring[j],ring[i]))
    previous=ring
faces.append(tuple(previous[::-1]));body=obj('Reference_head_body',v,faces);body.data.materials.append(skin);body.data.materials.append(oral)
body.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],[tuple(t.vertices) for t in body.data.loop_triangles],all_triangles=True)
axis=cfg['reference_body_axis_m'];mouth=cfg['mouth_trial'];half=cfg['head_span_m']*mouth['full_width_over_head_span']/2;center=axis/2-cfg['head_axial_extent_m']*mouth['center_front_offset_over_head_depth'];corner=axis/2-cfg['head_axial_extent_m']*mouth['corner_offset_over_head_depth'];gap=mouth['maximum_gap_m'];outline=[]
for sign,phases in [(1,np.linspace(-math.pi/2,math.pi/2,17)),(-1,np.linspace(math.pi/2,-math.pi/2,17))]:
    for a in phases:
        y=half*math.sin(a);x=corner+(center-corner)*math.cos(a)+sign*gap*max(.02,math.cos(a))/2;outline.append((x,y))
hits=[]
for x,y in outline:
    hit,_,_,_=tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),2);assert hit is not None;hits.append(hit.z)
roof=max(hits)+mouth['recess_depth_m'];n=len(outline);vv=[(x,y,z) for z in [-.25,roof] for x,y in outline];ff=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
cutter=obj('Temporary actual oral subtraction',vv,ff);cutter.data.materials.append(skin);cutter.data.materials.append(oral)
for f in cutter.data.polygons:f.material_index=1
bpy.context.view_layer.objects.active=body;mod=body.modifiers.new('Integrated finite oral volume','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True);recalc(body)
for f in body.data.polygons:f.use_smooth=True
tree=BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],[tuple(t.vertices) for t in body.data.loop_triangles],all_triangles=True);probes=[]
for a in np.linspace(-1.2,1.2,9):
    x=corner+(center-corner)*math.cos(a);y=half*math.sin(a);hit,_,fi,_=tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),2);assert hit is not None
    mi=body.data.polygons[body.data.loop_triangles[fi].polygon_index].material_index;probes.append(dict(x=x,y=y,z=hit.z,roof_hit=mi==1 and abs(hit.z-roof)<1e-5))
assert all(p['roof_hit'] for p in probes)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
tri=len(body.data.loop_triangles);assert tri<=2800 # Partial only; leaves budget for fins/eyes.
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'fin-authoring.json').write_text(json.dumps(dict(fins=[],body_triangles=tri,whole_triangles=tri,scope='Static head/mouth cage only.'))+'\n')
r=dict(ok=True,kind='sparse_shared_shark_head_neck_author',model_sha256=sha(out/'fish.glb'),input_sha256=sha(cp),triangles=tri,watertight=True,actual_oral_roof_probes=probes,cdt_maximum_input_vertex_error_m=max_cdt_error,body_station_reduction=dict(original=len(rear_rows),retained=len(keep),maximum_omitted_envelope_error_bound_m=body_tolerance,preserved_join_and_axial_hinges=True),head_body_boolean_union=False,voxel_remesh=False,decimation=False,formal_acceptance=False,whole_fish=False,visual_review='pending')
(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
