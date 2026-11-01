extends SceneTree
const Hall=preload("res://scripts/aquarium/AquariumHall3D.gd")
const Prop=preload("res://scripts/aquarium/editor/PropTransform.gd")
var hall
var directory := ""
var checks: Dictionary={}
var outputs: Array=[]
var last_mouse := Vector2.ZERO
func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--report-dir="):directory=arg.trim_prefix("--report-dir=")
    if directory.is_empty():quit(2);return
    DirAccess.make_dir_recursive_absolute(directory);call_deferred("run")
func check(id: String,value: bool) -> void:checks[id]=value;print("BUILD_CHECK ",id," ",value)
func same(a: Variant,b: Variant) -> bool:
    if (a is int or a is float) and (b is int or b is float):return absf(float(a)-float(b))<.0000000001
    if a is Dictionary and b is Dictionary:
        if a.size()!=b.size():return false
        for k in a:
            if not b.has(k) or not same(a[k],b[k]):return false
        return true
    if a is Array and b is Array:
        if a.size()!=b.size():return false
        for i in a.size():
            if not same(a[i],b[i]):return false
        return true
    return a==b
func settle() -> void:
    for i in 8:await process_frame
    await RenderingServer.frame_post_draw
func capture(name_value: String) -> void:
    await settle();var path := directory+"/"+name_value+".png"
    check("image_"+name_value,root.get_texture().get_image().save_png(path)==OK);outputs.append(path)
func pointer(at: Vector2,pressed: bool=false,button:=false) -> void:
    Input.warp_mouse(at)
    if button:
        var event := InputEventMouseButton.new();event.position=at;event.global_position=at;event.button_index=MOUSE_BUTTON_LEFT;event.pressed=pressed;Input.parse_input_event(event)
    else:
        var event := InputEventMouseMotion.new();event.position=at;event.global_position=at;event.relative=at-last_mouse;last_mouse=at;event.button_mask=MOUSE_BUTTON_MASK_LEFT if pressed else 0;Input.parse_input_event(event)
func drag_card(card: Control,to: Vector2) -> void:
    var start: Vector2=card.get_global_rect().get_center()
    pointer(start);await settle();pointer(start,true,true);await process_frame
    pointer(start+Vector2(-22,0),true);await settle()
    check("native_gui_drag_started_"+str(checks.size()),root.gui_is_dragging())
    pointer(to,true);await settle();pointer(to,false,true);await settle()
func handle_drag(owner_value,gizmo,from: Vector2,to: Vector2) -> void:
    var click := InputEventMouseButton.new();click.position=from;click.button_index=MOUSE_BUTTON_LEFT;click.pressed=true
    owner_value.canvas.gui_input.emit(click)
    var motion := InputEventMouseMotion.new();motion.position=to;owner_value.canvas.gui_input.emit(motion)
    click.pressed=false;click.position=to;owner_value.canvas.gui_input.emit(click)
    await settle()
func run() -> void:
    hall=Hall.new();hall.save_path=directory+"/not-player-save.json";hall.read_only=true;root.add_child(hall)
    var initial: Dictionary=hall._state();await settle()
    var bridge=hall.build_editor;var palette=bridge.palette
    for frame in 100:
        if bridge.thumbnails.complete:break
        await process_frame
    check("thumbnail_render_does_not_edit_document",hall._state()==initial)
    check("hall_catalog_is_bottom",palette.position.y>700 and palette.size.x>1800)
    check("hall_inspector_is_right",bridge.inspector.position.x>1500 and not bridge.inspector.get_rect().intersects(palette.get_rect()))
    check("hall_asset_thumbnails_ready",bridge.thumbnails.complete and palette.entries.all(func(item):return item.get("preview") is Texture2D))
    palette.tabs.current_tab=1;await settle()
    check("bottom_category_tabs_filter",palette.cards.get_child_count()==3)
    palette.tabs.current_tab=0;await settle()
    check("hall_uses_shared_palette",palette.scope=="hall" and palette.entries.size()==8)
    palette.search.text=palette.entries[6].label;palette.search.text_changed.emit(palette.search.text);await settle();check("search_filters_cards",palette.cards.get_child_count()==1)
    var count: int=hall.objects.size()
    await drag_card(palette.cards.get_child(0),hall.editor_camera.unproject_position(Vector3(3,0,2.7)))
    check("real_palette_drag_creates_hall_furniture",hall.objects.size()==count+1)
    palette.search.text="";palette.search.text_changed.emit("");bridge.set_mode("move");await settle()
    # Select an existing bench, then use actual projected handle events.
    hall.selected=2;bridge.tick();var before: Dictionary=hall._state();var history_size: int=hall.edit_history.past.size()
    var g=bridge.gizmo;var a: Vector2=g.project(g.pivot+Vector3.RIGHT*g.length_world*.7)
    await handle_drag(hall,g,a,a+Vector2(25,0))
    check("hall_move_handle_changes_document",hall._state()!=before)
    check("one_drag_one_history_entry",hall.edit_history.past.size()==history_size+1)
    hall._undo();check("hall_drag_single_undo",hall._state()==before);hall._redo()
    hall.selected=2;bridge.tick();before=hall._state();history_size=hall.edit_history.past.size()
    bridge.start();g.dragging=true;bridge.change(Transform3D(Basis.IDENTITY,Vector3(80,0,80)));g.dragging=false;bridge.finish(false)
    check("hall_out_of_bounds_keeps_document",hall._state()==before and hall.edit_history.past.size()==history_size)
    await capture("01-hall-building-palette")
    hall.selected=0;hall._open_water_panel();await settle()
    check("water_settings_are_right_context",hall.water_panel.position.x>1500 and not bridge.inspector.visible and not hall.side.visible)
    check("water_settings_clear_bottom_catalog",hall.water_panel.get_rect().end.y<=palette.position.y)
    await capture("04-right-water-properties")
    hall.water_panel.hide();await settle()
    hall.selected=0;check("open_real_tank_editor",hall._open_content_editor());await settle()
    var editor=hall.active_editor;var tb=editor.build_editor
    check("tank_catalog_is_bottom",tb.palette.position.y>700 and tb.palette.size.x>=1440)
    check("tank_inspector_is_right",tb.inspector.position.x>1100 and not tb.inspector.get_rect().intersects(tb.palette.get_rect()))
    check("tank_catalog_has_source_thumbnails",tb.palette.entries.all(func(item):return item.get("preview") is Texture2D))
    check("tank_reuses_identical_palette_class",tb.palette.get_script()==palette.get_script())
    for item in tb.palette.entries:
        if item.id=="river_boulder":tb.palette.search.text=item.label
    tb.palette.search.text_changed.emit(tb.palette.search.text);await settle()
    check("tank_catalog_search",tb.palette.cards.get_child_count()>0)
    count=editor.rocks.size()
    var drop: Vector2=editor.get_global_transform_with_canvas()*editor.camera.unproject_position(Vector3(.30,.03,.13))
    await drag_card(tb.palette.cards.get_child(0),drop)
    check("real_palette_drag_creates_tank_prop",editor.rocks.size()==count+1)
    editor.selected=editor.rocks.size()-1;editor._set_tool("select");tb.set_mode("move");await settle()
    g=tb.gizmo;var position_before: Vector3=editor.rocks[-1].node.position
    a=g.project(g.pivot+Vector3.UP*g.length_world*.75)
    await handle_drag(editor,g,a,a+Vector2(0,-35))
    check("tank_y_handle_lifts_object",editor.rocks[-1].node.position.y>position_before.y+.005)
    var lifted: Dictionary=editor._state();check("full_transform_serialized",lifted.rocks[-1].has("rotation") and lifted.rocks[-1].has("stretch"))
    check("right_inspector_tracks_selected_asset",tb.inspector.title.text==editor.rock_specs[editor.rocks[-1].id].name_zh and not tb.inspector.measurements.text.is_empty())
    editor._undo();check("tank_single_undo_restores_height",absf(editor.rocks[-1].node.position.y-position_before.y)<.00001)
    editor._redo();editor._set_tool("select");await settle()
    check("tank_redo_restores_full_transform",editor._state()==lifted)
    tb.set_mode("rotate");await settle();g=tb.gizmo
    a=g.project(g.ring_point(0,.7));var b: Vector2=g.project(g.ring_point(0,1.0))
    var old_rotation: Vector3=editor.rocks[-1].node.rotation
    await handle_drag(editor,g,a,b)
    check("three_ring_x_rotation_changes_pose",editor.rocks[-1].node.rotation.distance_to(old_rotation)>.02)
    await capture("02-tank-rotation-rings")
    tb.set_mode("scale");await settle();g=tb.gizmo
    a=g.project(g.pivot+g.direction(0)*g.length_world)
    var old_scale: Vector3=editor.rocks[-1].node.scale
    await handle_drag(editor,g,a,a+Vector2(14,0))
    check("axis_cube_changes_x_scale",absf(editor.rocks[-1].node.scale.x-old_scale.x)>.005)
    check("axis_cube_preserves_other_scales",absf(editor.rocks[-1].node.scale.y-old_scale.y)<.00001 and absf(editor.rocks[-1].node.scale.z-old_scale.z)<.00001)
    await capture("03-tank-scale-cubes")
    var valid: Dictionary=editor._state();var undo_count: int=editor.history.size()
    tb.start();var illegal: Transform3D=editor.rocks[-1].node.transform;illegal.origin.y=8;tb.change(illegal);tb.finish(false)
    check("tank_invalid_height_rejected",editor._state()==valid and editor.history.size()==undo_count)
    tb.set_mode("move");await settle();tb.start()
    var changed: Transform3D=editor.rocks[-1].node.transform;changed.origin.x-=.01;tb.change(changed);tb.finish(true);editor._set_tool("select")
    check("cancel_restores_without_history",editor._state()==valid and editor.history.size()==undo_count)
    check("hall_validator_accepts_extended_content",hall._valid_content(valid))
    var invalid := valid.duplicate(true);invalid.rocks[-1].stretch=[1,NAN,1]
    check("nonfinite_stretch_rejected",not hall._valid_content(invalid))
    invalid=valid.duplicate(true);invalid.rocks[-1].rotation=[0,INF,0]
    check("nonfinite_rotation_rejected",not hall._valid_content(invalid))
    tb.palette.search.text="";tb.palette.search.text_changed.emit("");tb.palette.tabs.current_tab=0;await settle()
    check("bottom_cards_form_horizontal_strip",tb.palette.cards.get_child(1).position.x>tb.palette.cards.get_child(0).position.x and tb.palette.cards.get_child(0).position.y==tb.palette.cards.get_child(1).position.y)
    await capture("05-bottom-catalog-and-properties")
    editor.apply_requested.emit(valid);await settle()
    check("apply_returns_to_hall",hall.active_editor==null)
    var content: Dictionary=hall.objects[0].data.content
    check("applied_transform_preserved",content==valid)
    var rendered: Node3D=hall.objects[0].tank.props[-1].node
    check("runtime_full_rotation",rendered.rotation.distance_to(Prop.vector(valid.rocks[-1].rotation))<.0001)
    check("runtime_axis_scale",rendered.scale.distance_to(Prop.vector(valid.rocks[-1].stretch)*5)<.0001)
    check("save_extended_hall",hall._write_layout(directory+"/hall-layout.json"))
    hall._undo();hall._redo();check("hall_history_preserves_transform",hall.objects[0].data.content==valid)
    check("cold_load_file_valid",hall._load_layout(directory+"/hall-layout.json"))
    check("cold_load_extended_hall",same(hall.objects[0].data.content,valid))
    hall.selected=0;hall._open_content_editor();await settle()
    editor=hall.active_editor;check("reopen_editor_preserves_full_transform",editor._state()==valid)
    editor.cancel_requested.emit();await settle()
    check("cancel_editor_preserves_hall",same(hall.objects[0].data.content,valid))
    check("readonly_player_save_untouched",not FileAccess.file_exists(hall.save_path))
    var okay := not checks.values().has(false)
    var file=FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"schema_version":1,"ok":okay,"checks":checks,"outputs":outputs,"user_acceptance":"pending"},"  "));file.close()
    hall.queue_free()
    for i in 4:await process_frame
    print("BUILD_REVIEW ",okay," ",checks.size());quit(0 if okay else 1)
