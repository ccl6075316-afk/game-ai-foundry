extends SceneTree
## Read-only actual-import/final-assembly audit; no model or acceptance changes.
var output := ""
var mode := "inventory"
var species_filter := "black_seabream"
var samples := 180
var holder: Node3D
var camera: Camera3D
var factory
var texture_cache: Dictionary = {}
var measurements: Array = []
var input_bindings: Dictionary = {}
var shared_geometry_stats: Dictionary = {}

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="): output=arg.trim_prefix("--output=")
        if arg.begins_with("--mode="): mode=arg.trim_prefix("--mode=")
        if arg.begins_with("--species="): species_filter=arg.trim_prefix("--species=")
        if arg.begins_with("--samples="): samples=int(arg.trim_prefix("--samples="))
    if output.is_empty() or not output.is_absolute_path() or samples<30:
        push_error("Explicit absolute review output and >=30 samples required");quit(2);return
    DirAccess.make_dir_recursive_absolute(output)
    call_deferred("run")

func bind_file(path: String) -> void:
    if path.is_empty() or not FileAccess.file_exists(path) or input_bindings.has(path):return
    input_bindings[path]=FileAccess.get_sha256(path)

func bind_tree(path: String, extensions: Array) -> void:
    var directory=DirAccess.open(path)
    if directory==null:return
    for name in directory.get_files():
        if name.get_extension() in extensions:bind_file(path.path_join(name))
    for name in directory.get_directories():bind_tree(path.path_join(name),extensions)

func geometry_stats(mesh: Mesh) -> Dictionary:
    var rid=mesh.get_instance_id()
    if shared_geometry_stats.has(rid):return shared_geometry_stats[rid]
    var rows: Array=[]
    var raw: Array=mesh.get("_surfaces") if mesh is ArrayMesh else []
    for si in mesh.get_surface_count():
        var a=mesh.surface_get_arrays(si)
        var v: PackedVector3Array=a[Mesh.ARRAY_VERTEX]
        var indices: PackedInt32Array=a[Mesh.ARRAY_INDEX]
        var used=PackedByteArray();used.resize(v.size());used.fill(0)
        var position_ids: Dictionary={};var point_ids=PackedInt32Array()
        var nonfinite := 0
        for vertex in v:
            if not vertex.is_finite():nonfinite+=1
            if not position_ids.has(vertex):position_ids[vertex]=position_ids.size()
            point_ids.append(position_ids[vertex])
        var seen: Dictionary={};var zero := 0;var repeated := 0
        var near_zero := 0
        var scale2=maxf(mesh.get_aabb().size.length_squared(),1e-20)
        var count=indices.size() if not indices.is_empty() else v.size()
        var triangles=count/3 if mesh.surface_get_primitive_type(si)==Mesh.PRIMITIVE_TRIANGLES else 0
        for ti in triangles:
            var ids: Array[int]=[]
            for j in 3:
                var index=indices[ti*3+j] if not indices.is_empty() else ti*3+j
                ids.append(index);used[index]=1
            var area2=(v[ids[1]]-v[ids[0]]).cross(v[ids[2]]-v[ids[0]]).length()
            if area2==0.0:zero+=1
            elif area2<scale2*1e-12:near_zero+=1
            if area2>0.0:
                var keys: Array[int]=[point_ids[ids[0]],point_ids[ids[1]],point_ids[ids[2]]]
                keys.sort()
                var key=Vector3i(keys[0],keys[1],keys[2])
                if seen.has(key):repeated+=1
                else:seen[key]=true
        var referenced := 0
        for value in used:referenced+=value
        var lods=raw[si].get("lods",[]) if si<raw.size() else []
        rows.append({"surface":si,"vertices":v.size(),"triangles":triangles,
            "unused_vertices":v.size()-referenced,"nonfinite_vertices":nonfinite,
            "exact_zero_area_triangles":zero,"near_zero_area_triangles":near_zero,
            "coincident_triangles_within_surface":repeated,
            "has_imported_lods":not lods.is_empty(),
            "bone_slots_per_vertex":a[Mesh.ARRAY_BONES].size()/maxi(1,v.size()) if a[Mesh.ARRAY_BONES]!=null else 0})
    var result={"surfaces":rows,"geometry_resource":mesh.resource_path}
    bind_file(mesh.resource_path)
    shared_geometry_stats[rid]=result
    return result

func texture_stats(texture: Texture2D) -> Dictionary:
    var id=texture.get_instance_id()
    if not texture_cache.has(id):
        var image=texture.get_image()
        texture_cache[id]={"width":texture.get_width(),"height":texture.get_height(),
            "image_data_bytes":image.get_data_size() if image!=null else 0,
            "mipmaps":image.has_mipmaps() if image!=null else false,
            "resource":texture.resource_path}
        bind_file(texture.resource_path)
    return texture_cache[id]

func inspect_model(model: Node3D) -> Dictionary:
    var meshes: Array=[];var materials: Dictionary={};var shaders: Dictionary={};var textures: Dictionary={}
    var total={"vertices":0,"triangles":0,"visible_triangles":0,"hidden_triangles":0,
        "visible_surfaces":0,"hidden_meshes":0,"unused_vertices":0,"nonfinite_vertices":0,
        "exact_zero_area_triangles":0,"near_zero_area_triangles":0,
        "coincident_triangles_within_surface":0,"visible_surfaces_with_lods":0,"bones":0}
    for skeleton in model.find_children("*","Skeleton3D",true,false):total.bones+=skeleton.get_bone_count()
    for node in model.find_children("*","MeshInstance3D",true,false):
        var mesh=node as MeshInstance3D
        if mesh.mesh==null:continue
        var geometry=geometry_stats(mesh.mesh)
        var shown=mesh.is_visible_in_tree()
        if not shown:total.hidden_meshes+=1
        var row={"node":str(model.get_path_to(mesh)),"visible":shown,"surfaces":geometry.surfaces,
            "geometry_resource":geometry.geometry_resource,"materials":[]}
        for surface in geometry.surfaces:
            for field in ["vertices","triangles","unused_vertices","nonfinite_vertices",
                    "exact_zero_area_triangles","near_zero_area_triangles","coincident_triangles_within_surface"]:
                total[field]+=surface[field]
            if shown:
                total.visible_triangles+=surface.triangles;total.visible_surfaces+=1
                if surface.has_imported_lods:total.visible_surfaces_with_lods+=1
            else:total.hidden_triangles+=surface.triangles
            var material=mesh.get_active_material(surface.surface)
            var record={"type":"none"}
            if material!=null:
                materials[material.get_instance_id()]=true;bind_file(material.resource_path)
                record={"type":material.get_class(),"resource":material.resource_path,"textures":[]}
                if material is ShaderMaterial:
                    var shader=material.shader
                    var code=shader.code
                    var digest=code.sha256_text()
                    shaders[digest]={"characters":code.length(),"texture_call_sites":code.count("texture(" )+code.count("texelFetch("),"resource":shader.resource_path}
                    record.shader_sha256=digest;bind_file(shader.resource_path)
                    for uniform in shader.get_shader_uniform_list():
                        var value=material.get_shader_parameter(uniform.name)
                        if value is Texture2D:
                            var info=texture_stats(value)
                            textures[value.get_instance_id()]=info
                            record.textures.append({"uniform":uniform.name,"texture":info})
                elif material is BaseMaterial3D:
                    record.transparency=material.transparency;record.cull_mode=material.cull_mode
                    record.shading_mode=material.shading_mode
                    for slot in BaseMaterial3D.TEXTURE_MAX:
                        var value=material.get_texture(slot)
                        if value!=null:
                            var info=texture_stats(value);textures[value.get_instance_id()]=info
                            record.textures.append({"slot":slot,"texture":info})
            row.materials.append(record)
        meshes.append(row)
    var bytes := 0
    for info in textures.values():bytes+=info.image_data_bytes
    total.meshes=meshes.size();total.node_count=model.find_children("*","Node",true,false).size()+1
    total.unique_materials=materials.size();total.unique_shader_variants=shaders.size()
    total.unique_texture_objects=textures.size();total.texture_image_data_bytes=bytes
    return {"totals":total,"meshes":meshes,"shaders":shaders.values()}

func self_test() -> bool:
    var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX]=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.UP,Vector3.ONE])
    arrays[Mesh.ARRAY_INDEX]=PackedInt32Array([0,1,2,0,1,2,0,0,1])
    var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
    var row=geometry_stats(mesh).surfaces[0]
    return row.triangles==3 and row.unused_vertices==1 and row.exact_zero_area_triangles==1 and row.coincident_triangles_within_surface==1

func distribution(values: Array) -> Dictionary:
    if values.is_empty():return {}
    var sorted=values.duplicate();sorted.sort();var sum := 0.0
    for value in values:sum+=float(value)
    return {"mean":sum/values.size(),"p50":sorted[int((sorted.size()-1)*.5)],
        "p95":sorted[int((sorted.size()-1)*.95)],"max":sorted[-1]}

func measure_case(label: String, animated: bool, count: int) -> Dictionary:
    var frame_ms: Array=[];var motion_ms: Array=[];var draws: Array=[];var primitives: Array=[];var gpu: Array=[];var cpu: Array=[]
    var previous=Time.get_ticks_usec()
    for index in samples+60:
        await process_frame
        var started=Time.get_ticks_usec()
        if animated:
            for row in factory.fish:
                row.controller.step(1.0/60.0)
                if row.has("jaw_controller"):row.jaw_controller.apply(.5)
                row.carrier.position=row.audit_home
        var elapsed=(Time.get_ticks_usec()-started)/1000.0
        await RenderingServer.frame_post_draw
        var now=Time.get_ticks_usec()
        if index>=60:
            frame_ms.append((now-previous)/1000.0);motion_ms.append(elapsed)
            draws.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
            primitives.append(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
            gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()))
            cpu.append(RenderingServer.viewport_get_measured_render_time_cpu(root.get_viewport_rid()))
        previous=now
    return {"label":label,"fish_count":count,"animated":animated,"sample_frames":samples,
        "frame_ms":distribution(frame_ms),"motion_step_ms":distribution(motion_ms),
        "draw_calls":distribution(draws),"rendered_primitives":distribution(primitives),
        "renderer_gpu_ms":distribution(gpu),"renderer_cpu_ms":distribution(cpu)}

func clear_fish() -> void:
    for row in factory.fish:row.carrier.queue_free()
    factory.fish.clear()
    await process_frame
    await RenderingServer.frame_post_draw

func run() -> void:
    var started=Time.get_ticks_usec()
    bind_tree("res://scripts/aquarium",["gd","gdshader","gdshaderinc"])
    bind_tree("res://assets/models/fish/motion",["json","res"])
    bind_tree("res://assets/models/fish",["glb"])
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    Engine.max_fps=0
    root.size=Vector2i(1280,720)
    root.title="鱼模型性能审计 · 临时测量窗口"
    holder=Node3D.new();root.add_child(holder)
    camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.01;camera.far=200
    holder.add_child(camera);camera.position=Vector3(0,0,10);camera.current=true
    var environment=WorldEnvironment.new();environment.environment=Environment.new()
    environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("152b36")
    environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_energy=.7
    holder.add_child(environment)
    var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-25,0);holder.add_child(light)
    RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(),true)
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var fixture_ok=self_test()
    var inventory: Array=[]
    if mode=="inventory":
        for species in factory.SPECIES:
            var path="res://assets/models/fish/"+species+".glb"
            var original=(load(path) as PackedScene).instantiate();holder.add_child(original)
            var raw=inspect_model(original);original.queue_free()
            var profile:Dictionary=factory.profiles[species]
            factory._add_fish(holder,species,float(profile.real_length_cm)/100.,profile)
            var entry:Dictionary=factory.fish[-1]
            var final=inspect_model(entry.model)
            inventory.append({"species":species,"raw_import":raw,"final":final,"load":factory.loading_metrics[-1]})
            print("FISH_AUDIT ",species," ",JSON.stringify(final.totals))
            await clear_fish()
    else:
        camera.position=Vector3(0,0,20);camera.size=2.0
        measurements.append(await measure_case("empty",false,0))
        var selections: Array=[1,10,50]
        for count in selections:
            var profile:Dictionary=factory.profiles[species_filter]
            var length_m=float(profile.real_length_cm)/100.
            var columns=ceili(sqrt(float(count)*1.7));var rows=ceili(float(count)/columns)
            for i in count:
                factory._add_fish(holder,species_filter,length_m,profile)
                var entry:Dictionary=factory.fish[-1]
                entry.audit_home=Vector3((float(i%columns)-(columns-1)*.5)*length_m*1.2,
                    ((rows-1)*.5-float(i/columns))*length_m*.65,0)
                entry.carrier.position=entry.audit_home
            camera.size=maxf(length_m*rows*.85,length_m*columns*1.35/(1280./720.))
            for animated in [false,true]:
                var result=await measure_case(species_filter+"_"+str(count),animated,count)
                measurements.append(result);print("FISH_BENCH ",JSON.stringify(result))
            if count==50:
                root.get_texture().get_image().save_png(output+"/"+species_filter+"-50.png")
            await clear_fish()
    var changed: Array=[]
    for path in input_bindings:
        if FileAccess.get_sha256(path)!=input_bindings[path]:changed.append(path)
    var report={"schema_version":1,"command":"fish.runtime-performance-audit","ok":fixture_ok and changed.is_empty(),
        "status":"done" if fixture_ok and changed.is_empty() else "blocked","next_action":"human_review",
        "self_test":fixture_ok,"input_changes":changed,"input_bindings":input_bindings,
        "gpu":RenderingServer.get_video_adapter_name(),"rendering_method":RenderingServer.get_current_rendering_method(),
        "resolution":[1280,720],"mode":mode,"inventory":inventory,"benchmarks":measurements,
        "elapsed_seconds":(Time.get_ticks_usec()-started)/1000000.,
        "limits":["Audit only, no anatomical acceptance or model modifications.",
            "Coincident triangles are candidates, not automatically removable; opposite sides and layered materials may be intentional.",
            "Exact zero area and unreferenced vertices are structural diagnostics; near-zero threshold is AABB diagonal squared times 1e-12.",
            "Triangle counts are base imported/final geometry, not proof of per-frame rasterized count or LOD choice.",
            "Texture bytes sum unique texture objects per fish; shared content can still appear in distinct objects. This is not total VRAM.",
            "Shader texture call sites are source-text counts, not executed samples or GPU timing.",
            "Benchmarks use a diagnostic grid and actual controllers, fixed 1/60 simulation step, no tank/water/shadows, VSync off, 60 warmup frames.",
            "Renderer timing zero may be unsupported; other desktop GPU workloads can affect wall times."]}
    var file=FileAccess.open(output+"/"+mode+".validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  "));file.close()
    factory.free()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    quit(0 if report.ok else 1)
