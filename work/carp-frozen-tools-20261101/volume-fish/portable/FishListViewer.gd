extends "FishAssetViewer.gd"
## List wrapper around the frozen complete-GLB viewer; no asset writes/builders.
var catalog: Dictionary
var world: Node3D
var viewport: SubViewport
var fish_list: ItemList
var info: Label
var pause_button: Button
var action_choice: OptionButton
var selected_index := -1
var catalog_path := ""
var output_directory := ""
var sidebar_width := 245.0
var tracked_center := Vector3.ZERO

func run() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--catalog="):catalog_path=arg.trim_prefix("--catalog=")
    catalog=JSON.parse_string(FileAccess.get_file_as_string(catalog_path))
    assert(catalog.get("entries",[]).size()>0)
    output_directory=catalog.output;DirAccess.make_dir_recursive_absolute(output_directory)
    root.size=Vector2i(1320,820);root.title="新鱼预览 · 可切换列表"
    root.content_scale_size=Vector2i.ZERO;root.content_scale_mode=Window.CONTENT_SCALE_MODE_DISABLED;root.content_scale_factor=1.
    Engine.max_fps=60;root.window_input.connect(func(e: InputEvent):
        if e is InputEventKey:_input(e))
    root.close_requested.connect(_finish)
    set_auto_accept_quit(false)
    var theme:=Theme.new();var font:=SystemFont.new();font.font_names=PackedStringArray(["Microsoft YaHei","Noto Sans CJK SC"]);theme.default_font=font;theme.default_font_size=16
    var layout:=HBoxContainer.new();layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);layout.add_theme_constant_override("separation",0);layout.theme=theme;root.add_child(layout)
    var panel:=PanelContainer.new();panel.custom_minimum_size=Vector2(sidebar_width,0);layout.add_child(panel)
    var margin:=MarginContainer.new()
    for key in ["margin_left","margin_right","margin_top","margin_bottom"]:margin.add_theme_constant_override(key,14)
    panel.add_child(margin);var side:=VBoxContainer.new();side.add_theme_constant_override("separation",12);margin.add_child(side)
    var title:=Label.new();title.text="新鱼预览";title.add_theme_font_size_override("font_size",24);side.add_child(title)
    fish_list=ItemList.new();fish_list.custom_minimum_size=Vector2(216,180);fish_list.add_theme_constant_override("v_separation",12);side.add_child(fish_list)
    for entry in catalog.entries:fish_list.add_item(entry.label)
    fish_list.item_selected.connect(_select_fish)
    info=Label.new();info.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;info.custom_minimum_size.y=95;side.add_child(info)
    action_choice=OptionButton.new()
    for label in ["游动","转向","上浮","下潜"]:action_choice.add_item(label)
    action_choice.item_selected.connect(func(i: int):
        if controller!=null:controller.set_action(["Swim","Turn","Ascend","Dive"][i],true))
    side.add_child(action_choice)
    pause_button=_button(side,"暂停 / 继续",func():motion_paused=not motion_paused;_pause_label())
    var zoom_buttons:=HBoxContainer.new();side.add_child(zoom_buttons)
    _button(zoom_buttons,"＋ 放大",func():_zoom(.8));_button(zoom_buttons,"－ 缩小",func():_zoom(1.25))
    _button(side,"复位视角",func():_apply_camera({}))
    var views:=HBoxContainer.new();side.add_child(views)
    _button(views,"侧面",func():_view(0,0));_button(views,"正面",func():_view(90,0));_button(views,"俯视",func():_view(0,85))
    _button(side,"灰模 / 贴图",_toggle_gray)
    var filler:=Control.new();filler.size_flags_vertical=Control.SIZE_EXPAND_FILL;side.add_child(filler)
    var tips:=Label.new();tips.text="左键拖动：旋转\n右键拖动：平移\n鼠标滚轮：缩放\n空格：暂停 / 继续\n0：复位视角";tips.modulate=Color(.74,.80,.86);side.add_child(tips)
    var frame:=Control.new();frame.size_flags_horizontal=Control.SIZE_EXPAND_FILL;frame.size_flags_vertical=Control.SIZE_EXPAND_FILL;layout.add_child(frame)
    var box:=SubViewportContainer.new();box.stretch=true;box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);box.mouse_filter=Control.MOUSE_FILTER_IGNORE;frame.add_child(box)
    viewport=SubViewport.new();viewport.size=Vector2i(1075,820);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;box.add_child(viewport)
    var input_surface:=Control.new();input_surface.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);input_surface.mouse_filter=Control.MOUSE_FILTER_STOP;frame.add_child(input_surface)
    input_surface.gui_input.connect(func(e: InputEvent):
        var forwarded: InputEvent=e.duplicate()
        if forwarded is InputEventMouse:forwarded.position+=input_surface.global_position
        _input(forwarded))
    world=Node3D.new();viewport.add_child(world)
    camera_node=Camera3D.new();world.add_child(camera_node);camera_node.current=true;camera_node.fov=38
    var environment:=WorldEnvironment.new();environment.environment=Environment.new();environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("25343c");environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.8;world.add_child(environment)
    var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-35,0);light.light_energy=.8;world.add_child(light)
    fish_list.select(0);_select_fish(0)
    if catalog.get("mode","")=="smoke":await _catalog_smoke();_finish()

func _button(parent: Control,text: String,callback: Callable) -> Button:
    var button:=Button.new();button.text=text;button.pressed.connect(callback);button.size_flags_horizontal=Control.SIZE_EXPAND_FILL;parent.add_child(button);return button

func _select_fish(index: int) -> void:
    ready_for_input=false
    if controller!=null:controller=null
    if is_instance_valid(carrier):carrier.free()
    model=null;player=null;skeleton=null;meshes.clear();gray=false;elapsed=0;native_clip=""
    var entry: Dictionary=catalog.entries[index];config=entry.viewer.duplicate(true);config.mode="interactive";config.output=output_directory
    for path in config.input_paths:assert(FileAccess.get_sha256(path)==catalog.bindings[path],"Viewer input changed: "+path)
    var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file(config.model,state)==OK)
    model=doc.generate_scene(state);assert(model!=null)
    carrier=Node3D.new();world.add_child(carrier);carrier.add_child(model);model.scale=_v(config.model_scale);_collect(model);assert(not meshes.is_empty())
    inventory=_inventory();assert(inventory.mesh_count==int(config.inventory.mesh_count)and inventory.surface_count==int(config.inventory.surface_count))
    bounds=_world_bounds();camera_node.near=maxf(bounds.size.length()*.0005,.0001);camera_node.far=maxf(bounds.size.length()*100.,100.)
    base_distance=maxf(bounds.size.length()/(2.*tan(deg_to_rad(camera_node.fov*.5)))*1.15,.05);_apply_camera({});_start_native()
    if config.get("controller")!=null:_configure_controller()
    action_choice.select(0);_pause_label();selected_index=index;ready_for_input=true
    tracked_center=bounds.get_center()
    info.text=entry.label+"\n"+entry.status+"\n"+str(int(entry.triangles))+" 面 · "+str(entry.length_cm)+" cm"
    _check("loaded_"+str(entry.id),true)

func _advance(delta: float) -> void:
    super._advance(delta)
    var center: Vector3=_world_bounds().get_center()
    target+=center-tracked_center;tracked_center=center;_update_camera()

func _pause_label() -> void:pause_button.text="继续播放" if motion_paused else "暂停播放"
func _zoom(factor: float) -> void:
    distance=clampf(distance*factor,base_distance*.02,base_distance*30.);_update_camera()
func _view(yaw_degrees: float,pitch_degrees: float) -> void:
    _apply_camera({"yaw_degrees":yaw_degrees,"pitch_degrees":pitch_degrees})
func _input(event: InputEvent) -> bool:
    if event is InputEventMouse and event.position.x<sidebar_width:return false
    var result:=super._input(event)
    if is_instance_valid(pause_button):_pause_label()
    return result

func _catalog_smoke() -> void:
    await process_frame;await process_frame
    for i in catalog.entries.size():
        var rect: Rect2=fish_list.get_item_rect(i);var p: Vector2=fish_list.global_position+rect.get_center()
        var click:=InputEventMouseButton.new();click.position=p;click.global_position=p;click.button_index=MOUSE_BUTTON_LEFT;click.pressed=true;root.push_input(click);await process_frame
        click.pressed=false;root.push_input(click);await process_frame
        _check("list_click_"+str(i),selected_index==i)
        var old_pose:=_pose_signature()
        for step in 17:_advance(1./60.)
        _check("motion_"+str(i),old_pose!=_pose_signature())
        await _save_capture("fish-"+str(i))
    var center:=Vector2(850,410);var old_transform:=camera_node.transform
    var drag:=InputEventMouseMotion.new();drag.position=center;drag.global_position=center;drag.relative=Vector2(45,18);drag.button_mask=MOUSE_BUTTON_MASK_LEFT;root.push_input(drag);await process_frame
    _check("root_drag_rotates",not camera_node.transform.is_equal_approx(old_transform))
    var old_target:=target;drag.button_mask=MOUSE_BUTTON_MASK_RIGHT;root.push_input(drag);await process_frame;_check("root_drag_pans",not target.is_equal_approx(old_target))
    var old_distance:=distance;var wheel:=InputEventMouseButton.new();wheel.position=center;wheel.global_position=center;wheel.button_index=MOUSE_BUTTON_WHEEL_UP;wheel.pressed=true;root.push_input(wheel);await process_frame;_check("root_wheel_zooms",distance<old_distance)
    _check("inventory_kept",_inventory()==inventory)
    fish_list.select(0);_select_fish(0);await _save_capture("list-overview")

func _finish() -> void:
    if closing:return
    for path in catalog.bindings:_check("unchanged_"+str(path),FileAccess.get_sha256(path)==catalog.bindings[path])
    super._finish()
