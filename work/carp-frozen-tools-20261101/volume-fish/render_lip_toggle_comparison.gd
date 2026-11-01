extends SceneTree
## Current production zander, visibility-only A/B. No candidate meshes are loaded.
var output := ""
var preflight := false
var factory
var entries: Array = []
var cameras: Array = []
var viewports: Array = []
var worlds: Array = []
var bindings: Dictionary = {}
var checks: Dictionary = {}
var images: Array = []
var failures: Array = []
var layout: HBoxContainer
var totals: Array = []

func _initialize() -> void: call_deferred("run")
func bind(path: String) -> void:
    # Shared inputs and selected zander resources only; no whale asset/work scan.
    if "whale_shark" in path.to_lower():
        failures.append({"kind":"validation","code":"unexpected_other_species_input","message":path}); return
    if FileAccess.file_exists(path): bindings[path] = FileAccess.get_sha256(path)

func selected_paths(value: Variant) -> void:
    if value is Dictionary:
        for key in value: selected_paths(value[key])
    elif value is Array:
        for item in value: selected_paths(item)
    elif value is String and value.begins_with("res://"): bind(value)

func bind_inputs() -> void:
    var scripts := "res://scripts/aquarium"
    for name in DirAccess.open(scripts).get_files():
        if name.get_extension() in ["gd","gdshader","gdshaderinc"] and name != "FinalizedFish157.gd": bind(scripts.path_join(name))
    var candidate := scripts.path_join("review_candidates/zander")
    for name in DirAccess.open(candidate).get_files():
        if name.get_extension() in ["gd","gdshader","gdshaderinc"]: bind(candidate.path_join(name))
    var configs := "res://assets/models/fish/motion"
    for name in DirAccess.open(configs).get_files():
        if not name.ends_with(".json") or "whale" in name.to_lower(): continue
        var path := configs.path_join(name)
        var data = JSON.parse_string(FileAccess.get_file_as_string(path))
        if data is Dictionary and data.get("profiles",{}).has("zander"):
            bind(path); selected_paths(data.profiles.zander)
    bind("res://assets/models/fish/zander.glb")
    bind(get_script().resource_path)

func digest(value: Variant) -> String:
    var hash := HashingContext.new(); hash.start(HashingContext.HASH_SHA256)
    hash.update(var_to_bytes(value)); return hash.finish().hex_encode()

func stable(value: Variant) -> Variant:
    if value is Texture2D:
        if not value.resource_path.is_empty(): return {"texture":value.resource_path}
        var image: Image = value.get_image()
        return {"texture_class":value.get_class(),"pixels":digest(image.get_data()) if image else "missing"}
    if value is Material: return material_state(value)
    if value is Resource: return {"class":value.get_class(),"path":value.resource_path}
    if value is Dictionary:
        var result := {}
        for key in value: result[key] = stable(value[key])
        return result
    if value is Array:
        var result: Array = []
        for item in value: result.append(stable(item))
        return result
    return value

func material_state(material: Material) -> Dictionary:
    if material == null: return {"missing":true}
    var result := {"class":material.get_class()}
    if material is ShaderMaterial:
        result.shader = material.shader.code.sha256_text()
        var params := {}
        for uniform in material.shader.get_shader_uniform_list():
            params[str(uniform.name)] = stable(material.get_shader_parameter(uniform.name))
        result.parameters = params
    else:
        var properties := {}
        for property in material.get_property_list():
            var key: String = property.name
            if property.usage & PROPERTY_USAGE_STORAGE and key not in ["resource_name","resource_path","resource_local_to_scene","script"]:
                properties[key] = stable(material.get(key))
        result.properties = properties
    return result

func state(entry: Dictionary) -> Dictionary:
    var meshes := {}; var pose: Array = []; var stored := 0; var visible := 0; var lips := 0
    for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
        if mesh.mesh == null: continue
        var arrays: Array = []; var materials: Array = []; var count := 0; var skin: Array = []
        for surface in mesh.mesh.get_surface_count():
            var a: Array = mesh.mesh.surface_get_arrays(surface); arrays.append(a)
            var indices = a[Mesh.ARRAY_INDEX]; var vertices = a[Mesh.ARRAY_VERTEX]
            count += (indices.size() if indices != null and indices.size()>0 else vertices.size())/3
            materials.append(material_state(mesh.get_active_material(surface)))
        if mesh.skin != null:
            for i in mesh.skin.get_bind_count(): skin.append([mesh.skin.get_bind_bone(i),str(mesh.skin.get_bind_name(i)),mesh.skin.get_bind_pose(i)])
        meshes[str(entry.model.get_path_to(mesh))] = {"arrays":digest(arrays),"materials":digest(materials),"skin":digest(skin),"skeleton":str(mesh.skeleton),"transform":mesh.transform,"visible":mesh.visible}
        stored += count
        if mesh.is_visible_in_tree(): visible += count
        if str(mesh.name)=="Source_lips139": lips += count
    for i in entry.skeleton.get_bone_count(): pose.append([entry.skeleton.get_bone_name(i),entry.skeleton.get_bone_parent(i),entry.skeleton.get_bone_rest(i),entry.skeleton.get_bone_pose(i)])
    return {"meshes":meshes,"pose":digest(pose),"model_transform":entry.model.transform,"carrier_transform":entry.carrier.transform,"stored_triangles":stored,"visible_triangles":visible,"lip_triangles":lips}

func run() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="): output = arg.trim_prefix("--output=")
        elif arg=="--preflight": preflight=true
    var allowed := ProjectSettings.globalize_path("res://../plans/reviews/fish-lip-toggle-v1").simplify_path()
    if not output.is_absolute_path() or output != allowed:
        push_error("--output must be the absolute fish-lip-toggle-v1 review directory"); quit(2); return
    if DirAccess.make_dir_recursive_absolute(output)!=OK:
        push_error("Cannot create comparison output"); quit(2); return
    bind_inputs()
    if not preflight and DisplayServer.get_name()=="headless":
        failures.append({"kind":"dependency","code":"rendered_display_required","message":"Use --preflight for headless checks; actual comparison needs Metal GPU"})
        await finish(); return
    root.content_scale_mode=Window.CONTENT_SCALE_MODE_DISABLED; root.size=Vector2i(1536,900)
    if not preflight: DisplayServer.window_set_size(Vector2i(1536,900))
    root.title="Zander / WITH lip band vs WITHOUT lip band / visibility only"
    layout=HBoxContainer.new(); layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); root.add_child(layout)
    preload("res://scripts/aquarium/FishRuntimeData.gd").begin_entry()
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new(); factory._load_profiles()
    for i in 2:
        var column:=VBoxContainer.new(); column.size_flags_horizontal=Control.SIZE_EXPAND_FILL; layout.add_child(column)
        var label:=Label.new(); label.text="LEFT: WITH LIP BAND / original" if i==0 else "RIGHT: WITHOUT LIP BAND / visibility only"
        label.add_theme_font_size_override("font_size",22); column.add_child(label)
        var container:=SubViewportContainer.new(); container.stretch=true; container.size_flags_vertical=Control.SIZE_EXPAND_FILL; column.add_child(container)
        var viewport:=SubViewport.new(); viewport.size=Vector2i(768,856); viewport.own_world_3d=true; container.add_child(viewport); viewports.append(viewport)
        var world:=Node3D.new(); viewport.add_child(world); worlds.append(world)
        var env:=WorldEnvironment.new(); env.environment=Environment.new(); env.environment.background_mode=Environment.BG_COLOR
        env.environment.background_color=Color("183b4a"); env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
        env.environment.ambient_light_color=Color.WHITE; env.environment.ambient_light_energy=0.8; world.add_child(env)
        var light:=DirectionalLight3D.new(); light.rotation_degrees=Vector3(-35,-30,0); light.shadow_enabled=false; world.add_child(light)
        var camera:=Camera3D.new(); camera.projection=Camera3D.PROJECTION_ORTHOGONAL; camera.near=0.001; camera.far=100
        world.add_child(camera); camera.current=true; cameras.append(camera)
        var count_before: int=factory.fish.size(); var profile: Dictionary=factory.profiles.zander
        factory._add_fish(world,"zander",float(profile.real_length_cm)/100.0,profile)
        if factory.fish.size()!=count_before+1 or factory.fish[-1].species!="zander":
            failures.append({"kind":"validation","code":"fish_load_failed","message":"Current zander factory did not append requested fish"}); await finish(); return
        var entry: Dictionary=factory.fish[-1]; entries.append(entry)
        entry.controller.seek(0.0); entry.player.pause(); entry.carrier.transform=Transform3D.IDENTITY
        entry.skeleton.force_update_all_bone_transforms()
        var lip=entry.model.find_child("Source_lips139",true,false) as MeshInstance3D
        if lip==null or lip.mesh==null or not lip.visible:
            failures.append({"kind":"validation","code":"lip_missing","message":"Current Source_lips139 missing or already hidden"}); await finish(); return
        await process_frame
    # Track only paths actually validated by this selected-species factory call.
    for path in preload("res://scripts/aquarium/FishRuntimeData.gd")._digests:
        if not bindings.has(path): bindings[path]=preload("res://scripts/aquarium/FishRuntimeData.gd")._digests[path]
    var left:=state(entries[0]); var right:=state(entries[1]); totals=[left,right]
    checks.identical_mesh_skin_material_pose_before_toggle = left==right
    var lip: MeshInstance3D=entries[1].model.find_child("Source_lips139",true,false)
    lip.visible=false # The only A/B change.
    var toggled:=state(entries[1]); var normalized: Dictionary=toggled.duplicate(true)
    for path in normalized.meshes:
        if path.ends_with("/Source_lips139"): normalized.meshes[path].visible=true
    normalized.visible_triangles=right.visible_triangles
    checks.only_lip_visibility_changed = normalized==right
    checks.visible_triangle_delta_equals_lip = left.visible_triangles-toggled.visible_triangles==left.lip_triangles
    totals[1]=toggled
    if not checks.identical_mesh_skin_material_pose_before_toggle or not checks.only_lip_visibility_changed or not checks.visible_triangle_delta_equals_lip:
        failures.append({"kind":"validation","code":"comparison_mismatch","message":"Geometry, skin, materials, pose or visibility changed beyond the lip toggle"})
        await finish(); return
    var baseline_lip: MeshInstance3D=entries[0].model.find_child("Source_lips139",true,false)
    var box: AABB=baseline_lip.global_transform*baseline_lip.get_aabb()
    for shot in ["whole-pair","mouth-oblique-pair","mouth-front-pair"]:
        var target: Vector3=Vector3.ZERO if shot=="whole-pair" else box.get_center()
        var direction:=Vector3(0,0,1) if shot=="whole-pair" else (Vector3(1,0,0) if shot=="mouth-front-pair" else Vector3(1,0.25,1).normalized())
        for camera in cameras:
            camera.size=float(entries[0].length_m)*1.35 if shot=="whole-pair" else box.size.length()*2.7
            camera.position=target+direction*2.0; camera.look_at(target)
        checks[shot+"_cameras_equal"]=cameras[0].transform==cameras[1].transform and cameras[0].size==cameras[1].size
        if preflight: continue
        for frame in 4: await process_frame
        await RenderingServer.frame_post_draw
        var path:=output.path_join(shot+".png")
        if root.get_texture().get_image().save_png(path)!=OK: failures.append({"kind":"validation","code":"image_write_failed","message":path})
        else: images.append({"path":path,"sha256":FileAccess.get_sha256(path),"camera_transform":str(cameras[0].transform),"orthographic_size":cameras[0].size})
    await finish()

func finish() -> void:
    var changes: Array=[]
    for path in bindings:
        if FileAccess.get_sha256(path)!=bindings[path]: changes.append(path)
    if not changes.is_empty(): failures.append({"kind":"validation","code":"input_changed","message":str(changes)})
    var report:={"schema_version":1,"command":"fish.lip.visibility-comparison","stage":"validate","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","scope":"visibility_only/prototype_only","inputs":{"species":"zander","seek_seconds":0.0,"left":"current factory, lip visible","right":"same factory, only Source_lips139.visible=false","sha256_before":bindings,"changed_inputs":changes},"summary":{"checks":checks,"triangles":totals,"images":images,"rendered":not preflight and not images.is_empty(),"preflight_only":preflight,"whale_instantiations":0,"acceptance":"pending visual review; no geometry/material/model/fin/body acceptance"},"outputs":images.map(func(item):return item.path),"failures":failures}
    if is_instance_valid(factory): factory.fish.clear(); factory.free(); factory=null
    entries.clear(); preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    if is_instance_valid(layout): layout.queue_free()
    cameras.clear(); viewports.clear(); worlds.clear()
    for frame in 3: await process_frame
    var path:=output.path_join("preflight.validation.json" if preflight else "comparison.validation.json")
    report.outputs.append(path)
    var file:=FileAccess.open(path,FileAccess.WRITE)
    if file==null: push_error("Cannot write comparison report"); quit(2); return
    file.store_string(JSON.stringify(report,"  ")+"\n"); file.close()
    print("LIP_TOGGLE_COMPARISON ",JSON.stringify({"ok":report.ok,"report":path,"checks":checks}))
    quit(0 if failures.is_empty() else 1)
