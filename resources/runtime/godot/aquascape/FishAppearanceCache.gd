extends RefCounted
## Bounded, process-local prepared appearance templates. No disk/model export.
const Data=preload("res://scripts/aquarium/FishRuntimeData.gd")
static var _templates: Dictionary={}
static var _generation := ""
static var _exit_connected := false
static var metrics := {"hits":0,"misses":0,"invalidations":0}

static func _files(path: String,extensions: Array,result: Array[String]) -> void:
    var directory := DirAccess.open(path)
    if directory==null:return
    for name in directory.get_files():
        if name.get_extension() in extensions:result.append(path.path_join(name))
    for name in directory.get_directories():_files(path.path_join(name),extensions,result)

static func begin_entry() -> void:
    if not _exit_connected and Engine.get_main_loop() is SceneTree:
        (Engine.get_main_loop() as SceneTree).root.tree_exiting.connect(clear)
        _exit_connected=true
    Data.begin_entry()
    var files: Array[String]=[]
    _files("res://scripts/aquarium",["gd","gdshader","gdshaderinc"],files)
    # Config changes can activate previously unused donors or helper branches.
    var config_dir := DirAccess.open("res://assets/models/fish/motion")
    for name in config_dir.get_files():
        if name.ends_with(".json"):files.append("res://assets/models/fish/motion/"+name)
    files.sort()
    var generation := "appearance-cache-v1"
    for path in files:generation+=path+Data.sha256(path)
    for key in ["FISH_EYE_MODE","FISH_EYE_PROBE","FISH_EYE_RETIRED_PROBE"]:generation+=key+OS.get_environment(key)
    var digest := generation.sha256_text()
    if digest!=_generation:
        clear();_generation=digest

static func _clone(source: Node3D) -> Node3D:
    var model := source.duplicate(7) as Node3D
    model.scene_file_path=source.scene_file_path
    var materials: Dictionary={}
    for node in [model]+model.find_children("*","Node",true,false):
        for key in node.get_meta_list():
            var value: Variant=node.get_meta(key)
            if value is Dictionary or value is Array:node.set_meta(key,value.duplicate(true))
        if not node is MeshInstance3D:continue
        if node.material_override!=null:
            var original: Material=node.material_override
            if not materials.has(original):materials[original]=original.duplicate()
            node.material_override=materials[original]
        for i in node.mesh.get_surface_count():
            var original: Material=node.get_active_material(i)
            if original==null:continue
            if not materials.has(original):materials[original]=original.duplicate()
            if original is ShaderMaterial:
                # These deliberately disabled legacy controls can be absent from
                # a composed shader's uniform list and omitted by duplicate().
                for key in ["mouth_source_projection","rim_local_source"]:
                    var value: Variant=original.get_shader_parameter(key)
                    if value!=null:materials[original].set_shader_parameter(key,value)
            node.set_surface_override_material(i,materials[original])
    # The appearance is unchanged; only per-instance material handles differ.
    if model.has_meta("mouth_repair139_receipt"):
        var receipt: Dictionary=model.get_meta("mouth_repair139_receipt")
        for name in receipt.auxiliary_unchanged:
            var mesh=model.find_child(name,true,false) as MeshInstance3D
            for i in receipt.auxiliary_unchanged[name].materials.size():
                receipt.auxiliary_unchanged[name].materials[i][0]=mesh.get_active_material(i).get_instance_id()
        model.set_meta("mouth_repair139_receipt",receipt)
    return model

static func get_model(species: String) -> Node3D:
    if "--gf-uncached-appearance" in OS.get_cmdline_user_args():return null
    if _templates.has(species):
        var record: Dictionary=_templates[species]
        var current := true
        for path in record.dependencies:
            if Data.sha256(path)!=record.dependencies[path]:current=false;break
        if current:
            metrics.hits+=1
            return _clone(record.model)
        record.model.free();_templates.erase(species);metrics.invalidations+=1
    metrics.misses+=1;return null

static func remember(species: String,model: Node3D,surfaces: Dictionary) -> void:
    if "--gf-uncached-appearance" in OS.get_cmdline_user_args():return
    if _templates.has(species):return
    # Actual helper validation ran before this snapshot, before animation starts.
    model.set_meta("cached_surface_counts",surfaces.duplicate(true))
    _templates[species]={"model":_clone(model),"dependencies":Data._digests.duplicate()}
    assert(_templates.size()<=32,"Prepared fish cache must remain bounded")

static func clear() -> void:
    for record in _templates.values():record.model.free()
    _templates.clear()
