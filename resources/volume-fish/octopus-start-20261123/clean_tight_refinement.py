import bpy,bmesh,json
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'motion-r3/rest';bpy.ops.wm.open_mainfile(filepath=str(O/'octopus-gray.blend'));ob=bpy.data.objects['Octopus_gray_skin'];bm=bmesh.new();bm.from_mesh(ob.data);before=len(bm.faces)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));print('CLEAN',before,len(bm.faces),'MIN',min(f.calc_area()for f in bm.faces),'manifold',all(e.is_manifold for e in bm.edges));assert all(e.is_manifold for e in bm.edges);assert min(f.calc_area()for f in bm.faces)>1e-12
bm.to_mesh(ob.data);bm.free();ob.data.update();p=O/'gray-build.validation.json';d=json.loads(p.read_text());d['parts'][ob.name]=sum(len(f.vertices)-2 for f in ob.data.polygons);d['refinement_cleanup']={'faces_before':before,'faces_after':len(ob.data.polygons)};p.write_text(json.dumps(d,indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.collections['GRAY_REVIEW'].objects:o.select_set(True)
bpy.context.view_layer.objects.active=ob;bpy.ops.wm.save_as_mainfile(filepath=str(O/'octopus-gray.blend'),compress=True);bpy.ops.export_scene.gltf(filepath=str(O/'octopus-gray.glb'),export_format='GLB',use_selection=True,export_animations=False)
