extends Control
## Editable hall host. Separate per-slot creative layout; legacy game data is
## never rewritten as if these decorative fish were purchased inventory.
signal return_requested
const LayoutStore=preload("res://scripts/aquarium/hall/HallLayoutStore.gd")
const WalkController=preload("res://scripts/aquarium/hall/HallWalkController.gd")
var editor_input=preload("res://scripts/aquarium/hall/HallEditorInput.gd").new()
var layout_rules=preload("res://scripts/aquarium/hall/HallLayoutRules.gd").new()
var document=preload("res://scripts/aquarium/hall/HallLayoutDocument.gd").new()
var build_commands: RefCounted
var scene_projection: RefCounted
var save_path := "user://aquarium-hall-3d-preview-v1.json"
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
var dragging := false
var orbiting := false
var drag_offset := Vector3.ZERO
var yaw := .48
var pitch := .83
var view_size := 20.5
var camera_target := Vector3(1.8,1.0,-.6)
var pending_kind := ""
var pointer := Vector2.ZERO
var notice := "自由布展：点击选取，拖动移动，Q/E 旋转；Tab 切换逛馆。"
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
var water_panel
var water_drag := false
var inspecting := false
var inspection_camera: Camera3D
var inspection_tank_id := ""
var inspection_fish := 0
var inspection_distance := 2.4
var inspection_yaw := 0.0
var inspection_pitch := .08
const WaterProfile=preload("res://scripts/aquarium/TankWaterProfile.gd")
var pixel_materials := true
var surface_materials: Array=[]
var surface_art: Dictionary={}
const HALL_ART := "res://assets/aquarium-hall-style-v3/"
var side: ColorRect
var detail: Label
var status: Label
var mode_button: Button
var size_spin: SpinBox
var fish_spin: SpinBox
var visitor_spin: SpinBox
var visitor_crowd
var selection_box: MeshInstance3D
var edit_history=preload("res://scripts/aquarium/hall/HallEditHistory.gd").new()
var history: Array:
    get:return edit_history.past
var future: Array:
    get:return edit_history.future
var panel_sync := false
var active_editor
var editor_object_id := ""
var editor_backdrop: ColorRect
var editor_hidden: Array=[]
var capture_active := false
var id_serial := 1
var statistics_clock := 0.0
var saved_digest := ""
const Footprint = preload("res://scripts/aquarium/HallFootprint.gd")
var parcels: Array:
    get:return document.parcels()
var room_geometry: Node3D
var build_preview: Node3D
var parcel_hints: Node3D
var parcel_label: Label
var tool_label: Label
var tank_size_choice: OptionButton
var wall_choice: OptionButton
var pending_yaw := 0.0
var wall_anchor: Variant=null
var wall_with_door := false
var panning := false
var placement_error := ""
const MAX_OBJECTS := 80
const MAX_TANKS := 8
const FLOOR_COLORS := [Color("778d8b"),Color("b4b5a5"),Color("4c626d")]
const WALL_COLORS := [Color("d4d6c5"),Color("8daaad"),Color("b1b3a0")]

func _ready() -> void:
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    mouse_filter=Control.MOUSE_FILTER_IGNORE
    _register_input()
    viewport=SubViewport.new();viewport.size=Vector2i(1920,1080);viewport.own_world_3d=true
    viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    add_child(viewport)
    world=Node3D.new();viewport.add_child(world)
    canvas=TextureRect.new();canvas.texture=viewport.get_texture()
    canvas.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;canvas.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    canvas.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    canvas.gui_input.connect(_canvas_input);add_child(canvas)
    build_commands=preload("res://scripts/aquarium/hall/HallBuildCommands.gd").new(document,layout_rules,edit_history)
    _room()
    _player()
    inspection_camera=Camera3D.new();inspection_camera.near=.025;inspection_camera.far=100;inspection_camera.fov=62;world.add_child(inspection_camera)
    _ui()
    visitor_crowd=preload("res://scripts/aquarium/visitors/HallVisitorCrowd.gd").new()
    world.add_child(visitor_crowd)
    _restore(_default_state())
    _mode(true)
    saved_digest=JSON.stringify(_state()).sha256_text()
    if FileAccess.file_exists(save_path):
        if not _load_layout(save_path):notice="大厅存档无效，已保留默认布局。"
    if not visitor_crowd.resources_ready:notice="游客暂不可用："+visitor_crowd.resource_error
    _sync_panel()
    DisplayServer.window_set_title("潮汐馆 · 可编辑 3D 大厅")

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

func _collision(parent: Node3D,at: Vector3,size: Vector3,layer:=1) -> StaticBody3D:
    return scene_projection._collision(parent,at,size,layer)

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
    selection_box=MeshInstance3D.new();world.add_child(selection_box)
    var wire := _paint(Color("f2cc72"),true);wire.no_depth_test=true
    selection_box.material_override=wire;selection_box.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    build_preview=Node3D.new();world.add_child(build_preview)
    parcel_hints=Node3D.new();world.add_child(parcel_hints)

func _clear_geometry(node: Node3D) -> void:
    scene_projection._clear_geometry(node)

func _rebuild_room() -> void:
    scene_projection.rebuild_room(parcels,editing,floor_paint,wall_paint)
    room_geometry=scene_projection.room_geometry
    _refresh_parcel_hints()

func _expand_at(at: Vector3) -> bool:
    if not _execute_build("expand",{"cell":Footprint.at(at)}):return false
    _fit_hall();notice="已增加一块 6×7 米地基；外墙已更新，可继续点相邻地块。"
    return true

func _fit_hall() -> void:
    var rect: Rect2=Footprint.extent(parcels)
    # Keep the hall in the visible space to the left of the inspector.
    camera_target=Vector3(rect.get_center().x+1.8,1.0,rect.get_center().y-.6)
    view_size=clampf(maxf(rect.size.y*1.45,rect.size.x*.98),20.5,58)
    _camera()

func _refresh_parcel_hints() -> void:
    if not is_instance_valid(parcel_hints):return
    _clear_geometry(parcel_hints)
    if pending_kind!="parcel" or not editing:return
    for cell in Footprint.candidates(parcels):
        var rect: Rect2=Footprint.rect(cell);var p := rect.get_center()
        var material := _paint(Color(.24,.69,.64,.18),true)
        material.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
        _box(parcel_hints,Vector3(p.x,.015,p.y),Vector3(5.84,.025,6.84),material)
        var sign := Label3D.new();sign.text="＋ 6×7 m";sign.position=Vector3(p.x,.12,p.y);sign.rotation.x=-PI/2;sign.font_size=55;sign.pixel_size=.012;parcel_hints.add_child(sign)

func _player() -> void:
    player=CharacterBody3D.new();player.collision_layer=4;player.collision_mask=3;world.add_child(player)
    var collision := CollisionShape3D.new();var capsule := CapsuleShape3D.new();capsule.radius=.24;capsule.height=1.7
    collision.shape=capsule;player.add_child(collision)
    player.position=Vector3(0,.88,3.2)
    eye=Camera3D.new();eye.position.y=.74;eye.fov=68;eye.near=.04;eye.far=70;player.add_child(eye)

func _default_state() -> Dictionary:
    return {"schema_version":1,"floor_style":0,"wall_style":0,"objects":[
        {"id":"exhibit-main","kind":"tank","name":"沉船与遗迹主缸","at":[0,-4.8],"yaw":0.0,"scale":1.0,"fish_count":8,"content":{}},
        {"id":"exhibit-side","kind":"tank","name":"侧厅海鱼缸","at":[-5.7,-.15],"yaw":PI/2,"scale":.65,"fish_count":4,"content":{}},
        {"id":"bench-1","kind":"bench","name":"观赏长凳","at":[0,.85],"yaw":0.0,"scale":1.0},
        {"id":"plinth-1","kind":"plinth","name":"石灯展示台","at":[5.8,-3.5],"yaw":0.0,"scale":1.0}
    ]}

func _bounds(data: Dictionary) -> AABB:
    return layout_rules._bounds(data)

func _transform(data: Dictionary) -> Transform3D:
    return layout_rules._transform(data)

func _valid_placement(data: Dictionary,rows: Array,ignore_id: String="",cells: Array=[]) -> bool:
    var valid := layout_rules._valid_placement(data,rows,ignore_id,parcels if cells.is_empty() else cells)
    placement_error=layout_rules.placement_error
    return valid

func _create(data: Dictionary) -> Dictionary:
    return scene_projection._create(data)

func _wall_geometry(root: Node3D,data: Dictionary) -> void:
    scene_projection._wall_geometry(root,data)

func _refresh_wall(row: Dictionary) -> void:
    scene_projection._refresh_wall(row)

func _state() -> Dictionary:
    return document.snapshot()

func _restore(state: Dictionary) -> void:
    if not document.replace(state,layout_rules):notice="布局无效，当前场景保持不变。";return
    _apply_document(true)

func _apply_document(reset_selection: bool=false,change: Dictionary={}) -> void:
    if reset_selection or change.get("kind")=="expand":_rebuild_room()
    objects=scene_projection.apply_layout(objects,document.snapshot(),change)
    document.materialize_initial_content(scene_projection.initial_contents(objects),layout_rules)
    for row in objects:row.data=document.object_data(row.data.id)
    if reset_selection or selected>=objects.size():selected=-1
    _finishes();_sync_panel()
    var spatial: bool=reset_selection or change.get("kind") in ["add","remove","expand"]
    for field in change.get("fields",[]):
        if field in ["at","yaw","scale","length"]:spatial=true
    if spatial:_visitor_layout_changed()

func _execute_build(kind: String,payload: Dictionary,remember: bool=true) -> bool:
    var result: Dictionary=build_commands.execute(kind,payload,remember)
    if not result.ok:notice=result.error;return false
    _apply_document(false,result)
    return true

func _change_finish(key: String) -> void:
    _execute_build("style",{"key":key,"value":(document.style(key)+1)%3})

func _remember() -> void:
    build_commands.remember()

func _undo() -> void:
    if not build_commands.undo():return
    _apply_document(true);notice="已撤销。"

func _redo() -> void:
    if not build_commands.redo():return
    _apply_document(true);notice="已重做。"

func _finishes() -> void:
    floor_paint.set_shader_parameter("tile_color",FLOOR_COLORS[floor_style])
    wall_paint.albedo_color=WALL_COLORS[wall_style]

func _floor_hit(screen: Vector2) -> Variant:
    var origin := editor_camera.project_ray_origin(screen);var ray := editor_camera.project_ray_normal(screen)
    if absf(ray.y)<.001:return null
    var t: float=-origin.y/ray.y
    if t<0:return null
    return origin+ray*t

func _pick(screen: Vector2) -> int:
    var cam: Camera3D=editor_camera if editing else eye
    var origin := cam.project_ray_origin(screen);var ray := cam.project_ray_normal(screen)
    var query := PhysicsRayQueryParameters3D.create(origin,origin+ray*80,2)
    var hit: Dictionary=world.get_world_3d().direct_space_state.intersect_ray(query)
    if hit.is_empty():return -1
    var id: String=hit.collider.get_meta("hall_id","")
    for i in objects.size():
        if objects[i].data.id==id:return i
    return -1

func _move_selected(at: Vector3) -> bool:
    if selected<0:return false
    return _execute_build("patch",{"id":objects[selected].data.id,"patch":{"at":[snappedf(at.x,.25),snappedf(at.z,.25)]}},false)

func _rotate_selected(direction: float) -> bool:
    if selected<0:return false
    var data: Dictionary=objects[selected].data
    if not _execute_build("patch",{"id":data.id,"patch":{"yaw":data.yaw+(PI/2 if data.kind=="wall" else deg_to_rad(15))*direction}}):
        notice="旋转后会碰到其他物件或墙。";return false
    return true

func _resize_selected(value: float) -> bool:
    if panel_sync or selected<0:return false
    var data: Dictionary=objects[selected].data
    var patch: Dictionary={}
    if data.kind=="wall":patch.length=snappedf(clampf(value,3 if data.get("door",false) else .5,18),.5)
    else:patch.scale=clampf(value,.4,1.3)
    if not _execute_build("patch",{"id":data.id,"patch":patch}):notice="放大后空间不足。";_sync_panel();return false
    return true

func _candidate(kind: String,at: Vector3) -> Dictionary:
    var preset := [.5,.65,1.0]
    var choice: int=tank_size_choice.selected if is_instance_valid(tank_size_choice) else 1
    var data := {"id":"placement-preview","kind":kind,"name":{"tank":"新展缸","bench":"观赏长凳","plinth":"石灯展示台"}.get(kind,"隔墙"),"at":[snappedf(at.x,.25),snappedf(at.z,.25)],"yaw":pending_yaw,"scale":float(preset[choice]) if kind=="tank" else 1.0}
    if kind=="tank":data.fish_count=0;data.content={}
    return data

func _add_at(kind: String,at: Vector3) -> bool:
    if objects.size()>=MAX_OBJECTS:notice="大厅最多 80 件物品。";return false
    if kind=="tank" and objects.filter(func(r):return r.data.kind=="tank").size()>=MAX_TANKS:notice="本版最多 8 个展缸。";return false
    var id: String="hall-%d-%d" % [Time.get_unix_time_from_system(),id_serial];id_serial+=1
    var data := _candidate(kind,at);data.id=id
    if not _execute_build("add",{"object":data}):return false
    selected=objects.size()-1;_set_tool("");_sync_panel();notice="已添加，可拖动调整位置。";return true

func _wall_candidate(start: Vector3,finish: Vector3) -> Dictionary:
    start=Vector3(snappedf(start.x,.5),0,snappedf(start.z,.5))
    finish=Vector3(snappedf(finish.x,.5),0,snappedf(finish.z,.5))
    var along_x := absf(finish.x-start.x)>=absf(finish.z-start.z)
    if along_x:finish.z=start.z;finish.x=start.x+clampf(finish.x-start.x,-18,18)
    else:finish.x=start.x;finish.z=start.z+clampf(finish.z-start.z,-18,18)
    return {"id":"wall-preview","kind":"wall","name":"门洞隔墙" if wall_with_door else "馆内隔墙","at":[(start.x+finish.x)/2,(start.z+finish.z)/2],"yaw":0.0 if along_x else PI/2,"scale":1.0,"length":start.distance_to(finish),"door":wall_with_door}

func _commit_wall(start: Vector3,finish: Vector3) -> bool:
    var data := _wall_candidate(start,finish)
    if data.length<(3 if data.door else .5):notice="门洞隔墙至少 3 米。" if data.door else "请拉出至少半米长的直墙。";return false
    if objects.size()>=MAX_OBJECTS:notice="大厅最多 80 件物品。";return false
    data.id="wall-%d-%d" % [Time.get_unix_time_from_system(),id_serial];id_serial+=1
    if not _execute_build("add",{"object":data}):return false
    selected=objects.size()-1;wall_anchor=null;_sync_panel()
    notice="隔墙已建好；可继续画下一段，按 Esc 结束。"
    return true

func _set_tool(kind: String) -> void:
    pending_kind=kind;pending_yaw=0;wall_anchor=null;dragging=false
    if is_instance_valid(build_preview):_clear_geometry(build_preview)
    _refresh_parcel_hints()
    notice={"parcel":"点击浅绿色相邻地块扩建；每块 6×7 米。","wall":"先点墙起点，再点终点；自动取直线，Esc 取消。","tank":"移动鼠标预览新展缸；Q/E 转向，点击放下，Esc 取消。","bench":"点击空地放长凳。","plinth":"点击空地放展示台。","":"已切回选择，可拖动物件。"}.get(kind,"")
    if kind=="parcel":
        var extent: Rect2=Footprint.extent(parcels)
        view_size=clampf(maxf(extent.size.y*1.45,extent.size.x*.98)+13,30,65);_camera()

func _preview(at: Variant) -> void:
    _clear_geometry(build_preview)
    if at==null or pending_kind=="" or not editing:return
    var box: AABB
    var allowed := false
    if pending_kind=="parcel":
        var cell: Array=Footprint.at(at);var rect: Rect2=Footprint.rect(cell)
        box=AABB(Vector3(rect.position.x,.03,rect.position.y),Vector3(6,.06,7));allowed=Footprint.can_add(parcels,cell)
    elif pending_kind=="wall":
        if wall_anchor==null:
            box=AABB(Vector3(snappedf(at.x,.5)-.12,0,snappedf(at.z,.5)-.12),Vector3(.24,.12,.24));allowed=Footprint.contains(parcels,box)
        else:
            var data := _wall_candidate(wall_anchor,at)
            box=_transform(data)*_bounds(data);allowed=data.length>=(3 if data.door else .5) and _valid_placement(data,objects)
    else:
        var data := _candidate(pending_kind,at)
        box=_transform(data)*_bounds(data);allowed=_valid_placement(data,objects) and objects.size()<MAX_OBJECTS
        if pending_kind=="tank" and objects.filter(func(r):return r.data.kind=="tank").size()>=MAX_TANKS:allowed=false
    var paint := _paint(Color(.3,.9,.65,.24) if allowed else Color(1,.28,.26,.30),true)
    paint.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA;paint.cull_mode=BaseMaterial3D.CULL_DISABLED
    _box(build_preview,box.get_center(),box.size,paint)
    if is_instance_valid(tool_label):tool_label.text=("可放置" if allowed else "不可放置")+" · "+{"parcel":"扩建地块","wall":"画隔墙","tank":"放展缸","bench":"放长凳","plinth":"放展示台"}.get(pending_kind,"")

func _delete_selected() -> void:
    if selected<0:return
    var id: String=objects[selected].data.id
    if _execute_build("remove",{"id":id}):selected=-1;_sync_panel();notice="已删除，可撤销。"

func _selection() -> void:
    selection_box.visible=editing and selected>=0
    if not selection_box.visible:return
    var row: Dictionary=objects[selected];var box: AABB=_bounds(row.data).grow(.025)
    var mesh := ImmediateMesh.new();mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for pair in [[0,1],[1,3],[3,2],[2,0],[4,5],[5,7],[7,6],[6,4],[0,4],[1,5],[2,6],[3,7]]:
        for corner in pair:mesh.surface_add_vertex(box.get_endpoint(corner))
    mesh.surface_end();selection_box.mesh=mesh;selection_box.transform=row.node.transform

func _mode(value: bool) -> void:
    _stop_inspection()
    editing=value;looking=false;dragging=false;orbiting=false;panning=false;_set_tool("")
    hall_lighting.set_state(hall_lighting.enabled,editing)
    _rebuild_room()
    Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    side.visible=editing;editor_camera.current=editing;eye.current=not editing
    if not editing:_safe_spawn()
    _camera();_sync_panel()

func _safe_spawn() -> void:
    var query := PhysicsShapeQueryParameters3D.new();var capsule := CapsuleShape3D.new();capsule.radius=.25;capsule.height=1.7;query.shape=capsule;query.collision_mask=3
    var candidates: Array=[Vector3(0,.88,3.2),Vector3(3,.88,4.4),Vector3(-3,.88,4.4),Vector3(0,.88,6.1)]
    for cell in parcels:
        var r: Rect2=Footprint.rect(cell)
        for x in [1.0,3.0,5.0]:
            for z in [1.0,3.5,6.0]:candidates.append(Vector3(r.position.x+x,.88,r.position.y+z))
    for at in candidates:
        query.transform=Transform3D(Basis.IDENTITY,at)
        if world.get_world_3d().direct_space_state.intersect_shape(query).is_empty():player.position=at;player.velocity=Vector3.ZERO;player.rotation.y=0;eye.rotation.x=0;return

func _camera() -> void:
    editor_camera.size=view_size
    editor_camera.position=camera_target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*30
    editor_camera.look_at(camera_target)

func _physics_process(delta: float) -> void:
    if editing or inspecting or active_editor!=null:return
    WalkController.tick(player,delta)

func _input(event: InputEvent) -> void:
    if active_editor!=null:return
    if inspecting and event is InputEventMouseMotion and looking:
        inspection_yaw-=event.relative.x*.004;inspection_pitch=clampf(inspection_pitch+event.relative.y*.003,-.65,.85)
        _update_inspection();get_viewport().set_input_as_handled();return
    if event is InputEventMouseMotion and looking and not editing:
        player.rotation.y-=event.relative.x*.003
        eye.rotation.x=clampf(eye.rotation.x-event.relative.y*.003,-1.2,1.2)
        get_viewport().set_input_as_handled()
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode==KEY_ESCAPE:
            if inspecting:_stop_inspection();get_viewport().set_input_as_handled();return
            Input.mouse_mode=Input.MOUSE_MODE_VISIBLE;looking=false;_set_tool("");get_viewport().set_input_as_handled()
        if event.keycode==KEY_TAB:_mode(not editing);get_viewport().set_input_as_handled()
    if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_RIGHT and not event.pressed and looking:
        looking=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    if event is InputEventMouseButton and not event.pressed:
        if event.button_index==MOUSE_BUTTON_RIGHT:orbiting=false
        if event.button_index==MOUSE_BUTTON_MIDDLE:panning=false

func _canvas_input(event: InputEvent) -> void:
    if active_editor!=null:return
    if inspecting:
        if event is InputEventMouseButton:
            if event.button_index==MOUSE_BUTTON_RIGHT:
                looking=event.pressed;Input.mouse_mode=Input.MOUSE_MODE_CAPTURED if looking else Input.MOUSE_MODE_VISIBLE
            if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
                inspection_distance=clampf(inspection_distance*(.88 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.14),.22,8.0);_update_inspection()
        return
    if editing:
        editor_input.canvas_input(self,event)
        return
    if event is InputEventMouseButton:
        pointer=event.position*Vector2(viewport.size)/canvas.size
        if event.button_index==MOUSE_BUTTON_RIGHT and event.pressed:looking=true;Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
        if event.button_index==MOUSE_BUTTON_LEFT and event.pressed:selected=_pick(pointer);_sync_panel()

func _unhandled_key_input(event: InputEvent) -> void:
    editor_input.key_input(self,event)

func _open_content_editor() -> bool:
    _stop_inspection()
    if selected<0 or objects[selected].data.kind!="tank":notice="先选择一个展缸。";return false
    editor_object_id=objects[selected].data.id
    active_editor=load("res://scripts/aquarium/HallTankEditor.gd").new()
    active_editor.initial_state=objects[selected].tank.content_state()
    active_editor.apply_requested.connect(_apply_content_editor)
    active_editor.cancel_requested.connect(_close_content_editor)
    editor_hidden.clear()
    for child in get_children():
        if child is CanvasItem and child.visible:editor_hidden.append(child);child.hide()
    editor_backdrop=ColorRect.new();editor_backdrop.color=Color("0c2028");editor_backdrop.size=Vector2(1920,1080);add_child(editor_backdrop)
    viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED
    visitor_crowd.set_paused(true)
    add_child(active_editor);Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    return true

func _apply_content_editor(state: Dictionary) -> void:
    if not _execute_build("patch",{"id":editor_object_id,"patch":{"content":state}}):return
    _close_content_editor();notice="缸内布景已应用；保存大厅可一起保存。"

func _close_content_editor() -> void:
    if is_instance_valid(active_editor):active_editor.hide();active_editor.queue_free()
    active_editor=null
    visitor_crowd.set_paused(false)
    if is_instance_valid(editor_backdrop):editor_backdrop.hide();editor_backdrop.queue_free()
    for child in editor_hidden:
        if is_instance_valid(child):child.show()
    editor_hidden.clear();side.visible=editing;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    get_window().content_scale_size=Vector2i(1920,1080)
    DisplayServer.window_set_title("潮汐馆 · 可编辑 3D 大厅")
    editor_camera.current=editing;eye.current=not editing

func _ui() -> void:
    preload("res://scripts/aquarium/hall/HallEditorPanel.gd").new().build(self)

func _open_water_panel() -> void:
    if selected<0 or objects[selected].tank==null:
        for i in objects.size():
            if objects[i].tank!=null:selected=i;break
    if selected<0 or objects[selected].tank==null:notice="先放置一个展缸，再调整水体。";return
    _set_tool("");dragging=false;_sync_panel();water_panel.show()

func _water_changed(key: String,value: Variant) -> void:
    if selected<0 or objects[selected].tank==null:return
    var config: Dictionary=objects[selected].data.water.duplicate(true);config[key]=value
    if _execute_build("patch",{"id":objects[selected].data.id,"patch":{"water":config}},not water_drag):
        notice="已调整这个展缸的水体外观；可撤销并保存。"

func _water_preset(index: int) -> void:
    if selected<0 or objects[selected].tank==null:return
    _execute_build("patch",{"id":objects[selected].data.id,"patch":{"water":WaterProfile.preset(index)}})

func _start_inspection(reset: bool=true) -> void:
    if selected<0 or objects[selected].tank==null:_open_water_panel()
    if selected<0 or objects[selected].tank==null:return
    inspection_tank_id=objects[selected].data.id;inspecting=true;looking=false;dragging=false
    if reset:inspection_distance=2.4*objects[selected].node.scale.x;inspection_yaw=0;inspection_pitch=.08;inspection_fish=0
    side.hide();editor_camera.current=false;eye.current=false;inspection_camera.current=true
    Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    notice="近景观察：滚轮推进缸内，右键环绕，Esc 返回。"
    _update_inspection()

func _update_inspection() -> void:
    for row in objects:
        if row.data.id!=inspection_tank_id or row.tank==null:continue
        var target: Vector3=row.tank.global_transform*Vector3(0,1.4,0)
        if not row.tank.fish.is_empty():target=row.tank.fish[posmod(inspection_fish,row.tank.fish.size())].carrier.global_position
        var axis := Vector3(sin(inspection_yaw)*cos(inspection_pitch),sin(inspection_pitch),cos(inspection_yaw)*cos(inspection_pitch))
        axis=row.node.global_basis.orthonormalized()*axis
        inspection_camera.global_position=target+axis*inspection_distance
        inspection_camera.look_at(target);return
    _stop_inspection()

func _stop_inspection() -> void:
    if not inspecting:return
    inspecting=false;looking=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    inspection_camera.current=false;editor_camera.current=editing;eye.current=not editing;side.visible=editing
    notice="已返回大厅视角。"

func _fish_count_changed(value: float) -> void:
    if panel_sync or selected<0 or objects[selected].data.kind!="tank":return
    if _execute_build("patch",{"id":objects[selected].data.id,"patch":{"fish_count":int(value)}}):notice="已调整这个展缸的展示海鱼数量。"

func _sync_panel() -> void:
    if not is_instance_valid(detail):return
    panel_sync=true
    parcel_label.text="地块 %d / 24  ·  面积 %d m²" % [parcels.size(),parcels.size()*42]
    if pending_kind=="":tool_label.text="选择物件进行编辑"
    mode_button.text="切换逛馆  Tab" if editing else "编辑大厅  Tab"
    if selected<0:
        detail.text="未选中物件\n点击展缸、家具或隔墙"
        size_spin.editable=false;fish_spin.editable=false
    else:
        var data: Dictionary=objects[selected].data
        detail.text="%s\n位置 %.2f / %.2f m" % [data.name,data.at[0],data.at[1]]
        size_spin.editable=true
        size_spin.min_value=3 if data.kind=="wall" and data.get("door",false) else (.5 if data.kind=="wall" else .4)
        size_spin.max_value=18 if data.kind=="wall" else 1.3;size_spin.step=.5 if data.kind=="wall" else .05
        size_spin.set_value_no_signal(float(data.length) if data.kind=="wall" else float(data.scale))
        fish_spin.editable=data.kind=="tank";fish_spin.set_value_no_signal(float(data.get("fish_count",0)))
    if is_instance_valid(water_panel) and selected>=0 and objects[selected].tank!=null:water_panel.bind(objects[selected].data.water,objects[selected].data.name)
    panel_sync=false;_selection()

func _visitor_layout_changed() -> void:
    if is_instance_valid(visitor_crowd):visitor_crowd.set_layout(parcels,objects)

func _process(delta: float) -> void:
    if is_instance_valid(water_renderer):water_renderer.sync(objects,delta)
    if inspecting:_update_inspection()
    statistics_clock+=delta
    if statistics_clock>.15:statistics_clock=0;status.text=notice

func _finite_number(value: Variant) -> bool:
    return layout_rules._finite_number(value)

func _valid_content(data: Variant) -> bool:
    return layout_rules._valid_content(data)

func _valid_state(data: Variant) -> bool:
    return layout_rules._valid_state(data)

func _write_layout(path: String) -> bool:
    return LayoutStore.write_layout(path,_state(),layout_rules)

func _save_layout() -> void:
    if read_only:notice="当前为只读预览，不写入游戏存档。";return
    var okay := _write_layout(save_path)
    if okay:saved_digest=JSON.stringify(_state()).sha256_text()
    notice="大厅与全部缸内布景已保存。" if okay else "保存失败，当前布局仍保留。"

func _load_layout(path: String) -> bool:
    if not FileAccess.file_exists(path):notice="还没有大厅存档。";return false
    var state: Variant=LayoutStore.read_layout(path,layout_rules)
    if state==null:notice="存档无效，当前布局保持不变。";return false
    _remember();_set_tool("");_restore(state);_fit_hall();saved_digest=JSON.stringify(_state()).sha256_text();notice="已读取地块、隔墙与全部展缸。旧版布局仅在主动保存时升级。";return true

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
