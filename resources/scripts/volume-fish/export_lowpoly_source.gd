extends SceneTree
var output=""
func _initialize():
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(output.is_absolute_path() and output.simplify_path().begins_with(ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()))
    DirAccess.make_dir_recursive_absolute(output);call_deferred("run")
func run():
    var holder=Node3D.new();root.add_child(holder)
    var factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    factory._add_fish(holder,"zander",float(factory.profiles.zander.real_length_cm)/100.,factory.profiles.zander)
    var model=factory.fish[-1].model;var nodes=[];var id=0
    for node in model.find_children("*","MeshInstance3D",true,false):
        if not node.visible:continue
        var parts=[]
        for si in node.mesh.get_surface_count():
            var a=node.mesh.surface_get_arrays(si);var row={"surface":si,"count":a[Mesh.ARRAY_VERTEX].size(),"attributes":{}}
            for slot in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_COLOR,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_TEX_UV2,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:
                if a[slot]==null or a[slot].is_empty():continue
                var name="source-"+str(id)+"-"+str(si)+"-"+str(slot)+".bin"
                var f=FileAccess.open(output.path_join(name),FileAccess.WRITE);f.store_buffer(a[slot].to_byte_array());f.close()
                row.attributes[str(slot)]=name
            parts.append(row)
        nodes.append({"name":String(node.name),"path":str(model.get_path_to(node)),"surfaces":parts});id+=1
    var bindings={}
    var inventory=JSON.parse_string(FileAccess.get_file_as_string("res://../plans/reviews/fish-performance-audit-v1/inventory.validation.json"))
    for file in inventory.input_bindings:
        if FileAccess.file_exists(file):bindings[file]=FileAccess.get_sha256(file)
    var f=FileAccess.open(output.path_join("source.validation.json"),FileAccess.WRITE)
    f.store_string(JSON.stringify({"species":"zander","nodes":nodes,"inputs":bindings,"accepted":false,"production_changed":false},"  "));f.close()
    print("SOURCE_EXPORT ",nodes.size()," nodes")
    holder.queue_free();await process_frame
    factory.free();preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    quit()
