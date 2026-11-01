"""Share actual tail-cap support vertices with the finite body cage.

Rest silhouette and per-corner native UV/normal values are interpolated on the
same old triangles. This fixes the LBS mismatch between a new Boolean cap point
and an unsupported long body triangle; no runtime geometry patch is used.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();c=json.loads(cp.read_text());assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();src=Path(c['baseline']);assert sha(src/'fish.glb')==c['baseline_sha256'];bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));ob=bpy.data.objects['Reference_head_body'];old=ob.data;old.calc_loop_triangles();assert len(old.polygons)==len(old.loop_triangles)
vertices=[v.co.copy()for v in old.vertices];rows=[]
for f in old.polygons:
    rows.append(dict(ids=list(f.vertices),uv=[old.uv_layers.active.data[i].uv.copy()for i in f.loop_indices],normal=[old.corner_normals[i].vector.copy()for i in f.loop_indices],material=f.material_index,smooth=f.use_smooth))
bm=bmesh.new();bm.from_mesh(old);bm.faces.ensure_lookup_table();tag=bm.faces.layers.int.new('source_face_for_uv');
for fi,face in enumerate(bm.faces):face[tag]=fi
inserted=[]
for raw in c['support_points_blender']:
    point=Vector(raw)
    # Float/Boolean duplicates of existing support points are not new cage
    # features. This2um identity criterion is far below the frozen0.5mm seam;
    # it does not discard any root selection or alter contact tolerances.
    if min((v.co-point).length for v in bm.verts)<2e-6:continue
    bm.faces.ensure_lookup_table();bm.faces.index_update();tree=BVHTree.FromBMesh(bm);hit,normal,fi,distance=tree.find_nearest(point);assert distance<2e-6,('Cap support point outside finite body',raw,distance)
    nearest=None
    for edge in bm.edges:
        a,b=[v.co for v in edge.verts];direction=b-a;fraction=(hit-a).dot(direction)/direction.length_squared;projection=a+direction*max(0,min(1,fraction));value=(projection-hit).length
        if nearest is None or value<nearest[0]:nearest=(value,edge,fraction,projection)
    if nearest[0]<2e-6 and 0<nearest[2]<1:
        edge,new=bmesh.utils.edge_split(nearest[1],nearest[1].verts[0],nearest[2]);new.co=nearest[3];method='shared edge split'
        bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    else:
        face=bm.faces[fi];original=face[tag];result=bmesh.ops.poke(bm,faces=[face],offset=0);assert len(result['verts'])==1;new=result['verts'][0];new.co=hit;method='finite triangle split'
        for face in result['faces']:face[tag]=original
    inserted.append(dict(point=raw,actual_body_support=list(new.co),snap_distance_m=(new.co-point).length,method=method))
# Improve the planar support triangulation inside each ORIGINAL UV triangle.
# Sequential pokes can leave long slivers which fold under nonlinear LBS even
# though the support points themselves are correct. Never cross a source chart.
for origin in range(len(rows)):
    group=[face for face in bm.faces if face[tag]==origin]
    if len(group)>1:
        edges=[edge for edge in bm.edges if len(edge.link_faces)==2 and all(face[tag]==origin for face in edge.link_faces)]
        bmesh.ops.beautify_fill(bm,faces=group,edges=edges)
assert all(e.is_manifold for e in bm.edges),'Body support refinement opened the body';bm.faces.ensure_lookup_table();origins=[face[tag]for face in bm.faces]
mesh=bpy.data.meshes.new('Reference shared tail-cap support cage');bm.to_mesh(mesh);bm.free();mesh.update()
for material in old.materials:mesh.materials.append(material)
uv=mesh.uv_layers.new(name=old.uv_layers.active.name);normals=[];normal_repairs=[]
for f,origin in zip(mesh.polygons,origins):
    row=rows[origin];f.material_index=row['material'];f.use_smooth=row['smooth'];a,b,z=[vertices[i]for i in row['ids']]
    face_normals=[]
    for loop in f.loop_indices:
        point=mesh.vertices[mesh.loops[loop].vertex_index].co;beta=barycentric_transform(point,a,b,z,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));uv.data[loop].uv=sum((row['uv'][k]*beta[k]for k in range(3)),Vector((0,0)));face_normals.append(sum((row['normal'][k]*beta[k]for k in range(3)),Vector((0,0,0))).normalized())
    if sum(face_normals,Vector()).dot(f.normal)<=0:
        normal_repairs.append(dict(face=f.index,source_face=origin,old_mean_dot=sum(face_normals,Vector()).dot(f.normal)/3));face_normals=[f.normal.copy()for _ in face_normals]
    normals.extend(face_normals)
mesh.normals_split_custom_set(normals);ob.data=mesh
bm=bmesh.new();bm.from_mesh(mesh);assert all(e.is_manifold for e in bm.edges),'Body support refinement opened the body';bm.free()
auth=json.loads((src/'fin-authoring.json').read_text());auth['body_triangles']=len(mesh.polygons);auth['whole_triangles']+=len(mesh.polygons)-len(old.polygons);assert auth['whole_triangles']<=4000,auth['whole_triangles']
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type=='MESH':o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');report=dict(ok=True,model_sha256=sha(out/'fish.glb'),config_sha256=sha(cp),inserted=inserted,body_triangles=len(mesh.polygons),whole_triangles=auth['whole_triangles'],static_silhouette_unchanged=True,inherited_invalid_corner_normal_repairs=normal_repairs,method='Finite body triangle subdivision at actual tail-cap support points. Shared BMesh edge/interior splits, barycentric UV and split normals; inherited negative mean-normal triangles receive their actual geometric normals. No contour displacement, no root narrowing or tolerance change.',formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(ok=True,supports=len(inserted),triangles=auth['whole_triangles'],normal_repairs=len(normal_repairs),maximum_snap_m=max((r['snap_distance_m']for r in inserted),default=0))))
