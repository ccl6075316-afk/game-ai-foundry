extends SceneTree
## Read-only actual importer inspection. No eye/surface helper, guard bypass,
## material override, LOD rewrite, acceptance receipt or model/config write.
## Godot --path <isolated game> --script <this absolute script> --
##   res://assets/models/fish/zander.glb <absolute output directory> <expected GLB SHA>
func digest(bytes:PackedByteArray)->String:
    var context:=HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(bytes);return context.finish().hex_encode()
func vec3_array(items)->Array:
    var result:Array=[]
    if items==null:return result
    for p in items:result.append([p.x,p.y,p.z])
    return result
func vec2_array(items)->Array:
    var result:Array=[]
    if items==null:return result
    for p in items:result.append([p.x,p.y])
    return result
func bytes_file(path:String,bytes:PackedByteArray):
    var f:=FileAccess.open(path,FileAccess.WRITE);assert(f!=null);f.store_buffer(bytes);f.close()
func json_file(path:String,data):
    var f:=FileAccess.open(path,FileAccess.WRITE);assert(f!=null);f.store_string(JSON.stringify(data,"  "));f.close()
func _initialize():call_deferred("run")
func run():
    var args:=OS.get_cmdline_user_args();assert(args.size()==3,"model resource, output directory, exact expected model SHA required")
    var model_path:String=args[0];var out:String=args[1];var expected:String=args[2]
    assert(model_path.begins_with("res://") and model_path.ends_with(".glb"));assert(out.is_absolute_path());assert(expected.length()==64 and FileAccess.get_sha256(model_path)==expected,"Wrong or stale GLB")
    assert(not FileAccess.file_exists(out+"/imported-meshes.validation.json"),"Refuse overwrite frozen inspection")
    assert(DirAccess.make_dir_recursive_absolute(out)==OK)
    var model=load(model_path).instantiate();root.add_child(model)
    var meshes:Array=[]
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        assert(mesh.mesh!=null);var name:String=str(mesh.name);var snapshots:Array=[];var arrays_context:=HashingContext.new();var lod_context:=HashingContext.new();arrays_context.start(HashingContext.HASH_SHA256);lod_context.start(HashingContext.HASH_SHA256);var counts:Array=[]
        for surface in mesh.mesh.get_surface_count():
            var arrays:Array=mesh.mesh.surface_get_arrays(surface);var data:Dictionary=RenderingServer.mesh_get_surface(mesh.mesh.get_rid(),surface)
            var encoded:PackedByteArray=var_to_bytes(arrays);var lod_encoded:PackedByteArray=var_to_bytes(data.get("lods",[]));arrays_context.update(encoded);lod_context.update(lod_encoded)
            var base:String=name+"-surface-"+str(surface);bytes_file(out+"/"+base+"-arrays.var.bin",encoded);bytes_file(out+"/"+base+"-lods.var.bin",lod_encoded)
            var indices:PackedInt32Array=arrays[Mesh.ARRAY_INDEX];var vertices:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];assert(indices.size()%3==0)
            var lods:Array=[];var raw_lods:Array=data.get("lods",[]);counts.append(raw_lods.size())
            if not raw_lods.is_empty():
                var raw_index:PackedByteArray=data.index_data;var index_count:int=int(data.index_count);assert(index_count>0)
                var width:int=int(raw_index.size()/float(index_count));assert(width in [2,4] and raw_index.size()==index_count*width)
                for level in raw_lods.size():
                    var entry:Dictionary=raw_lods[level];var bytes:PackedByteArray=entry.index_data;assert(bytes.size()%width==0);var decoded:Array=[]
                    for at in range(0,bytes.size(),width):decoded.append(bytes.decode_u16(at) if width==2 else bytes.decode_u32(at))
                    assert(decoded.size()%3==0)
                    for index in decoded:assert(index>=0 and index<vertices.size())
                    lods.append({"level":level,"edge_length":entry.edge_length,"index_width":width,"indices":decoded,"index_data_sha256":digest(bytes),"triangles":decoded.size()/3})
            var geometry:Dictionary={"mesh":name,"surface":surface,"rest_xyz":vec3_array(vertices),"rest_normals":vec3_array(arrays[Mesh.ARRAY_NORMAL]),"source_uv":vec2_array(arrays[Mesh.ARRAY_TEX_UV]),"indices":Array(indices),"bones_flat":Array(arrays[Mesh.ARRAY_BONES]) if arrays[Mesh.ARRAY_BONES]!=null else [],"weights_flat":Array(arrays[Mesh.ARRAY_WEIGHTS]) if arrays[Mesh.ARRAY_WEIGHTS]!=null else [],"lods":lods}
            if arrays[Mesh.ARRAY_TEX_UV2]!=null:geometry["source_uv2"]=vec2_array(arrays[Mesh.ARRAY_TEX_UV2])
            json_file(out+"/"+base+".json",geometry)
            snapshots.append({"surface":surface,"primitive":mesh.mesh.surface_get_primitive_type(surface),"vertices":vertices.size(),"base_triangles":indices.size()/3,"lod_count":lods.size(),"arrays_sha256":digest(encoded),"lods_sha256":digest(lod_encoded),"geometry_file":base+".json"})
            assert(var_to_bytes(mesh.mesh.surface_get_arrays(surface))==encoded and var_to_bytes(RenderingServer.mesh_get_surface(mesh.mesh.get_rid(),surface).get("lods",[]))==lod_encoded,"Exporter changed imported geometry")
        meshes.append({"mesh":name,"skeleton_path":str(mesh.skeleton),"surface_count":mesh.mesh.get_surface_count(),"lod_counts":counts,"all_surface_arrays_sha256":arrays_context.finish().hex_encode(),"all_lods_sha256":lod_context.finish().hex_encode(),"surfaces":snapshots})
    assert(not meshes.is_empty());assert(FileAccess.get_sha256(model_path)==expected)
    json_file(out+"/imported-meshes.validation.json",{"ok":true,"status":"read_only_import_inspection_complete","accepted":false,"model_resource":model_path,"model_sha256":expected,"exporter_sha256":FileAccess.get_sha256(get_script().resource_path),"engine":Engine.get_version_info(),"import_settings_sha256":FileAccess.get_sha256(model_path+".import") if FileAccess.file_exists(model_path+".import") else "missing","meshes":meshes,"limits":["Actual current imported arrays and every LOD exported; no level was pruned or repaired.","Inspection only, no geometry/eye/material/fin/body acceptance and no runtime guard authorization.","Import settings and Godot version must be frozen beside this report; actual runtime assembly remains a separate strict contract."]})
    model.queue_free();print("108_IMPORTED_MESH_INSPECTION_COMPLETE");quit()
