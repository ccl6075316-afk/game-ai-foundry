extends "res://scripts/aquarium/AquascapeArtLab.gd"
## Data-driven native gallery; all visible prop paint is generated source artwork.
var entries: Array=[]
var plant_current
var bounds: Dictionary={}
var homes: Dictionary={}
var labels: Dictionary={}
var selected := -1
var page := 0
var auto_rotate := false
var capture_active := false
var selection_label: Label
var flow_button: Button
var prop_scales: Dictionary={}

func _ready() -> void:
    get_window().content_scale_size=Vector2i(1440,900)
    super._ready()
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--focus="):
            for i in entries.size():
                if entries[i].id==arg.trim_prefix("--focus="):_focus(i)
        if arg.begins_with("--prop-scale="):_resize_selected(float(arg.trim_prefix("--prop-scale=")))

func _catalog_entries() -> Array:
    return JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-v5/catalog.json")).assets

func _build() -> void:
    entries=_catalog_entries()
    DisplayServer.window_set_title("潮汐馆 · %d 种缸底置景" % entries.size())
    scenery=Node3D.new()
    world.add_child(scenery)
    plant_current=preload("res://scripts/aquarium/PlantCurrent.gd").new()
    add_child(plant_current)
    var gallery_rows: int=ceili(entries.size()/5.0)
    var gallery_depth: float=maxf(2.55,gallery_rows*.57+.3)
    _box(Vector3(0,-.028,0),Vector3(3.3,.05,gallery_depth),_solid(Color("344c48")))
    _box(Vector3(0,-.004,0),Vector3(3.25,.012,gallery_depth-.05),_solid(Color("857c61")))
    for i in entries.size():
        var row: Dictionary=entries[i]
        var model: Node3D=(load(row.model) as PackedScene).instantiate()
        model.name=row.id
        scenery.add_child(model)
        art_nodes[row.id]=model
        var box := AABB()
        var first := true
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            var local_box: AABB=model.global_transform.affine_inverse()*mesh.global_transform*mesh.get_aabb()
            box=local_box if first else box.merge(local_box)
            first=false
            var originals: Array=[]
            for surface in mesh.mesh.get_surface_count():
                var material: Material
                if not row.animated:
                    var mapped := ShaderMaterial.new()
                    mapped.shader=load("res://scripts/aquarium/ThreeViewArtwork.gdshader")
                    for view in ["front","right","top"]:
                        mapped.set_shader_parameter(view+"_art",load(row.material_dir+"/"+row.id+"-"+view+".png"))
                    var d: Dictionary=row.projection_bounds
                    mapped.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
                    material=mapped
                else:
                    var painted: StandardMaterial3D=mesh.get_active_material(surface).duplicate()
                    painted.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
                    painted.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
                    material=painted
                originals.append(material)
                mesh.set_surface_override_material(surface,material)
            art_originals[mesh]=originals
        bounds[row.id]=box
        var home := Vector3((i%5-2)*.62,.009-box.position.y,(float(i/5)-(gallery_rows-1)*.5)*.57)
        if row.get("deformation","")=="shader":home.y=.009
        homes[row.id]=home
        model.position=home
        var label := Label3D.new()
        label.text="%02d  %s" % [i+1,row.name_zh]
        label.font_size=36
        label.pixel_size=.0008
        label.billboard=BaseMaterial3D.BILLBOARD_ENABLED
        label.no_depth_test=true
        label.modulate=Color("ebe7d3")
        label.position=home+Vector3(0,-.004,.22)
        scenery.add_child(label)
        labels[row.id]=label
        if row.animated:
            if row.get("deformation","")=="shader":
                plant_current.attach_shader(row.id,model,row)
                for mesh in model.find_children("*","MeshInstance3D",true,false):
                    var originals: Array=[]
                    for surface in mesh.mesh.get_surface_count():originals.append(mesh.get_surface_override_material(surface))
                    art_originals[mesh]=originals
            else:plant_current.attach(row.id,model)
    plant_current.apply_at(0)
    _overview(0)

func _ui() -> void:
    var header := ColorRect.new()
    header.color=Color("0c2329")
    header.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
    header.offset_bottom=100
    header.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(header)
    _label(header,"A Q U A S C A P E   /   %d 种缸底置景" % entries.size(),Vector2(26,14),26,Color("e9dfc2"))
    selection_label=_label(header,"水草、石头与沉木 · 点击右侧逐件查看",Vector2(26,56),18,Color("b9d2c1"))
    var buttons := HBoxContainer.new()
    buttons.position=Vector2(775,25)
    header.add_child(buttons)
    for i in 3:
        var b := Button.new()
        b.text=["全部","水草","石木"][i]
        b.custom_minimum_size=Vector2(88,40)
        b.focus_mode=Control.FOCUS_NONE
        b.pressed.connect(func():_overview(i))
        buttons.add_child(b)
    var side := PanelContainer.new()
    side.position=Vector2(1130,104)
    side.size=Vector2(306,678)
    add_child(side)
    var scroll := ScrollContainer.new()
    side.add_child(scroll)
    var list := VBoxContainer.new()
    scroll.add_child(list)
    for i in entries.size():
        var b := Button.new()
        b.text="%02d  %s" % [i+1,entries[i].name_zh]
        b.alignment=HORIZONTAL_ALIGNMENT_LEFT
        b.custom_minimum_size=Vector2(280,31)
        b.focus_mode=Control.FOCUS_NONE
        b.pressed.connect(func():_focus(i))
        list.add_child(b)
    var footer := ColorRect.new()
    footer.color=Color("0c2329")
    footer.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
    footer.offset_top=-102
    footer.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(footer)
    _label(footer,"拖动旋转 · 滚轮拉近 · ＋／－ 素材倍率 · 空格旋转 · P 暂停 · R 总览 · ← → 切换",Vector2(26,12),17,Color("b4c9bb"))
    mode_label=_label(footer,"独立原画 / 侧视 / 俯视 · 原尺寸贴图 · 1 材质  2 灰模  4 俯视  5 背面",Vector2(26,45),16,Color("d6b77c"))
    flow_button=Button.new()
    flow_button.text="水流：轻柔"
    flow_button.position=Vector2(1175,18)
    flow_button.custom_minimum_size=Vector2(210,42)
    flow_button.focus_mode=Control.FOCUS_NONE
    flow_button.pressed.connect(_toggle_flow)
    footer.add_child(flow_button)

func _overview(value: int) -> void:
    selected=-1
    page=value
    var visible_index := 0
    for i in entries.size():
        var row: Dictionary=entries[i]
        var show_it: bool=value==0 or (value==1 and row.animated) or (value==2 and not row.animated)
        prop_scales[row.id]=1.0
        art_nodes[row.id].scale=Vector3.ONE
        art_nodes[row.id].visible=show_it
        labels[row.id].visible=show_it
        if not show_it:continue
        var at: Vector3=homes[row.id]
        if value!=0:at.z=(visible_index/5-.5)*.62
        art_nodes[row.id].position=at
        labels[row.id].position=at+Vector3(0,-.004,.22)
        visible_index+=1
    yaw=.07;pitch=1.02;view_size=2.85 if value==0 else 2.35
    target=Vector3(.30,.13,0)
    if is_instance_valid(selection_label):selection_label.text=["%d种水草 · %d种石木造景" % [entries.filter(func(r):return r.animated).size(),entries.filter(func(r):return not r.animated).size()],"水草 · 点击右侧查看名称、学名与独立模型","石头与木材 · 独立三向原画贴图"][value]
    _camera()

func _focus(index: int) -> void:
    selected=posmod(index,entries.size())
    var row: Dictionary=entries[selected]
    for entry in entries:
        art_nodes[entry.id].visible=entry.id==row.id
        labels[entry.id].visible=false
    art_nodes[row.id].position=Vector3.ZERO
    var box: AABB=bounds[row.id]
    var factor: float=prop_scales.get(row.id,1.0)
    view_size=maxf(.04,maxf(box.size.y,box.size.x)*1.65*factor)
    target=box.get_center()*factor+Vector3(view_size*.10,0,0)
    yaw=.25;pitch=.22
    if is_instance_valid(selection_label):selection_label.text=row.name_zh+"   /   "+row.get("scientific_name","静态石木素材")+"   · 素材 %.2f×" % factor
    _camera()

func _resize_selected(factor: float) -> void:
    if selected<0:return
    var row: Dictionary=entries[selected]
    factor=clampf(factor,.125,4.0)
    prop_scales[row.id]=factor
    art_nodes[row.id].scale=Vector3.ONE*factor
    target=bounds[row.id].get_center()*factor+Vector3(view_size*.10,0,0)
    selection_label.text=row.name_zh+"   /   "+row.get("scientific_name","静态石木素材")+"   · 素材 %.2f×" % factor
    _camera()

func _toggle_flow() -> void:
    plant_current.running=not plant_current.running
    if is_instance_valid(flow_button):flow_button.text="水流：轻柔" if plant_current.running else "水流：暂停"

func _input_view(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        if event.button_index==MOUSE_BUTTON_LEFT:dragging=event.pressed
        if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_UP:view_size=maxf(.02,view_size*.9)
        if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_DOWN:view_size=minf(5,view_size*1.1)
    if event is InputEventMouseMotion and dragging:
        yaw-=event.relative.x*.007
        pitch=clampf(pitch+event.relative.y*.005,-.1,1.52)
    _camera()

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo:return
    match event.keycode:
        KEY_1:_mode(0)
        KEY_2:_mode(1)
        KEY_3:_mode(2)
        KEY_4:pitch=1.49
        KEY_5:yaw=PI+.25;pitch=.22
        KEY_R:_overview(page)
        KEY_P:_toggle_flow()
        KEY_SPACE:auto_rotate=not auto_rotate
        KEY_RIGHT:_focus(selected+1)
        KEY_LEFT:_focus(selected-1)
        KEY_EQUAL,KEY_PLUS,KEY_KP_ADD:
            if selected>=0:_resize_selected(prop_scales.get(entries[selected].id,1.0)*2.0)
        KEY_MINUS,KEY_KP_SUBTRACT:
            if selected>=0:_resize_selected(prop_scales.get(entries[selected].id,1.0)*.5)
    _camera()

func _process(delta: float) -> void:
    if auto_rotate and not dragging and not capture_active:
        yaw+=delta*.22
        _camera()

func _settle(t: float) -> void:
    plant_current.apply_at(t)
    for i in 3:await get_tree().process_frame
    await RenderingServer.frame_post_draw

func _capture(directory: String) -> void:
    capture_active=true
    plant_current.running=false
    DirAccess.make_dir_recursive_absolute(directory)
    for i in 12:await get_tree().process_frame
    var failures: Array=plant_current.failures.duplicate()
    var paused_time: float=plant_current.current_time
    for i in 3:await get_tree().process_frame
    var pause_ok: bool=plant_current.current_time==paused_time
    _toggle_flow()
    for i in 6:await get_tree().process_frame
    var resume_ok: bool=plant_current.current_time>paused_time
    _toggle_flow()
    var baseline: Array=[]
    var root_motion := 0.0
    var tip_motion: Dictionary={}
    for row in entries:
        if row.animated and row.get("deformation","")!="shader":tip_motion[row.id]=0.0
    for frame in 41:
        await _settle(frame*.25)
        var probes: Array=plant_current.sample_probes()
        if frame==0:baseline=probes
        for j in probes.size():
            var p: Array=probes[j].position
            var b: Array=baseline[j].position
            var d: float=Vector3(p[0]-b[0],p[1]-b[1],p[2]-b[2]).length()
            if probes[j].anchor:root_motion=maxf(root_motion,d)
            else:tip_motion[probes[j].id]=maxf(tip_motion[probes[j].id],d)
    if root_motion>.000002:failures.append("native root probes moved")
    for id in tip_motion:
        if tip_motion[id]<.0003:failures.append(id+": no visible native leaf motion")
    if not pause_ok or not resume_ok:failures.append("pause/resume failed")
    # Players can place the same asset at arbitrary headings. Check imported
    # skin roots after relocation and four rotations, rather than one staging.
    var placement_base: Dictionary={}
    for row in entries:
        if row.animated:placement_base[row.id]=art_nodes[row.id].global_transform
    var placement_error := 0.0
    for heading in 4:
        for id in placement_base:
            art_nodes[id].global_transform=Transform3D(Basis(Vector3.UP,heading*PI/2),Vector3(.13,0,.07))*placement_base[id]
        await _settle(heading*2.5)
        var moved: Array=plant_current.sample_probes()
        for j in moved.size():
            if not moved[j].anchor:continue
            var p: Array=moved[j].position
            var b: Array=baseline[j].position
            var delta: Transform3D=art_nodes[moved[j].id].global_transform*placement_base[moved[j].id].affine_inverse()
            var expected: Vector3=delta*Vector3(b[0],b[1],b[2])
            placement_error=maxf(placement_error,expected.distance_to(Vector3(p[0],p[1],p[2])))
    for id in placement_base:art_nodes[id].global_transform=placement_base[id]
    if placement_error>.000002:failures.append("relocated/rotated plant root probes drift")
    var outputs: Array=[]
    for category in 3:
        _overview(category);_mode(0)
        await _settle(2.5)
        var path: String=directory+"/overview-%s.png" % category
        if get_viewport().get_texture().get_image().save_png(path)!=OK:failures.append(path)
        outputs.append(path)
    for i in entries.size():
        for view in ["front","right","back","top","gray"]:
            _focus(i);_mode(1 if view=="gray" else 0)
            if view=="right":yaw=PI/2;pitch=.12
            if view=="back":yaw=PI+.25
            if view=="top":yaw=0;pitch=1.49
            _camera()
            await _settle(2.5)
            var path: String=directory+"/"+entries[i].id+"-"+view+".png"
            if get_viewport().get_texture().get_image().save_png(path)!=OK:failures.append(path)
            outputs.append(path)
        if entries[i].animated:
            _focus(i);_mode(0)
            await _settle(7.5)
            var phase_path: String=directory+"/"+entries[i].id+"-phase-b.png"
            if get_viewport().get_texture().get_image().save_png(phase_path)!=OK:failures.append(phase_path)
            outputs.append(phase_path)
    _overview(1);_mode(0)
    var frames_dir: String=directory+"/frames"
    DirAccess.make_dir_recursive_absolute(frames_dir)
    for frame in 120:
        await _settle(frame/12.0)
        if get_viewport().get_texture().get_image().save_png(frames_dir+"/frame%04d.png" % frame)!=OK:failures.append("frame capture")
    _focus(7);_mode(0)
    flow_button.text="水流：轻柔（回放）"
    var detail_dir: String=directory+"/detail-frames"
    DirAccess.make_dir_recursive_absolute(detail_dir)
    for frame in 120:
        await _settle(frame/12.0)
        if get_viewport().get_texture().get_image().save_png(detail_dir+"/frame%04d.png" % frame)!=OK:failures.append("detail frame capture")
    var data := {"schema_version":1,"command":"aquascape.catalog-native-render","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","outputs":outputs,"failures":failures,"counts":{"all":entries.size(),"animated_plants":tip_motion.size()},"native_rigs":plant_current.rig_summary(),"native_probe_count":baseline.size(),"sampled_poses":41,"max_native_root_motion_m":root_motion,"native_tip_motion_m":tip_motion,"pause_passed":pause_ok,"resume_passed":resume_ok,"video_frames":120,"video_fps":12,"visual_review":"pending","user_acceptance":"pending","scope":"Actual Godot import, native skinning, five rendered angles per asset. Sampled probes do not prove continuous collision freedom or exact source reconstruction."}
    var file := FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    data["player_placement_check"]={"headings_degrees":[0,90,180,270],"relocated":true,"max_root_transform_error_m":placement_error,"scope":"Asset root/skin behavior under placement transforms; no placement UI or collision test."}
    file.store_string(JSON.stringify(data,"  "))
    print(JSON.stringify(data))
    get_tree().quit(0 if failures.is_empty() else 1)
