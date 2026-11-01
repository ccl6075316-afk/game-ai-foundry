extends SceneTree
## Read the actual assembled fish, never the raw GLB triangle count alone.
var output=""
var species=""
func _initialize():
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
        if arg.begins_with("--species="):species=arg.trim_prefix("--species=")
    var allowed=ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()+"/"
    assert(output.is_absolute_path() and output.simplify_path().begins_with(allowed))
    assert(species in ["bluegill","zander","great_hammerhead","whale_shark"])
    DirAccess.make_dir_recursive_absolute(output);call_deferred("run")
func run():
    var holder=Node3D.new();root.add_child(holder)
    var factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var profile=factory.profiles[species]
    factory._add_fish(holder,species,float(profile.real_length_cm)/100.,profile)
    var entry=factory.fish[-1];entry.player.pause();entry.carrier.transform=Transform3D.IDENTITY
    var model=entry.model;var nodes=[];var id=0;var total=0;var files={}
    for node in model.find_children("*","MeshInstance3D",true,false):
        if not node.is_visible_in_tree():continue
        var parts=[];var count=0
        for si in node.mesh.get_surface_count():
            var a=node.mesh.surface_get_arrays(si);var row={"surface":si,"count":a[Mesh.ARRAY_VERTEX].size(),"triangles":a[Mesh.ARRAY_INDEX].size()/3,"attributes":{}}
            count+=row.triangles
            for slot in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_COLOR,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_TEX_UV2,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:
                if a[slot]==null or a[slot].is_empty():continue
                var name="source-"+str(id)+"-"+str(si)+"-"+str(slot)+".bin"
                var f=FileAccess.open(output.path_join(name),FileAccess.WRITE);f.store_buffer(a[slot].to_byte_array());f.close()
                row.attributes[str(slot)]=name;files[name]=FileAccess.get_sha256(output.path_join(name))
            var mat=node.get_active_material(si)
            row["material_type"]=mat.get_class()
            if mat is ShaderMaterial:row["shader_sha256"]=mat.shader.code.sha256_text()
            parts.append(row)
        total+=count
        # Coordinates are native mesh coordinates. Determinant converts volume
        # to standardized game metres, including all actual parent transforms.
        nodes.append({"name":String(node.name),"path":str(model.get_path_to(node)),"surfaces":parts,"triangles":count,"world_volume_scale":absf(node.global_basis.determinant()),"world_axis_scales":[node.global_basis.x.length(),node.global_basis.y.length(),node.global_basis.z.length()]});id+=1
    var bindings={}
    var inventory=JSON.parse_string(FileAccess.get_file_as_string("res://../plans/reviews/fish-performance-audit-v1/inventory.validation.json"))
    for file in inventory.input_bindings:
        assert(FileAccess.file_exists(file),"Missing baseline dependency "+file)
        bindings[file]=FileAccess.get_sha256(file)
    var f=FileAccess.open(output.path_join("source.validation.json"),FileAccess.WRITE)
    f.store_string(JSON.stringify({"schema_version":1,"species":species,"real_length_cm":profile.real_length_cm,"profile":profile,"nodes":nodes,"visible_triangles":total,"bone_count":entry.skeleton.get_bone_count(),"inputs":bindings,"binary_sha256":files,"exporter_sha256":FileAccess.get_sha256(get_script().resource_path),"accepted":false,"production_changed":false},"  "));f.close()
    print("BUDGET_SOURCE ",species," ",total," ",nodes.map(func(n):return n.name))
    holder.queue_free();await process_frame
    factory.free();preload("res://scripts/aquarium/FishAppearanceCache.gd").clear();quit()
