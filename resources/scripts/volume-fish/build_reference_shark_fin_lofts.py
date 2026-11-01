"""All eight species fins, continuous section foils and actual body basal caps.

Static shape trial only. No claim of skinning/motion or full fish acceptance.
"""
import bpy,bmesh,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();c=json.loads(cp.read_text());src=Path(c['baseline']);cfg=json.loads(Path(c['reference']).read_text());bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];body.data.calc_loop_triangles();bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);axis=cfg['reference_body_axis_m'];scale=c['metres_per_source_pixel'];records=[];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def material(name,rgba):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=rgba;p.inputs['Roughness'].default_value=1;p.inputs['Specular IOR Level'].default_value=0;return m
dark=material('Fin gray diagnostic; native fin chart pending',(.36,.40,.42,1));light=material('Paired fin underside diagnostic; native chart pending',(.83,.80,.74,1))
def build(name,v,f):
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
def close(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bad=[dict(faces=len(e.link_faces),points=[tuple(v.co)for v in e.verts])for e in bm.edges if len(e.link_faces)!=2]
    if bad:(out/(ob.name+'-topology-failure.json')).write_text(json.dumps(bad,indent=2))
    assert not bad,(ob.name,len(bad));bm.to_mesh(ob.data);bm.free();ob.data.calc_loop_triangles()
def surface(x,z=None,side=1,ventral=False,y=0):
    if z is None:origin=Vector((x,y,-1 if ventral else 1));direction=Vector((0,0,1 if ventral else-1))
    else:origin=Vector((x,side,z));direction=Vector((0,-side,0))
    h,n,fi,d=tree.ray_cast(origin,direction,2);assert h is not None,(x,z,side,ventral,y);return h,n
for row in c['rows']:
    assert sha(row['source_path'])==row['source_sha256'];root=np.array(row['root_curve_px']);root=root[np.argsort(root[:,0])];leading=np.array(row['root_endpoints_px'][0]);onset=row['onset_t'];paired=row['paired'];sections=np.array(row['sections_px']);nc=sections.shape[1];ns=sections.shape[0]
    for side in ([-1,1]if paired else[1]):
        name=row['name']+('_left'if side<0 else'_right')if paired else row['name'];verts=[];qs=[];flags=[];ss=[];faces=[]
        if row['name']=='Caudal':
            rotation=math.radians(row['plane_rotation_degrees']);co=math.cos(rotation);si=math.sin(rotation);source_lo=float(sections[:,:,1].min());source_hi=float(sections[:,:,1].max());root_y=float(leading[1]);chords=np.array(row['chord_levels'])
            for layer in [-1,1]:
                for section in sections:
                    y=float(section[0,1]);s=(root_y-y)/max(root_y-source_lo,1)if y<root_y else(y-root_y)/max(source_hi-root_y,1);envelope=row['root_full_thickness_m']/2*max(0,1-s)**.7
                    for j,q in enumerate(section):
                        dx=-(q[0]-leading[0])*scale;dz=-(q[1]-leading[1])*scale;x=axis*(.5-onset)+co*dx-si*dz;z=row['anchor_z_m']+si*dx+co*dz;shape=max(0,math.sin(math.pi*chords[j]))**.65;half=c['edge_full_thickness_m']/2+envelope*shape;verts.append((x,layer*half,z));qs.append(q.tolist());ss.append(float(s));flags.append(False)
        else:
            for layer in [-1,1]:
                for k,section in enumerate(sections):
                    s=row['span_levels'][k]
                    for j,q in enumerate(section):
                        x=axis*(.5-onset)-(q[0]-leading[0])*scale;base_y=float(np.interp(q[0],root[:,0],root[:,1]));span=(q[1]-base_y)*scale;chord=row['chord_levels'][j];half=c['edge_full_thickness_m']/2+(row['root_full_thickness_m']-c['edge_full_thickness_m'])/2*(1-s)**1.1*max(0,math.sin(math.pi*chord))**.65
                        if paired:
                            t=(axis/2-x)/axis;rows=cfg['body_stations'];mid=float(np.interp(t,[r['t']for r in rows],[(r['top_z_m']+r['bottom_z_m'])/2 for r in rows]));z=mid+row['root_z_offset_m'];h,_=surface(x,z,side);angle=math.radians(row['roll_degrees']);normal=Vector((0,side*math.sin(angle),math.cos(angle)));p=Vector((x,h.y+side*span*math.cos(angle),z-span*math.sin(angle)))+normal*layer*half
                            if k==0:p,n=surface(p.x,p.z,side);p.y-=side*.003
                        else:
                            h,_=surface(x,ventral=row['ventral'],y=layer*half);normal=Vector((0,1,0));p=Vector((x,layer*half,h.z-span))+normal*0
                            if k==0:p,n=surface(p.x,ventral=row['ventral'],y=p.y);p.z+=.003 if row['ventral']else-.003
                        verts.append(tuple(p));qs.append(q.tolist());ss.append(float(s));flags.append(k==0)
        offset=ns*nc
        normal=Vector((0,side*math.sin(math.radians(row['roll_degrees'])),math.cos(math.radians(row['roll_degrees']))))if paired else Vector((0,1,0))
        minimum_pair_separation=min((Vector(verts[i+offset])-Vector(verts[i])).dot(normal)for i in range(offset));assert minimum_pair_separation>1e-8,(name,'Crossed foil layers before body subtraction',minimum_pair_separation)
        for layer in range(2):
            off=layer*offset
            for k in range(ns-1):
                for j in range(nc-1):
                    ids=(off+k*nc+j,off+k*nc+j+1,off+(k+1)*nc+j+1,off+(k+1)*nc+j);faces.append(ids if layer else ids[::-1])
        boundary=list(range(nc))+[k*nc+nc-1 for k in range(1,ns)]+list(range((ns-1)*nc+nc-2,(ns-1)*nc-1,-1))+[k*nc for k in range(ns-2,0,-1)]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((a,b,b+offset,a+offset))
        ob=build(name,verts,faces);ob.data.materials.append(dark);ob.data.materials.append(light);close(ob)
        for f in ob.data.polygons:f.material_index=1 if paired and all(i<offset for i in f.vertices)else 0;f.use_smooth=True
        for key,values in [('source_mask_x_px',[q[0]for q in qs]),('source_mask_y_px',[q[1]for q in qs]),('source_span_t',ss),('source_layer_sign',[-1.]*offset+[1.]*offset)]:
            at=ob.data.attributes.new(key,'FLOAT','POINT')
            for a,value in zip(at.data,values):a.value=value
        roots={i for i,flag in enumerate(flags)if flag}
        if row.get('exact_complete_body_intersection',True):
            original_vertices=[v.co.copy()for v in ob.data.vertices];original_triangles=[tuple(t.vertices)for t in ob.data.loop_triangles];original_tree=BVHTree.FromPolygons(original_vertices,original_triangles,all_triangles=True)
            if name=='FirstDorsal':
                bm=bmesh.new();bm.from_mesh(ob.data);volume=bm.calc_volume(signed=True);bm.free();(out/'first-dorsal-before-cut.json').write_text(json.dumps(dict(volume=volume,vertices=[tuple(v.co)for v in ob.data.vertices],triangles=[tuple(t.vertices)for t in ob.data.loop_triangles]),indent=2)+'\n')
            # Intersect with every actual finite body triangle, not a body box.
            # Distinct material IDs preserve the exact full contact cap domain.
            cm=bpy.data.meshes.new('Temporary finite body cutter');cm.from_pydata(bv,[],bt);markers=[]
            for i,f in enumerate(cm.polygons):m=bpy.data.materials.new('Temporary basal triangle '+str(i));cm.materials.append(m);f.material_index=i;markers.append(m)
            cutter=bpy.data.objects.new('Temporary finite body cutter',cm);bpy.context.collection.objects.link(cutter);bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Whole actual fin/body intersection','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;mod.material_mode='TRANSFER';bpy.ops.object.modifier_apply(modifier=mod.name);roots={i for f in ob.data.polygons if f.material_index>=2 for i in f.vertices};assert roots,(name,'No actual body cap',len(ob.data.vertices),len(ob.data.polygons),len(ob.data.materials),sorted(set(f.material_index for f in ob.data.polygons)));bpy.data.objects.remove(cutter,do_unlink=True);bpy.data.meshes.remove(cm)
            for f in ob.data.polygons:
                if f.material_index>=2:f.material_index=0
                f.use_smooth=True
            while len(ob.data.materials)>2:ob.data.materials.pop(index=2)
            for m in markers:
                if m.users==0:bpy.data.materials.remove(m)
            close(ob)
            # Boolean-created edge vertices cannot inherit default-zero source
            # attributes: pull them back to the actual pre-cut finite triangle.
            maximum_free_source_distance=0
            for vertex in ob.data.vertices:
                h,nn,fi,d=original_tree.find_nearest(vertex.co);ids=original_triangles[fi];beta=barycentric_transform(h,*[original_vertices[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));beta=np.maximum(np.array(beta),0);beta/=beta.sum()
                for key,values in [('source_mask_x_px',[qs[i][0]for i in ids]),('source_mask_y_px',[qs[i][1]for i in ids]),('source_span_t',[ss[i]for i in ids]),('source_layer_sign',[-1. if i<offset else 1. for i in ids])]:ob.data.attributes[key].data[vertex.index].value=float(beta@values)
                if vertex.index not in roots:maximum_free_source_distance=max(maximum_free_source_distance,d)
            assert maximum_free_source_distance<5e-6,(name,'Free source surface lost',maximum_free_source_distance)
        # Original free-face source attributes survive the exact root cut.
        # New basal-only attributes are not used as painted-source coordinates.
        ob.data.calc_loop_triangles();records.append(dict(name=name,paired=paired,vertices=len(ob.data.vertices),triangles=len(ob.data.loop_triangles),root_ids=sorted(roots),root_points_native=[tuple(ob.data.vertices[i].co)for i in sorted(roots)],source_sha256=row['source_sha256'],source_root_curve_px=row['root_curve_px'],construction='Continuous span/chord closed foil. All layers and sealing counted; caudal is one connected outline/interval surface, actual whole-body finite intersection cap.',normal_thickness_basis='Engineering representation; not biological measurement',native_fin_material='pending',rig='pending'))
assert len(records)==8 and len({r['name']for r in records})==8;total=len(body.data.loop_triangles)+sum(r['triangles']for r in records);print(json.dumps(dict(pre_export_triangles=total,fin_triangles={r['name']:r['triangles']for r in records})),flush=True);assert total<=4000,total
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type=='MESH':o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
(out/'fin-authoring.json').write_text(json.dumps(dict(body_triangles=len(body.data.loop_triangles),whole_triangles=total,fins=records),indent=2)+'\n');r=dict(ok=True,kind='static_reference_shark_all_fin_lofts',model_sha256=sha(out/'fish.glb'),input_sha256=sha(cp),triangles=total,body_triangles=len(body.data.loop_triangles),inventory=[r['name']for r in records],complete_static_mesh_inventory=True,source_contour_and_all_fin_contact_validation='pending',native_fin_material='pending',rig='pending',motions='pending',formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
