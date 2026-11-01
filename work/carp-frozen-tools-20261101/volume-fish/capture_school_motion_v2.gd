extends SceneTree
## Controlled visual evidence, never a real-time FPS or model acceptance test.
const SPECIES := ["atlantic_sailfish", "whale_shark"]
const LABELS := ["大西洋旗鱼 · 2.4 m", "鲸鲨 · 8 m"]
const TOTAL_FRAMES := 192
const CAPTURE_FPS := 24
var output := ""
var wrapper_path := "res://scripts/aquarium/fish_school/FishSchoolReview.gd"
var variant := "current"
var ffmpeg := ""
var video := false
var viewer
var before: Dictionary = {}
var wrapper_hash := ""
var cameras: Array = []
var panels: Array = []
var captions: Array = []
var heading_label: Label
var captures: Array = []
var failures: Array = []
var tick := 0
var yaw_value := 0.0
var sample_ticks: Array = []
var start_clocks: Dictionary = {}
var final_clocks: Dictionary = {}
var raw_sequence_count := 0
var raw_sequence_bytes := 0
var sequence_deleted := false

func _initialize() -> void: call_deferred("run")

func run() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--capture-output="): output = arg.trim_prefix("--capture-output=")
        elif arg.begins_with("--baseline-wrapper="):
            wrapper_path = arg.trim_prefix("--baseline-wrapper=")
            variant = "frozen-v1"
        elif arg.begins_with("--ffmpeg="): ffmpeg = arg.trim_prefix("--ffmpeg=")
        elif arg == "--video": video = true
    var allowed := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path() + "/"
    var exact_snapshot := allowed + "baseline-v1/FishSchoolReview.gd"
    if output.is_empty() or not output.is_absolute_path() or output != output.simplify_path() or not output.begins_with(allowed):
        push_error("Capture output must be absolute beneath fish-school-motion-v2"); quit(2); return
    if variant == "frozen-v1" and wrapper_path != exact_snapshot:
        push_error("Baseline wrapper must be exact preserved baseline-v1 snapshot"); quit(2); return
    if FileAccess.file_exists(output.path_join("capture.validation.json")):
        push_error("Preserve existing capture evidence; select a fresh output directory"); quit(2); return
    if DisplayServer.get_name() == "headless" or (video and (not ffmpeg.is_absolute_path() or not FileAccess.file_exists(ffmpeg))):
        push_error("Rendered display required; --video also needs existing absolute --ffmpeg path"); quit(2); return
    if DirAccess.make_dir_recursive_absolute(output) != OK:
        push_error("Cannot create capture output"); quit(2); return
    if video: DirAccess.make_dir_recursive_absolute(output.path_join("frames"))
    root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
    root.size = Vector2i(1536,1024)
    DisplayServer.window_set_size(Vector2i(1536,1024))
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    viewer = Node3D.new(); root.add_child(viewer)
    viewer.set_script(load(wrapper_path)); viewer.set_process(false)
    viewer.roster = SPECIES.duplicate(); viewer.count = SPECIES.size()
    viewer.mode = "motion"; viewer.benchmark = false
    before = viewer._bindings(); wrapper_hash = FileAccess.get_sha256(wrapper_path)
    viewer._build_world()
    var populated: bool = await viewer._populate()
    viewer.set_process(false)
    if not populated or viewer.entries.size() != SPECIES.size():
        failures.append({"kind":"validation","code":"capture_population_failed","message":"Actual viewer population did not create both requested species"})
        await finish(); return
    viewer.camera.current = false
    for child in viewer.world.get_children():
        if child.has_meta("school_obstacle"): child.queue_free()
    for i in viewer.entries.size():
        var entry: Dictionary = viewer.entries[i]
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false): mesh.layers = 1 << i
        viewer.simulation.positions[i] = Vector3.ZERO
    # Feed the actual input flow for longer than the largest authored body delay;
    # this removes random initial route-heading transients in both variants.
    for warmup_tick in 60:
        for i in viewer.entries.size():
            viewer.simulation.velocities[i] = Vector3.RIGHT
            viewer.simulation.positions[i] += Vector3.RIGHT/60.0
        viewer._process(1.0/60.0)
    for entry in viewer.entries:
        start_clocks[entry.species] = {"body":entry.controller._body_clock,"fin":entry.controller._fin_clock}
    build_panels()
    var accumulator := 0.0
    for frame in range(1,TOTAL_FRAMES+1):
        accumulator += 60.0/CAPTURE_FPS
        var steps := floori(accumulator + 0.000001); accumulator -= steps
        for step_index in steps:
            var rate := 0.35 if tick < 240 else -0.35
            yaw_value += rate/60.0
            tick += 1
            for i in viewer.entries.size():
                viewer.simulation.velocities[i] = Vector3(cos(yaw_value),0,-sin(yaw_value))
                viewer.simulation.positions[i] += viewer.simulation.velocities[i]/60.0
            viewer._process(1.0/60.0)
        sample_ticks.append(tick)
        follow()
        heading_label.text = "%s · 受控输入 %.3f s · 航向 %.1f° · 4秒反向 · 真实模型 / 60 Hz输入，24 fps采样" % [variant,tick/60.0,rad_to_deg(yaw_value)]
        await process_frame
        await RenderingServer.frame_post_draw
        var image := root.get_texture().get_image()
        if video:
            var frame_path := output.path_join("frames/frame_%04d.png" % frame)
            var saved := image.save_png(frame_path)
            if saved != OK: failures.append({"kind":"validation","code":"video_frame_save_failed","message":frame_path + ": " + str(saved)})
        if frame in [48,96,144,192]:
            var path := output.path_join("at_%02ds.png" % (frame/CAPTURE_FPS))
            if image.save_png(path) == OK: captures.append(path)
            else: failures.append({"kind":"validation","code":"capture_save_failed","message":path})
    for entry in viewer.entries:
        final_clocks[entry.species] = {"body":entry.controller._body_clock,"fin":entry.controller._fin_clock}
    if video: encode_video()
    await finish()

func build_panels() -> void:
    var layer := CanvasLayer.new(); layer.layer = 10; root.add_child(layer)
    panels.append(layer)
    var background := ColorRect.new(); background.color = Color("101e27"); background.size = Vector2(1536,1024); layer.add_child(background)
    heading_label = Label.new(); heading_label.position = Vector2(18,16); heading_label.add_theme_font_size_override("font_size",22); layer.add_child(heading_label)
    for i in viewer.entries.size():
        for view in 2:
            var viewport := SubViewport.new(); viewport.size = Vector2i(752,416)
            viewport.world_3d = viewer.get_world_3d(); viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
            root.add_child(viewport); panels.append(viewport)
            var camera := Camera3D.new(); camera.cull_mask = 1 << i
            camera.projection = Camera3D.PROJECTION_ORTHOGONAL; camera.size = viewer.entries[i].length_m*0.8
            camera.near = 0.01; camera.far = 200
            viewport.add_child(camera); camera.current = true
            cameras.append({"camera":camera,"entry":i,"top":view==0})
            var caption := Label.new(); caption.position = Vector2(view*768+18,i*456+66)
            caption.text = LABELS[i] + (" · 俯视" if view==0 else " · 斜视")
            caption.add_theme_font_size_override("font_size",20); layer.add_child(caption)
            var rect := TextureRect.new(); rect.texture = viewport.get_texture(); rect.position = Vector2(view*768+8,i*456+98)
            rect.size = Vector2(752,416); rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE; rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
            layer.add_child(rect)
    var note := Label.new(); note.position = Vector2(18,990)
    note.text = "相机随鱼平移与转向，保留模型、骨骼、贴图和材质；仅隔离显示层。此片段不代表实时性能、形态或动作验收。"
    layer.add_child(note)

func follow() -> void:
    for item in cameras:
        var entry: Dictionary = viewer.entries[item.entry]
        var center: Vector3 = entry.carrier.global_position
        var basis: Basis = entry.carrier.global_basis
        var length_m: float = entry.length_m
        item.camera.global_position = center + basis*(Vector3(0,length_m*1.3,0) if item.top else Vector3(0,length_m*0.65,length_m*1.1))
        item.camera.look_at(center,-basis.z if item.top else basis.y)

func encode_video() -> void:
    for frame in range(1,TOTAL_FRAMES+1):
        var frame_path := output.path_join("frames/frame_%04d.png" % frame)
        if FileAccess.file_exists(frame_path):
            raw_sequence_count += 1
            var file := FileAccess.open(frame_path,FileAccess.READ)
            if file != null: raw_sequence_bytes += file.get_length(); file.close()
    if raw_sequence_count != TOTAL_FRAMES:
        failures.append({"kind":"validation","code":"video_sequence_incomplete","message":"Expected192 frame files; found " + str(raw_sequence_count)})
    if not failures.is_empty(): return
    var logs: Array = []
    var target := output.path_join("motion.mp4")
    var args := PackedStringArray(["-y","-loglevel","error","-framerate",str(CAPTURE_FPS),"-start_number","1","-i",output.path_join("frames/frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","18",target])
    var code := OS.execute(ffmpeg,args,logs,true)
    if code != 0 or not FileAccess.file_exists(target):
        failures.append({"kind":"dependency","code":"video_encoding_failed","message":str(logs)})
        return
    captures.append(target)
    if before != viewer._bindings() or wrapper_hash != FileAccess.get_sha256(wrapper_path):
        failures.append({"kind":"validation","code":"capture_source_changed_before_cleanup","message":"Preserving raw frames because capture sources changed"})
        return
    # Delete only the exact generated sequence after the encoded clip exists.
    var deleted := 0
    for frame in range(1,TOTAL_FRAMES+1):
        if DirAccess.remove_absolute(output.path_join("frames/frame_%04d.png" % frame)) == OK: deleted += 1
    sequence_deleted = deleted == TOTAL_FRAMES
    if not sequence_deleted: failures.append({"kind":"validation","code":"video_sequence_cleanup_incomplete","message":"Removed " + str(deleted) + " of192 encoded frames"})
    var directory := DirAccess.open(output.path_join("frames"))
    if directory != null and directory.get_files().is_empty() and directory.get_directories().is_empty(): DirAccess.remove_absolute(output.path_join("frames"))

func finish() -> void:
    var after: Dictionary = viewer._bindings()
    if before != after or wrapper_hash != FileAccess.get_sha256(wrapper_path): failures.append({"kind":"validation","code":"capture_source_changed","message":"Sources changed during controlled capture"})
    var hashes := {}
    for path in captures: hashes[path] = FileAccess.get_sha256(path)
    var critical := {}
    for path in before:
        if path.ends_with("/FoundryFishMotion.gd") or path.ends_with("/motion.json") or path.ends_with("/atlantic_sailfish.glb") or path.ends_with("/whale_shark.glb") or path.ends_with("/FishSchoolSimulation.gd"): critical[path] = before[path]
    var report := {"schema_version":1,"command":"fish.school.motion.focused-capture","stage":"validate","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","inputs":{"variant":variant,"wrapper_path":wrapper_path,"wrapper_sha256":wrapper_hash,"helper_sha256":FileAccess.get_sha256(get_script().resource_path),"source_binding_count":before.size(),"source_bindings_before_sha256":JSON.stringify(before).sha256_text(),"source_bindings_after_sha256":JSON.stringify(after).sha256_text(),"critical_file_sha256":critical,"species":SPECIES,"fixed_input_hz":60,"straight_preroll_ticks":60,"straight_preroll_seconds":1.0,"capture_fps":CAPTURE_FPS,"frames":TOTAL_FRAMES,"actual_simulation_ticks":tick,"sample_fixed_tick_indices":sample_ticks,"sampling":"accumulator alternates2/3 fixed60Hz ticks per24fps sample; no interpolation or wall-time FPS claim","speed_mps":1.0,"signed_yaw_rate_rps":[0.35,-0.35],"reversal_at_seconds":4},"summary":{"initial_native_clocks":start_clocks,"final_native_clocks":final_clocks,"capture_sha256":hashes,"raw_sequence_count":raw_sequence_count,"raw_sequence_bytes":raw_sequence_bytes,"temporary_sequence_deleted_after_encoding":sequence_deleted,"window_size":[root.size.x,root.size.y],"viewport_texture_size":[root.get_texture().get_size().x,root.get_texture().get_size().y],"rendering_method":RenderingServer.get_current_rendering_method(),"rendering_driver":RenderingServer.get_current_rendering_driver_name()},"scope":"Selected actual fish, camera follows carrier center and heading at species-relative framing; production mesh/skin/materials retained, only display visibility layers changed; no water/obstacles; visual evidence awaiting review, not performance or model/fin-root/body acceptance","outputs":captures+[output.path_join("capture.validation.json")],"failures":failures}
    viewer.set_process(false); viewer.entries.clear()
    if is_instance_valid(viewer.factory): viewer.factory.fish.clear(); viewer.factory.free(); viewer.factory = null
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    cameras.clear()
    for panel in panels: panel.queue_free()
    panels.clear(); viewer.queue_free(); viewer = null
    for frame in 3: await process_frame
    var file := FileAccess.open(output.path_join("capture.validation.json"),FileAccess.WRITE)
    if file == null: push_error("Cannot write capture report"); quit(2); return
    file.store_string(JSON.stringify(report,"  ")+"\n"); file.close()
    print("SCHOOL_MOTION_CAPTURE ",JSON.stringify({"ok":report.ok,"variant":variant,"report":output.path_join("capture.validation.json")}))
    quit(0 if failures.is_empty() else 1)
