extends Control
## Editable hall host for both standalone trials and the shared game inventory.
signal return_requested
const LayoutStore=preload("res://scripts/aquarium/hall/HallLayoutStore.gd")
const WalkController=preload("res://scripts/aquarium/hall/HallWalkController.gd")
var layout_rules=preload("res://scripts/aquarium/hall/HallLayoutRules.gd").new()
var document=preload("res://scripts/aquarium/hall/HallLayoutDocument.gd").new()
var build_commands: RefCounted
var scene_projection: RefCounted
var save_path := "user://aquarium-hall-3d-preview-v1.json"
@export var start_empty := false
@export_file("*.json") var starter_layout := ""
var read_only := false
var viewport: SubViewport
var world: Node3D
var canvas: TextureRect
var player: CharacterBody3D
var eye: Camera3D
var editor_camera: Camera3D
var objects: Array=[]
var selected := -1
var editing := true
var looking := false
var yaw := .48
var pitch := .83
var highest_shell_top := 0.0
var view_size := 20.5
var camera_target := Vector3(1.8,1.0,-.6)
var pointer := Vector2.ZERO
var notice := "自由布展：先单击选中，再按住物件拖动，Q/E 旋转；Tab 切换逛馆。"
var floor_style: int:
    get:return document.style("floor_style")
    set(value):document.set_style_for_legacy_review("floor_style",value)
var wall_style: int:
    get:return document.style("wall_style")
    set(value):document.set_style_for_legacy_review("wall_style",value)
var floor_paint: ShaderMaterial
var wall_paint: StandardMaterial3D
var hall_lighting
var water_renderer
var pixel_materials := true
var surface_materials: Array=[]
var surface_art: Dictionary={}
const HALL_ART := "res://assets/aquarium-hall-style-v3/"
var visitor_crowd
var edit_history=preload("res://scripts/aquarium/hall/HallEditHistory.gd").new()
var history: Array:
    get:return edit_history.past
var future: Array:
    get:return edit_history.future
var saved_digest := ""
const Footprint = preload("res://scripts/aquarium/HallFootprint.gd")
var parcels: Array:
    get:return document.parcels()
var room_geometry: Node3D
const Storeys=preload("res://scripts/aquarium/hall/HallStoreys.gd")
var active_level := 0
var highest_level := 0
var floor_views: Dictionary={}
var floor_cells: Dictionary={}
var visible_objects: Array=[]
var show_lower_life := false
const MAX_OBJECTS := 80
const MAX_TANKS := 8
const FLOOR_COLORS := [Color("778d8b"),Color("b4b5a5"),Color("4c626d")]
const WALL_COLORS := [Color("d4d6c5"),Color("8daaad"),Color("b1b3a0")]

var build_editor: RefCounted
var editor: RefCounted
var panel := preload("res://scripts/aquarium/hall/HallEditorPanel.gd").new()
var tank_session: RefCounted

func _ready() -> void:
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    mouse_filter=Control.MOUSE_FILTER_IGNORE
    _register_input()
    viewport=SubViewport.new();viewport.size=Vector2i(1920,1080);viewport.own_world_3d=true
    viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    add_child(viewport)
    world=Node3D.new();viewport.add_child(world)
    canvas=preload("res://scripts/aquarium/editor/BuildDropCanvas.gd").new();canvas.texture=viewport.get_texture()
    canvas.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;canvas.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    canvas.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    canvas.gui_input.connect(_canvas_input);add_child(canvas)
    build_commands=preload("res://scripts/aquarium/hall/HallBuildCommands.gd").new(document,layout_rules,edit_history)
    editor=preload("res://scripts/aquarium/hall/HallEditorController.gd").new(self)
    tank_session=preload("res://scripts/aquarium/hall/HallTankSession.gd").new(self)
    _room()
    _player()
    tank_session.create_camera(world)
    add_child(panel)
    panel.build(self)
    build_editor=preload("res://scripts/aquarium/editor/BuildEditorBridge.gd").new();build_editor.setup(self,false)
    visitor_crowd=preload("res://scripts/aquarium/visitors/HallVisitorCrowd.gd").new()
    if start_empty:
        save_path="user://aquarium-empty-hall-trial-v1.json"
        if not starter_layout.is_empty():
            save_path="user://"+starter_layout.get_file()
        visitor_crowd.requested_count=0
        panel.visitor_spin.set_value_no_signal(0)
    world.add_child(visitor_crowd)
    _restore(_default_state())
    _mode(true)
    saved_digest=JSON.stringify(_state()).sha256_text()
    if start_empty and not starter_layout.is_empty():
        _load_layout(save_path if FileAccess.file_exists(save_path) else starter_layout)
    elif not start_empty and (not session_layout.is_empty() or FileAccess.file_exists(save_path)):
        if not _load_layout(save_path):notice="大厅存档无效，已保留默认布局。"
    if not visitor_crowd.resources_ready:notice="游客暂不可用："+visitor_crowd.resource_error
    _sync_panel()
    DisplayServer.window_set_title("潮汐馆 · 可编辑 3D 大厅")

var warehouse_linked:=false
var warehouse: Dictionary={}

var session_layout:=""
var session_has_slot:=true
var save_session_layout:Callable

func configure_warehouse(items: Dictionary,layout: String,save_callback: Callable,has_slot:=true) -> void:
    session_has_slot=has_slot
    session_layout=layout
    save_session_layout=save_callback
    warehouse=items.duplicate()
    warehouse_linked=true

func configure_save(path: String,writable: bool=true) -> void:
    save_path=path;read_only=not writable

func _register_input() -> void:
    for pair in [["hall_left",KEY_A],["hall_right",KEY_D],["hall_forward",KEY_W],["hall_back",KEY_S]]:
        if InputMap.has_action(pair[0]):continue
        InputMap.add_action(pair[0])
        var event := InputEventKey.new();event.physical_keycode=pair[1]
        InputMap.action_add_event(pair[0],event)

func _paint(color: Color,unshaded:=false) -> StandardMaterial3D:
    var m := StandardMaterial3D.new();m.albedo_color=color;m.roughness=1;m.metallic_specular=0
    if unshaded:m.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    return m

func _surface(color: Color,art: String,art_tint: Color=Color.TRANSPARENT) -> StandardMaterial3D:
    var m := _paint(color)
    if not surface_art.has(art):surface_art[art]=load(HALL_ART+art+".png")
    m.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST_WITH_MIPMAPS
    m.uv1_triplanar=true;m.uv1_world_triplanar=true;m.uv1_scale=Vector3.ONE*.5
    m.uv1_triplanar_sharpness=32
    m.set_meta("hall_art",art);m.set_meta("plain_color",color)
    m.set_meta("art_tint",color if art_tint==Color.TRANSPARENT else art_tint)
    surface_materials.append(weakref(m))
    if pixel_materials:m.albedo_texture=surface_art[art];m.albedo_color=m.get_meta("art_tint")
    return m

func _set_pixel_materials(enabled: bool) -> void:
    # The plain branch exists for matched review captures, not a saved layout setting.
    pixel_materials=enabled;floor_paint.set_shader_parameter("use_artwork",enabled)
    surface_materials=surface_materials.filter(func(ref):return ref.get_ref()!=null)
    for ref in surface_materials:
        var m: StandardMaterial3D=ref.get_ref()
        m.albedo_texture=surface_art[m.get_meta("hall_art")] if enabled else null
        m.albedo_color=m.get_meta("art_tint" if enabled else "plain_color")
    _finishes()

func _box(parent: Node3D,at: Vector3,size: Vector3,paint: Material) -> MeshInstance3D:
    return scene_projection._box(parent,at,size,paint)

func _room() -> void:
    hall_lighting=load("res://scripts/aquarium/HallLighting.gd").new();world.add_child(hall_lighting)
    water_renderer=load("res://scripts/aquarium/TankWaterRenderer.gd").new();world.add_child(water_renderer)
    floor_paint=ShaderMaterial.new();floor_paint.shader=load("res://scripts/aquarium/HallFloor3D.gdshader")
    floor_paint.set_shader_parameter("floor_art",load(HALL_ART+"hall_floor.png"))
    wall_paint=_surface(WALL_COLORS[0],"hall_wall")
    scene_projection=preload("res://scripts/aquarium/hall/HallSceneProjection.gd").new(world,layout_rules,_surface,hall_lighting)
    _rebuild_room()
    editor_camera=Camera3D.new();editor_camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    editor_camera.near=.04;editor_camera.far=100;world.add_child(editor_camera)
    editor.create_preview_nodes()

func _clear_geometry(node: Node3D) -> void:
    scene_projection._clear_geometry(node)

func _rebuild_room() -> void:
    scene_projection.exterior_options=preload("hall/HallExteriorWall.gd").settings(_state())
    scene_projection.rebuild_room(parcels,editing,floor_paint,wall_paint)
    room_geometry=scene_projection.room_geometry
    editor._refresh_parcel_hints()

func _player() -> void:
    player=CharacterBody3D.new();player.collision_layer=4;player.collision_mask=3;world.add_child(player)
    var collision := CollisionShape3D.new();var capsule := CapsuleShape3D.new();capsule.radius=.24;capsule.height=1.7
    collision.shape=capsule;player.add_child(collision)
    player.position=Vector3(0,.88,3.2)
    eye=Camera3D.new();eye.position.y=.74;eye.fov=68;eye.near=.04;eye.far=70;player.add_child(eye)

func _default_state() -> Dictionary:
    return {"schema_version":1,"floor_style":0,"wall_style":0,"objects":[]}

func _bounds(data: Dictionary) -> AABB:
    return layout_rules._bounds(data)

func _transform(data: Dictionary) -> Transform3D:
    return layout_rules._transform(data)

func _create(data: Dictionary) -> Dictionary:
    return scene_projection._create(data)

func _state() -> Dictionary:
    return document.snapshot()

func _restore(state: Dictionary) -> void:
    if not document.replace(state,layout_rules):notice="布局无效，当前场景保持不变。";return
    _apply_document(true)

func _apply_document(reset_selection: bool=false,change: Dictionary={}) -> void:
    var kind: String=change.get("kind","")
    var layout := _state()
    var wall_finish_changed: bool=scene_projection.default_wall_finish!=int(layout.get("wall_finish",0))
    scene_projection.default_wall_finish=int(layout.get("wall_finish",0))
    if reset_selection or kind in ["expand","exterior"] or wall_finish_changed:_rebuild_room()
    if reset_selection or kind=="floor":
        var tiles: Array=layout.get("floor_tiles",[])
        floor_cells=Storeys.index(tiles)
        scene_projection.rebuild_floors(tiles,floor_paint)
    objects=scene_projection.apply_layout(objects,layout,{} if wall_finish_changed else change)
    if not is_instance_valid(scene_projection.architecture_view):
        scene_projection.architecture_view=preload("hall/HallArchitectureView.gd").new()
        world.add_child(scene_projection.architecture_view)
    scene_projection.architecture_view.rebuild(layout,scene_projection,floor_paint)
    document.materialize_initial_content(scene_projection.initial_contents(objects),layout_rules)
    for row in objects:row.data=document.object_data(row.data.id)
    if reset_selection:
        editor.floor_anchor=null;editor.floor_preview_key=[]
        if is_instance_valid(editor.build_preview):_clear_geometry(editor.build_preview)
    if reset_selection or selected>=objects.size():selected=-1
    var shell_top := 0.0
    for row in objects:
        if row.data.kind=="shell":
            shell_top=maxf(shell_top,row.node.position.y+float(row.data.design.height)*float(row.data.scale))
    if shell_top!=highest_shell_top:
        highest_shell_top=shell_top
        eye.far=maxf(70,highest_shell_top+50)
        _camera()
    highest_level=Storeys.top_level(layout)
    var level_changed := active_level>highest_level
    if level_changed:
        camera_target.y+=Storeys.elevation(highest_level-active_level)
        active_level=highest_level;editor._set_tool("");_camera()
    var update_guides: bool=reset_selection or kind in ["floor","expand","add","remove"] or (
        kind=="patch" and ("at" in change.fields or "yaw" in change.fields))
    editor._refresh_floor_view(update_guides,reset_selection or level_changed)
    _finishes();_sync_panel()
    var spatial: bool=reset_selection or change.get("kind") in ["add","remove","expand","floor","region","exterior"]
    for field in change.get("fields",[]):
        if field in ["at","yaw","scale","length","design","height","opening","opening_width","opening_height","opening_offset","sill","width","thickness","wall_profile","rock_depth","rock_relief","rock_size","rock_seed"]:spatial=true
    if spatial:_visitor_layout_changed()

func _execute_build(kind: String,payload: Dictionary,remember: bool=true) -> bool:
    var result: Dictionary=build_commands.execute(kind,payload,remember)
    if not result.ok:notice=result.error;return false
    _apply_document(false,result)
    return true

func _remember() -> void:
    build_commands.remember()

func _undo() -> void:
    if build_editor!=null and build_editor.shells.session.mode!="":return
    if not build_commands.undo():return
    _apply_document(true);notice="已撤销。"

func _redo() -> void:
    if build_editor!=null and build_editor.shells.session.mode!="":return
    if not build_commands.redo():return
    _apply_document(true);notice="已重做。"

func _finishes() -> void:
    floor_paint.set_shader_parameter("tile_color",FLOOR_COLORS[floor_style])
    wall_paint.albedo_color=WALL_COLORS[wall_style]
    scene_projection.refresh_exterior_tint()

func _pick(screen: Vector2) -> int:
    var cam: Camera3D=editor_camera if editing else eye
    var origin := cam.project_ray_origin(screen);var ray := cam.project_ray_normal(screen)
    var query := PhysicsRayQueryParameters3D.create(origin,origin+ray*cam.far,2)
    var hit: Dictionary=world.get_world_3d().direct_space_state.intersect_ray(query)
    if hit.is_empty():return -1
    var id: String=hit.collider.get_meta("hall_id","")
    for i in objects.size():
        if objects[i].data.id==id:return i
    return -1

func _mode(value: bool) -> void:
    if build_editor!=null and build_editor.shells.session.mode!="":build_editor.shells.session.cancel()
    tank_session._stop_inspection()
    editing=value;looking=false;editor.dragging=false;editor.orbiting=false;editor.panning=false;editor._set_tool("")
    hall_lighting.set_state(hall_lighting.enabled,editing)
    _rebuild_room()
    Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    panel.side.visible=editing;editor_camera.current=editing;eye.current=not editing
    editor._refresh_floor_view(true,true)
    if not editing:_safe_spawn()
    _camera();_sync_panel()

func _safe_spawn() -> void:
    var query := PhysicsShapeQueryParameters3D.new();var capsule := CapsuleShape3D.new();capsule.radius=.25;capsule.height=1.7;query.shape=capsule;query.collision_mask=3
    var candidates: Array=[Vector3(0,.88,3.2),Vector3(3,.88,4.4),Vector3(-3,.88,4.4),Vector3(0,.88,6.1)]
    if active_level>0:
        var upper_candidates: Array=[]
        for tile in document.floor_tiles():
            if int(tile[1])==active_level:upper_candidates.append(Vector3(tile[0]+.5,Storeys.elevation(active_level)+.88,tile[2]+.5))
        candidates=upper_candidates+candidates
    for cell in parcels:
        var r: Rect2=Footprint.rect(cell)
        for x in [1.0,3.0,5.0]:
            for z in [1.0,3.5,6.0]:candidates.append(Vector3(r.position.x+x,.88,r.position.y+z))
    for at in candidates:
        query.transform=Transform3D(Basis.IDENTITY,at)
        if world.get_world_3d().direct_space_state.intersect_shape(query).is_empty():player.position=at;player.velocity=Vector3.ZERO;player.rotation.y=0;eye.rotation.x=0;return

func _camera() -> void:
    editor_camera.size=view_size
    var distance := maxf(maxf(30,highest_shell_top+10),view_size*2)
    editor_camera.far=maxf(100,distance+view_size*2+absf(camera_target.y)+100)
    editor_camera.position=camera_target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*distance
    editor_camera.rotation=Vector3(-pitch,yaw,0)

func _physics_process(delta: float) -> void:
    if editing or tank_session.inspecting or tank_session.active_editor!=null:return
    WalkController.tick(player,delta)
    if player.position.y< -3:_safe_spawn()

func _input(event: InputEvent) -> void:
    if tank_session.active_editor!=null:return
    if editor.handle_input(event):
        get_viewport().set_input_as_handled()
        return
    if event is InputEventKey and build_editor!=null and build_editor.shells.session.mode!="":return
    if tank_session.handle_inspection_input(event):
        get_viewport().set_input_as_handled()
        return
    if event is InputEventMouseMotion and looking and not editing:
        player.rotation.y-=event.relative.x*.003
        eye.rotation.x=clampf(eye.rotation.x-event.relative.y*.003,-1.2,1.2)
        get_viewport().set_input_as_handled()
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode==KEY_ESCAPE:
            if tank_session.inspecting:tank_session._stop_inspection();get_viewport().set_input_as_handled();return
            Input.mouse_mode=Input.MOUSE_MODE_VISIBLE;looking=false;editor._set_tool("");get_viewport().set_input_as_handled()
        if event.keycode==KEY_TAB:_mode(not editing);get_viewport().set_input_as_handled()
    if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_RIGHT and not event.pressed and looking:
        looking=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE


func _canvas_input(event: InputEvent) -> void:
    if tank_session.active_editor!=null:return
    if tank_session.inspecting:
        tank_session.inspection_canvas_input(event)
        return
    if editing:
        editor.canvas_input(event)
        return
    if event is InputEventMouseButton:
        pointer=event.position*Vector2(viewport.size)/canvas.size
        if event.button_index==MOUSE_BUTTON_RIGHT and event.pressed:looking=true;Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
        if event.button_index==MOUSE_BUTTON_LEFT and event.pressed:selected=_pick(pointer);_sync_panel()

func _unhandled_key_input(event: InputEvent) -> void:
    editor.key_input(event)

func _sync_panel() -> void:
    panel.sync(self)
    editor._selection()

func _visitor_layout_changed() -> void:
    if is_instance_valid(visitor_crowd):visitor_crowd.set_layout(parcels,objects,document.floor_tiles(),preload("hall/HallExteriorWall.gd").settings(_state()))

func _process(delta: float) -> void:
    if build_editor!=null:build_editor.tick()
    if is_instance_valid(water_renderer):water_renderer.sync(visible_objects,delta)
    if tank_session.inspecting:tank_session._update_inspection()
    panel.tick(delta, notice)

func _valid_state(data: Variant) -> bool:
    return layout_rules._valid_state(data)

func _write_layout(path: String) -> bool:
    if warehouse_linked and path==save_path:
        var layout:=_state()
        if not layout_rules._valid_state(layout) or not valid_stock(layout):return false
        var serialized:=JSON.stringify(layout,"",true,true)
        if not save_session_layout.call(serialized):return false
        session_layout=serialized
        return true
    return LayoutStore.write_layout(path,_state(),layout_rules)

func valid_stock(layout: Dictionary) -> bool:
    var used:Dictionary={}
    for row in layout.objects:
        for fish in row.get("interior",{}).get("fish",[]):
            var id:String=fish.get("stock","")
            if used.has(id) or warehouse.get(id)!=fish.id:return false
            used[id]=true
    return true

func _save_layout() -> void:
    if read_only:notice="当前为只读预览，不写入游戏存档。";return
    var okay := _write_layout(save_path)
    if okay:saved_digest=JSON.stringify(_state()).sha256_text()
    notice="大厅与全部缸内布景已保存。" if okay else "保存失败，当前布局仍保留。"
    if okay and warehouse_linked and not session_has_slot:notice="已保存到本局。退出游戏前请在主菜单保存到槽位。"

func _load_layout(path: String) -> bool:
    if build_editor!=null and build_editor.shells.session.mode!="":build_editor.shells.session.cancel()
    var state: Variant
    if warehouse_linked and path==save_path and not session_layout.is_empty():
        state=JSON.parse_string(session_layout)
        if not layout_rules._valid_state(state):state=null
    else:
        if not FileAccess.file_exists(path):notice="还没有大厅存档。";return false
        state=LayoutStore.read_layout(path,layout_rules)
    if state!=null and warehouse_linked and not valid_stock(state):state=null
    if state==null:notice="存档无效，当前布局保持不变。";return false
    _remember();editor._set_tool("");active_level=0;floor_views.clear();_restore(state);editor._fit_hall();saved_digest=JSON.stringify(_state()).sha256_text();notice="已读取大厅布局。";return true

func _request_return() -> void:
    if JSON.stringify(_state()).sha256_text()==saved_digest:return_requested.emit();return
    var dialog := ConfirmationDialog.new();dialog.title="离开大厅";dialog.dialog_text="有尚未保存的布展修改。保存后离开吗？"
    dialog.ok_button_text="保存并离开";dialog.cancel_button_text="继续布置"
    dialog.add_button("不保存离开",true,"discard")
    dialog.confirmed.connect(func():
        if not read_only and _write_layout(save_path):return_requested.emit()
        elif read_only:return_requested.emit()
        else:notice="保存失败，仍留在大厅。")
    dialog.custom_action.connect(func(action):
        if action=="discard":return_requested.emit())
    dialog.canceled.connect(func():dialog.queue_free());add_child(dialog);dialog.popup_centered(Vector2i(500,180))

func _exit_tree() -> void:
    Input.mouse_mode=Input.MOUSE_MODE_VISIBLE

func _open_content_editor() -> bool:
    return tank_session._open_content_editor()

func _commit_wall(start: Vector3, finish: Vector3) -> bool:
    return editor._commit_wall(start, finish)

func _expand_at(at: Vector3) -> bool:
    return editor._expand_at(at)
