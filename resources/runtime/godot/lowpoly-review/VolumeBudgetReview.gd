extends "res://scripts/aquarium/lowpoly_review/LowPolyReview.gd"
## Reuses the tested root-viewport rotate/pan/cursor-zoom controls.
const STUDY="res://../plans/reviews/fish-volume-budget-v3"
const CONFIG="res://scripts/aquarium/lowpoly_review/volume-budget-study-v3.json"
var species_ids=["bluegill","zander","great_hammerhead","whale_shark"]
var settings={}
var species="bluegill"
var grid:GridContainer
var title_label:Label
var species_select:OptionButton
var action_select:OptionButton
var focus_part="whole"
var busy=false
var switch_records=[]
var camera_distance=2.0

func _ready() -> void:
    pan_mode=false
    settings=JSON.parse_string(FileAccess.get_file_as_string(CONFIG))
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--species="):species=arg.trim_prefix("--species=")
    assert(species in species_ids)
    DisplayServer.window_set_title("四种鱼减面对照 · 体积与数量预算实验")
    var background=ColorRect.new();background.color=Color("101e29");background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);background.mouse_filter=Control.MOUSE_FILTER_IGNORE;add_child(background)
    var margin=MarginContainer.new();margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    for side in ["left","right","top","bottom"]:margin.add_theme_constant_override("margin_"+side,12)
    add_child(margin)
    var layout=VBoxContainer.new();margin.add_child(layout)
    title_label=Label.new();title_label.add_theme_font_size_override("font_size",24);layout.add_child(title_label)
    var help=Label.new();help.text="左键旋转 · 右键/中键/Shift+左键平移 · 滚轮围绕指针缩放 · WASD/方向键平移 · 空格暂停";layout.add_child(help)
    var controls=HBoxContainer.new();layout.add_child(controls)
    species_select=OptionButton.new()
    for id in species_ids:species_select.add_item(settings.species[id].label)
    species_select.select(species_ids.find(species));species_select.item_selected.connect(func(index):load_species(species_ids[index]));controls.add_child(species_select)
    pause_button=button(controls,"暂停游动",toggle_pause)
    pan_button=button(controls,"左键平移模式",func():pan_mode=pan_button.button_pressed);pan_button.toggle_mode=true
    rotation_button=button(controls,"自动旋转：关",func():rotating=not rotating;rotation_button.text="自动旋转：开" if rotating else "自动旋转：关")
    action_select=OptionButton.new()
    for name in ["游动 Swim","转向 Turn","上浮 Ascend","下潜 Dive"]:action_select.add_item(name)
    action_select.item_selected.connect(func(index):
        for entry in entries:entry.controller.set_action(["Swim","Turn","Ascend","Dive"][index],true))
    controls.add_child(action_select)
    var views=HBoxContainer.new();layout.add_child(views)
    button(views,"整鱼",func():focus_part="whole";reset_view())
    button(views,"嘴/头近景",func():focus_part="head";reset_view())
    button(views,"尾鳍近景",func():focus_part="tail";reset_view())
    button(views,"侧面",func():yaw=0;pitch=0;update_cameras())
    button(views,"正面",func():yaw=PI/2;pitch=0;update_cameras())
    button(views,"俯视",func():yaw=0;pitch=1.5;update_cameras())
    button(views,"复位",reset_view)
    grid=GridContainer.new();grid.columns=2;grid.size_flags_vertical=Control.SIZE_EXPAND_FILL;layout.add_child(grid)
    status=Label.new();status.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;layout.add_child(status)
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    await load_species(species)
    if "--smoke-test" in OS.get_cmdline_user_args():await smoke_test()

func load_species(id:String) -> void:
    if busy:return
    busy=true;species_select.disabled=true
    entries.clear();cameras.clear();viewports.clear();panels.clear();initial_counts.clear()
    for child in grid.get_children():child.queue_free()
    factory.fish.clear();preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    await get_tree().process_frame
    species=id;focus_part="whole";yaw=0;pitch=0;pan=Vector3.ZERO;zoom=1;active_panel=-1;dragging=false;panning=false
    species_select.select(species_ids.find(species));action_select.select(0)
    var folder=STUDY.path_join(species)
    var source=JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("source.validation.json")))
    for path in source.inputs:assert(FileAccess.get_sha256(path)==source.inputs[path],"Baseline changed; rerun experiment before review: "+path)
    var budgets=[0];budgets.append_array(settings.species[species].whole_fish_triangle_budgets)
    var transport=preload("res://scripts/aquarium/lowpoly_review/LowPolyFishTransport.gd").new()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    title_label.text=settings.species[species].label+" · 标准体长 "+str(source.real_length_cm)+" cm · 原版与三档实验"
    for budget in budgets:
        var column=VBoxContainer.new();column.size_flags_horizontal=Control.SIZE_EXPAND_FILL;column.size_flags_vertical=Control.SIZE_EXPAND_FILL;grid.add_child(column)
        var label=Label.new();label.add_theme_font_size_override("font_size",18);column.add_child(label)
        var container=SubViewportContainer.new();container.stretch=true;container.size_flags_horizontal=Control.SIZE_EXPAND_FILL;container.size_flags_vertical=Control.SIZE_EXPAND_FILL;container.mouse_filter=Control.MOUSE_FILTER_STOP;column.add_child(container);panels.append(container)
        var viewport=SubViewport.new();viewport.own_world_3d=true;viewport.size=Vector2i(760,400);container.add_child(viewport);viewports.append(viewport)
        var world=Node3D.new();viewport.add_child(world)
        var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("183b4a");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.8;world.add_child(env)
        var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-30,0);world.add_child(light)
        var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=200;camera.current=true;world.add_child(camera);cameras.append(camera)
        factory._add_fish(world,species,float(source.real_length_cm)/100.,factory.profiles[species])
        var entry=factory.fish[-1];entry.player.pause();entry.carrier.transform=Transform3D.IDENTITY;entries.append(entry)
        if budget>0:
            var data=JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("low-"+str(int(budget))+".json")))
            assert(data.source_sha256==FileAccess.get_sha256(folder.path_join("source.validation.json")))
            transport.apply(entry.model,data)
        var total=0
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            if not mesh.is_visible_in_tree():continue
            for si in mesh.mesh.get_surface_count():total+=mesh.mesh.surface_get_arrays(si)[Mesh.ARRAY_INDEX].size()/3
        initial_counts.append({"budget":budget,"triangles":total})
        label.text=("原版" if budget==0 else "实验候选")+" · "+str(total)+" 三角面"
    status.text="左上原版，右上低档，左下中档，右下高档。同步相机与动作；小鱼鳍轮廓、嘴唇接头及鲨鱼头翼仍需局部修整。尚未替换正式鱼，也未完成鳍厚度/尾柄修复。"
    update_cameras();busy=false;species_select.disabled=false
    for frame in 8:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var screenshot=ProjectSettings.globalize_path(folder.path_join("interactive.png")).simplify_path()
    get_viewport().get_texture().get_image().save_png(screenshot)
    switch_records.append({"species":species,"counts":initial_counts.duplicate(true),"screenshot_sha256":FileAccess.get_sha256(screenshot)})
    save_record()
    print("VOLUME_REVIEW_READY ",species," ",initial_counts)

func update_cameras() -> void:
    if entries.is_empty():return
    var length_m=float(entries[0].length_m);var center=Vector3.ZERO;var size=length_m*.9
    if focus_part!="whole":
        var target=entries[0].model.find_child("Caudal" if focus_part=="tail" else "Source_lips139",true,false) as MeshInstance3D
        if target==null:target=entries[0].model.find_child("Cephalofoil",true,false) as MeshInstance3D
        var box=target.global_transform*target.get_aabb();center=box.get_center();size=maxf(box.size.length()*1.2,length_m*.08)
    center+=pan
    var direction=Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))
    camera_distance=maxf(length_m*3.,2.)
    for camera in cameras:
        camera.size=size*zoom;camera.position=center+direction*camera_distance;camera.look_at(center)

func cursor_world(position:Vector2,index:int) -> Vector3:
    var local=position-panels[index].get_global_rect().position
    var normalized=local/panels[index].size-Vector2(.5,.5)
    var camera=cameras[index];var height=camera.size
    var width=height*panels[index].size.x/panels[index].size.y
    return camera.position-camera.global_basis.z*camera_distance+camera.global_basis.x*normalized.x*width-camera.global_basis.y*normalized.y*height

func _process(delta:float) -> void:
    if busy:return
    super._process(delta)

func save_record():
    var directory=ProjectSettings.globalize_path(STUDY).simplify_path()
    var record={"schema_version":1,"accepted":false,"production_changed":false,"pid":OS.get_process_id(),"species":species,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"base_navigation_sha256":FileAccess.get_sha256("res://scripts/aquarium/lowpoly_review/LowPolyReview.gd"),"configuration_sha256":FileAccess.get_sha256(CONFIG),"switches":switch_records,"scope":"Interactive experimental recipe application, not a finalized/cold-load production model."}
    var f=FileAccess.open(directory.path_join("interactive.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(record,"  "));f.close()

func smoke_test():
    paused=true
    var tests=[]
    for id in species_ids:
        if species!=id:await load_species(id)
        var poses=[]
        for action in ["Swim","Turn","Ascend","Dive"]:
            for entry in entries:
                assert(entry.controller.set_action(action,true));entry.controller.step(0);entry.controller.seek(0)
                var before=[]
                for bi in entry.skeleton.get_bone_count():before.append(entry.skeleton.get_bone_pose(bi))
                entry.controller.seek(1.25);entry.carrier.transform=Transform3D.IDENTITY
                var after=[];var finite=true
                for bi in entry.skeleton.get_bone_count():
                    var pose=entry.skeleton.get_bone_pose(bi);after.append(pose);finite=finite and pose.origin.is_finite() and pose.basis.is_finite()
                assert(finite and var_to_bytes(before)!=var_to_bytes(after))
                poses.append({"action":action,"finite":finite,"changed":true})
        focus_part="head";update_cameras();focus_part="tail";update_cameras();focus_part="whole";reset_view()
        var initial_pan=pan;move_pan(Vector2(100,20),0);assert(pan!=initial_pan)
        var point=panels[0].get_global_rect().get_center();var anchor=cursor_world(point,0)
        cursor_zoom(point,0,.7);assert(anchor.distance_to(cursor_world(point,0))<.00001)
        tests.append({"species":species,"counts":initial_counts.duplicate(true),"action_pose_probes":poses,"pan_changed":true,"cursor_plane_anchor_stable":true})
    var f=FileAccess.open(ProjectSettings.globalize_path(STUDY).path_join("viewer-test.validation.json"),FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"tests":tests,"scope":"All species switched, four action two-time probes, focus/pan/zoom smoke check. Not full motion/contact acceptance."},"  "));f.close()
    get_tree().quit()
