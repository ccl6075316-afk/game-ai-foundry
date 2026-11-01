"""Weld sub-micron Boolean duplicates in an ordinary editable fish source.

No decimation or silhouette adaptation. Full cap selections are remapped by
their complete original coordinates. UV loops and skin groups remain in source.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists() and '/experiments/' in out.as_posix();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));auth=json.loads((src/'fin-authoring.json').read_text());records=[]
for ob in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    before=[v.co.copy() for v in ob.data.vertices];bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-7);bmesh.ops.dissolve_degenerate(bm,dist=2e-7,edges=list(bm.edges));bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),(ob.name,'Sliver repair opened source');bm.to_mesh(ob.data);bm.free();ob.data.calc_loop_triangles()
    records.append(dict(mesh=ob.name,before_vertices=len(before),after_vertices=len(ob.data.vertices),triangles=len(ob.data.loop_triangles)))
    if ob.name=='Reference_head_body':auth['body_triangles']=len(ob.data.loop_triangles)
    for fin in auth['fins']:
        if fin['name']!=ob.name:continue
        points=[Vector(p) for p in fin['root_points_native']];ids=[v.index for v in ob.data.vertices if min((v.co-p).length for p in points)<3e-7];assert ids;fin.update(root_ids=ids,root_points_native=[list(ob.data.vertices[i].co) for i in ids],vertices=len(ob.data.vertices),triangles=len(ob.data.loop_triangles))
auth['whole_triangles']=sum(r['triangles'] for r in records);assert auth['whole_triangles']<=4000
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in ['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');r=dict(ok=True,kind='ordinary_source_submicron_duplicate_weld',maximum_weld_radius_m=2e-7,records=records,whole_triangles=auth['whole_triangles'],source_sha256=hashlib.sha256((src/'fish.blend').read_bytes()).hexdigest(),model_sha256=hashlib.sha256((out/'fish.glb').read_bytes()).hexdigest(),formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
