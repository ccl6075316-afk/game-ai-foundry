"""Blender-only cleanup of sub-precision remesher slivers, not a shape edit."""
import bmesh

def clean(obj, distance):
    assert 0 < distance <= 2e-7
    bm=bmesh.new();bm.from_mesh(obj.data)
    before=(len(bm.verts),len(bm.faces))
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=distance)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=distance*.01)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return {'before_vertices_faces':before,'after_vertices_faces':[len(obj.data.vertices),len(obj.data.polygons)],'weld_native':distance}
