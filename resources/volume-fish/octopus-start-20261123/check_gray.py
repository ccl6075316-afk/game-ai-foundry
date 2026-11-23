"""Fresh Blender process: inspect saved source and cold-export selected grey mesh."""
import bpy, bmesh, hashlib, json, math
from pathlib import Path
root=Path(__file__).resolve().parent/'r2'
bpy.ops.wm.open_mainfile(filepath=str(root/'octopus-gray.blend'))
coll=bpy.data.collections['GRAY_REVIEW'];body=coll.objects['Octopus_gray_skin']
bm=bmesh.new();bm.from_mesh(body.data)
unseen=set(bm.verts);sizes=[]
while unseen:
    stack=[unseen.pop()];size=0
    while stack:
        v=stack.pop();size+=1
        for e in v.link_edges:
            w=e.other_vert(v)
            if w in unseen:unseen.remove(w);stack.append(w)
    sizes.append(size)
checks={'skin_connected_components':len(sizes),'skin_component_sizes':sizes,'skin_boundary_edges':sum(e.is_boundary for e in bm.edges),'skin_nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'skin_degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'finite_vertices':all(math.isfinite(x) for o in coll.objects for v in o.data.vertices for x in v.co)}
bm.free()
bpy.ops.object.select_all(action='DESELECT')
for o in coll.objects:o.select_set(True)
bpy.context.view_layer.objects.active=body
cold=root/'octopus-gray.cold.glb'
bpy.ops.export_scene.gltf(filepath=str(cold),export_format='GLB',use_selection=True,export_animations=False,export_yup=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks.update(source_sha256=sha(root/'octopus-gray.blend'),model_sha256=sha(root/'octopus-gray.glb'),cold_sha256=sha(cold))
checks['cold_export_byte_identical']=checks['model_sha256']==checks['cold_sha256']
checks['ok']=checks['skin_connected_components']==1 and checks['skin_nonmanifold_edges']==0 and checks['skin_degenerate_faces']==0 and checks['finite_vertices'] and checks['cold_export_byte_identical']
checks['scope']='Static grey skin topology and source cold export only; cups, oral opening, anatomy, rig and motions are not accepted.'
(root/'gray-source.validation.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
