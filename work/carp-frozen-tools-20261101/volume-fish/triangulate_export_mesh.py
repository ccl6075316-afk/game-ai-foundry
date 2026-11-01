"""Freeze Blender's existing export triangles without changing source vertices."""
import bpy
def triangulate_export_mesh(ob):
    old=ob.data;old.calc_loop_triangles()
    if all(len(f.vertices)==3 for f in old.polygons):return {'changed':False}
    assert not old.get('foundry_exact_normal_sha256'),'Do not silently retriangulate a guarded source'
    coords=[v.co[:]for v in old.vertices];weights=[[(g.group,g.weight)for g in v.groups]for v in old.vertices];names=[g.name for g in ob.vertex_groups];normals=[tuple(n.vector)for n in old.corner_normals]
    uv_layers={layer.name:[tuple(row.uv)for row in layer.data]for layer in old.uv_layers}
    triangles=[(tuple(t.vertices),tuple(t.loops),t.material_index,old.polygons[t.polygon_index].use_smooth)for t in old.loop_triangles]
    point_attrs={a.name:(a.data_type,[row.value for row in a.data])for a in old.attributes if a.domain=='POINT'and a.data_type in ('FLOAT','INT','BOOLEAN')and not a.name.startswith('.')}
    mesh=bpy.data.meshes.new(old.name+'_export_triangles');mesh.from_pydata(coords,[],[t[0]for t in triangles]);mesh.update()
    for mat in old.materials:mesh.materials.append(mat)
    for name,values in uv_layers.items():
        layer=mesh.uv_layers.new(name=name)
        for face,row in zip(mesh.polygons,triangles):
            for li,source in zip(face.loop_indices,row[1]):layer.data[li].uv=values[source]
    custom=[]
    for face,row in zip(mesh.polygons,triangles):
        face.material_index=row[2];face.use_smooth=row[3];custom.extend(normals[li]for li in row[1])
    mesh.normals_split_custom_set(custom)
    for key,value in old.items():mesh[key]=value
    for name,(kind,values)in point_attrs.items():
        attr=mesh.attributes.new(name,kind,'POINT')
        for i,value in enumerate(values):attr.data[i].value=value
    ob.data=mesh;ob.vertex_groups.clear()
    for name in names:ob.vertex_groups.new(name=name)
    for vi,groups in enumerate(weights):
        for group,weight in groups:ob.vertex_groups[group].add([vi],weight,'REPLACE')
    assert [v.co[:]for v in mesh.vertices]==coords
    return {'changed':True,'source_polygons':len(old.polygons),'export_triangles':len(mesh.polygons),'point_attributes_preserved':list(point_attrs),'vertices_weights_UVs_preserved':True}
