extends SceneTree
## Transport persistent actual body/lip geometry while preserving original source charts.
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(value)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var p=JSON.parse_string(FileAccess.get_file_as_string(args[0]));DirAccess.make_dir_recursive_absolute(p.output);var records=[]
    for kind in ["body","lips"]:
        var source=load(p[kind].resource)as ArrayMesh;var original=JSON.parse_string(FileAccess.get_file_as_string(p[kind].original));var data=JSON.parse_string(FileAccess.get_file_as_string(p[kind].geometry));assert(data.parts.size()==source.get_surface_count());var next=ArrayMesh.new()
        for si in source.get_surface_count():
            var arrays=source.surface_get_arrays(si);var old_positions:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var part=data.parts[si];assert(old_positions.size()==part.vertices.size());var vv=PackedVector3Array();var nn=PackedVector3Array()
            for i in old_positions.size():
                var old=original.parts[si].vertices[i];assert(old_positions[i].distance_to(Vector3(old[0],old[1],old[2]))<.0000002,"Actual resource order/geometry differs from frozen JSON")
                var v=part.vertices[i];var n=part.normals[i];vv.append(Vector3(v[0],v[1],v[2]));nn.append(Vector3(n[0],n[1],n[2]))
            arrays[Mesh.ARRAY_VERTEX]=vv;arrays[Mesh.ARRAY_NORMAL]=nn
            if arrays[Mesh.ARRAY_TANGENT]!=null and arrays[Mesh.ARRAY_TANGENT].size()==vv.size()*4:
                var tangents:PackedFloat32Array=arrays[Mesh.ARRAY_TANGENT].duplicate()
                for i in vv.size():
                    var t=Vector3(tangents[i*4],tangents[i*4+1],tangents[i*4+2]);t=(t-nn[i]*nn[i].dot(t)).normalized()
                    tangents[i*4]=t.x;tangents[i*4+1]=t.y;tangents[i*4+2]=t.z
                arrays[Mesh.ARRAY_TANGENT]=tangents
            next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays,[],source.get("_surfaces")[si].get("lods",{}));next.surface_set_material(si,PORTABLE.freeze(source.surface_get_material(si)))
            var cold=next.surface_get_arrays(si)
            for ai in arrays.size():
                if ai in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TANGENT]:continue
                assert(digest(arrays[ai])==digest(cold[ai]),"Unrelated UV/skin/topology field changed: "+str(ai))
        var dest=p.output+"/"+kind+".res";assert(ResourceSaver.save(next,dest,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
        records.append({"kind":kind,"resource_sha256":FileAccess.get_sha256(dest),"surfaces":next.get_surface_count()})
    var f=FileAccess.open(p.output+"/resources.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"records":records,"plan_sha256":FileAccess.get_sha256(args[0]),"builder_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Actual body/lip geometry transported, UV/skin/topology preserved. Original material reference lookup tables and lip colours retained deliberately; source reference positions are not the new physical support geometry. New finite eye/lip contacts, body and all-fin gates required."}));f.close();quit()
