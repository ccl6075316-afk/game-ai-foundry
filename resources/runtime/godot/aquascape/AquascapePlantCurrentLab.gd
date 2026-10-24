extends "res://scripts/aquarium/AquascapeThreeViewLab.gd"
var plant_current
var flow_button: Button

func _build() -> void:
    super._build()
    DisplayServer.window_set_title("潮汐馆 · 水草微流动态 V4")
    plant_current=preload("res://scripts/aquarium/PlantCurrent.gd").new()
    add_child(plant_current)
    for id in ["anubias","java_fern"]:
        var old: Node3D=art_nodes[id]
        var at: Vector3=old.position
        for mesh in old.find_children("*","MeshInstance3D",true,false):art_originals.erase(mesh)
        scenery.remove_child(old)
        old.queue_free()
        var packed: PackedScene=load("res://assets/aquascape-v4/"+id+".glb")
        var model: Node3D=packed.instantiate()
        model.name=id
        scenery.add_child(model)
        model.position=at
        art_nodes[id]=model
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            var originals: Array=[]
            for surface in mesh.mesh.get_surface_count():
                var painted: StandardMaterial3D=mesh.get_active_material(surface).duplicate()
                painted.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
                painted.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
                originals.append(painted)
                mesh.set_surface_override_material(surface,painted)
            art_originals[mesh]=originals
        plant_current.attach(id,model)
    plant_current.apply_at(0.0)

func _ui() -> void:
    super._ui()
    for label in find_children("*","Label",true,false):
        if label.text.begins_with("A Q U A S C A P E"):
            label.text="A Q U A S C A P E   V 4    /    水 草 微 流"
        if label.text.begins_with("拖动旋转"):
            label.text="拖动旋转 · 滚轮缩放 · 空格旋转视角 · P 暂停水草 · R 复位      1 材质   2 灰模   4 俯视"
    var groups: Array=find_children("*","HBoxContainer",true,false)
    if not groups.is_empty():
        flow_button=Button.new()
        flow_button.custom_minimum_size=Vector2(164,40)
        flow_button.pressed.connect(_toggle_current)
        groups[0].add_child(flow_button)
        _flow_label()

func _mode(value: int) -> void:
    super._mode(value)
    if is_instance_valid(mode_label):
        mode_label.text=["材质预览","动态灰模","映射格纹"][value]+" · 小水榕轻摆 / 爪哇蕨柔摆 · P 暂停对比"

func _flow_label() -> void:
    if is_instance_valid(flow_button):flow_button.text="水流：轻柔" if plant_current.running else "水流：暂停"

func _toggle_current() -> void:
    plant_current.running=not plant_current.running
    _flow_label()

func _unhandled_key_input(event: InputEvent) -> void:
    super._unhandled_key_input(event)
    if event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_P:_toggle_current()

func _pose_at(seconds: float) -> void:
    plant_current.apply_at(seconds)
    for i in 3:await get_tree().process_frame
    await RenderingServer.frame_post_draw

func _capture(directory: String) -> void:
    capture_active=true
    plant_current.running=false
    _flow_label()
    DirAccess.make_dir_recursive_absolute(directory)
    for i in 10:await get_tree().process_frame
    var paused_time: float=plant_current.current_time
    for i in 3:await get_tree().process_frame
    var pause_ok: bool=plant_current.current_time==paused_time
    _toggle_current()
    for i in 6:await get_tree().process_frame
    var resume_ok: bool=plant_current.current_time>paused_time
    _toggle_current()
    # Capture advances the native clip deterministically at its real timing.
    flow_button.text="水流：轻柔"
    var outputs: Array=[]
    var baseline: Array=[]
    var anchor_motion := 0.0
    var tip_motion: Dictionary={"anubias":0.0,"java_fern":0.0}
    var static_transforms: Array=[art_nodes.rock.global_transform,art_nodes.driftwood.global_transform]
    for frame in 41:
        await _pose_at(frame*.25)
        var probes: Array=plant_current.sample_probes()
        if frame==0:baseline=probes
        for j in probes.size():
            var p: Array=probes[j].position;var b: Array=baseline[j].position
            var distance: float=Vector3(p[0]-b[0],p[1]-b[1],p[2]-b[2]).length()
            if probes[j].anchor:anchor_motion=maxf(anchor_motion,distance)
            else:tip_motion[probes[j].id]=maxf(tip_motion[probes[j].id],distance)
    var views := [
        ["01-overview",0,.30,.30,1.16,Vector3(0,.24,0),2.5],
        ["02-plants-phase-a",0,.12,.15,.72,Vector3(-.36,.28,-.04),0.0],
        ["03-plants-phase-b",0,.12,.15,.72,Vector3(-.36,.28,-.04),2.5],
        ["04-plants-phase-c",0,.12,.15,.72,Vector3(-.36,.28,-.04),5.0],
        ["05-plants-phase-d",0,.12,.15,.72,Vector3(-.36,.28,-.04),7.5],
        ["06-gray",1,.30,.30,.72,Vector3(-.36,.28,-.04),5.0],
        ["07-back",0,PI+.25,.30,1.16,Vector3(0,.24,0),2.5],
        ["08-top",0,0,1.46,1.16,Vector3(0,.18,0),5.0]
    ]
    var failures: Array=plant_current.failures.duplicate()
    if not pause_ok or not resume_ok:failures.append("plant pause/resume control failed")
    for row in views:
        _mode(row[1]);yaw=row[2];pitch=row[3];view_size=row[4];target=row[5];_camera()
        await _pose_at(row[6])
        var path: String=directory+"/"+row[0]+".png"
        var err := get_viewport().get_texture().get_image().save_png(path)
        if err!=OK:failures.append("capture failed: "+path)
        outputs.append({"path":path,"time_s":row[6]})
    var frames_dir: String=directory+"/frames"
    DirAccess.make_dir_recursive_absolute(frames_dir)
    _mode(0);yaw=.12;pitch=.15;view_size=.72;target=Vector3(-.36,.28,-.04);_camera()
    for frame in 120:
        await _pose_at(frame/12.0)
        var err := get_viewport().get_texture().get_image().save_png(frames_dir+("/frame%04d.png" % frame))
        if err!=OK:failures.append("movie frame save failed")
    if anchor_motion>.000001:failures.append("native imported root probes move")
    if tip_motion.anubias<.0003 or tip_motion.java_fern<.003:failures.append("native imported leaf tips do not move enough")
    var static_unchanged: bool=static_transforms[0]==art_nodes.rock.global_transform and static_transforms[1]==art_nodes.driftwood.global_transform
    if not static_unchanged:failures.append("static scenery transforms changed")
    var data := {"schema_version":1,"command":"aquascape.plant-current-render","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","outputs":outputs,"failures":failures,"native_rigs":plant_current.rig_summary(),"native_probe_count":baseline.size(),"sampled_native_poses":41,"max_native_anchor_motion_m":anchor_motion,"max_native_tip_motion_from_phase_zero_m":tip_motion,"static_scenery_unchanged":static_unchanged,"pause_control_passed":pause_ok,"resume_control_passed":resume_ok,"video_frames":120,"video_fps":12,"visual_review":"pending","user_acceptance":"pending","scope":"Actual Godot native bones and skin, rendered across full loop. Probe sampling does not prove continuous leaf collision freedom."}
    var file := FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(data,"  "))
    print(JSON.stringify(data))
    get_tree().quit(0 if failures.is_empty() else 1)
