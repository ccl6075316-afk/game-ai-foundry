"""Native painted eyes on closed lenses conforming to the actual head surface.

The extreme silhouette point is not an eyeball center or a flat support plane.
Every lens sample is attached to this body's finite lateral surface.
"""
import bpy,bmesh,hashlib,json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();c=json.loads(cp.read_text());src=Path(c['baseline']);cfg=json.loads(Path(c['reference']).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(c['source']['path'])==c['source']['sha256'];bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];body.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co.copy()for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True);head_z=float(np.mean([(r['top_z_m']+r['bottom_z_m'])/2 for r in cfg['body_stations']if r['t']<.15]));im=bpy.data.images.load(c['source']['path'],check_existing=False);im.pack();SW,SH=im.size;mat=bpy.data.materials.new('Own original side eye pixels, closed conforming lens');mat.use_nodes=True;mat.use_backface_culling=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=1;bs.inputs['Specular IOR Level'].default_value=0;tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Closest';mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);records=[]
for name in c.get('replace_existing_eyes',[]):
    assert name in ['Eye_left','Eye_right'] and name in bpy.data.objects
    bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
spokes=int(c.get('spokes',12));assert spokes>=8
for side in [-1,1]:
    row=min(cfg['head_transverse_stations'],key=lambda r:abs(r['y_m']-side*.96*cfg['head_span_m']/2));cx=(row['front_x_m']+row['rear_x_m'])/2;cz=head_z;rx,rz,_=c['eye_radii_m'];params=[(0.,0.)]+[(r,i*math.tau/spokes)for r in [.55,1.]for i in range(spokes)];vertices=[];supports=[]
    for layer in [1,-1]:
        for r,a in params:
            x=cx+rx*r*math.cos(a);z=cz+rz*r*math.sin(a);h,n,fi,d=tree.ray_cast(Vector((x,side,z)),Vector((0,-side,0)),2);assert h is not None and n.y*side>0,(side,x,z,'missing actual eye support');offset=(.0001+.00045*(1-r*r))if layer>0 else-.00015;vertices.append((x,h.y+side*offset,z));supports.append(dict(layer=layer,source_radius=r,body_hit=list(h),offset_m=offset,body_normal_dot_outward=n.y*side))
    faces=[];N=len(params)
    for layer in [0,1]:
        off=layer*N
        for i in range(spokes):
            j=(i+1)%spokes;parts=[(off,off+1+i,off+1+j),(off+1+i,off+1+spokes+i,off+1+spokes+j,off+1+j)]
            faces.extend(parts if layer==0 else[tuple(p[::-1])for p in parts])
    for i in range(spokes):j=(i+1)%spokes;faces.append((1+spokes+i,1+spokes+j,N+1+spokes+j,N+1+spokes+i))
    name='Eye_left'if side<0 else'Eye_right';me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(mat);bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    assert all(len(e.link_faces)==2 for e in bm.edges);bm.to_mesh(me);bm.free();uv=me.uv_layers.new(name='NativeEye')
    for f in me.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;sx=c['source_center_px'][0]+(p.x-cx)/rx*c['source_radius_px'];sy=c['source_center_px'][1]-(p.z-cz)/rz*c['source_radius_px'];uv.data[li].uv=((sx+.5)/SW,1-(sy+.5)/SH)
    me.calc_loop_triangles();records.append(dict(name=name,center_xz_m=[cx,cz],radii_xz_m=[rx,rz],triangles=len(me.loop_triangles),actual_surface_supports=supports,native_source_center_px=c['source_center_px'],native_source_radius_px=c['source_radius_px'],style_scale_only_not_biological_eye_measurement=True))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];tri=sum(len(o.data.loop_triangles)for o in meshes);assert tri<=4000,tri;bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);auth=json.loads((src/'fin-authoring.json').read_text());auth['whole_triangles']=tri;auth['eyes']=records;(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');r=dict(ok=True,kind='native_eyes_on_actual_finite_head_surface',model_sha256=sha(out/'fish.glb'),source_sha256=c['source']['sha256'],whole_triangles=tri,eyes=records,body_and_fins_unchanged=True,formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=True,triangles=tri,eyes=[dict(name=x['name'],triangles=x['triangles'])for x in records])))
