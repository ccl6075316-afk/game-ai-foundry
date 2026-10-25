extends Control
## Editable hall host. Separate per-slot creative layout; legacy game data is
## never rewritten as if these decorative fish were purchased inventory.
signal return_requested
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
var floor_style := 0
var wall_style := 0
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
var selection_box: MeshInstance3D
var history: Array=[]
var future: Array=[]
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
var parcels: Array=Footprint.initial()
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
    _room()
    _player()
    inspection_camera=Camera3D.new();inspection_camera.near=.025;inspection_camera.far=100;inspection_camera.fov=62;world.add_child(inspection_camera)
    _ui()
    _restore(_default_state())
    _mode(true)
    saved_digest=JSON.stringify(_state()).sha256_text()
    if FileAccess.file_exists(save_path):
        if not _load_layout(save_path):notice="大厅存档无效，已保留默认布局。"
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
    var node := MeshInstance3D.new();var box := BoxMesh.new();box.size=size
    node.mesh=box;node.material_override=paint;node.position=at;parent.add_child(node)
    return node

func _collision(parent: Node3D,at: Vector3,size: Vector3,layer:=1) -> StaticBody3D:
    var body := StaticBody3D.new();body.collision_layer=layer;body.collision_mask=0;parent.add_child(body)
    var shape := CollisionShape3D.new();var box := BoxShape3D.new();box.size=size
    shape.shape=box;shape.position=at;body.add_child(shape)
    return body

func _room() -> void:
    hall_lighting=load("res://scripts/aquarium/HallLighting.gd").new();world.add_child(hall_lighting)
    water_renderer=load("res://scripts/aquarium/TankWaterRenderer.gd").new();world.add_child(water_renderer)
    floor_paint=ShaderMaterial.new();floor_paint.shader=load("res://scripts/aquarium/HallFloor3D.gdshader")
    floor_paint.set_shader_parameter("floor_art",load(HALL_ART+"hall_floor.png"))
    wall_paint=_surface(WALL_COLORS[0],"hall_wall")
    _rebuild_room()
    editor_camera=Camera3D.new();editor_camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    editor_camera.near=.04;editor_camera.far=100;world.add_child(editor_camera)
    selection_box=MeshInstance3D.new();world.add_child(selection_box)
    var wire := _paint(Color("f2cc72"),true);wire.no_depth_test=true
    selection_box.material_override=wire;selection_box.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    build_preview=Node3D.new();world.add_child(build_preview)
    parcel_hints=Node3D.new();world.add_child(parcel_hints)

func _clear_geometry(node: Node3D) -> void:
    for child in node.get_children():
        if child is StaticBody3D:child.collision_layer=0
        node.remove_child(child);child.queue_free()

func _rebuild_room() -> void:
    if not is_instance_valid(room_geometry):room_geometry=Node3D.new();world.add_child(room_geometry)
    _clear_geometry(room_geometry)
    var trim := _surface(Color("24434c"),"hall_wall")
    for cell in parcels:
        var rect: Rect2=Footprint.rect(cell)
        var center := rect.get_center()
        _box(room_geometry,Vector3(center.x,-.12,center.y),Vector3(6,.24,7),floor_paint)
        _collision(room_geometry,Vector3(center.x,-.12,center.y),Vector3(6,.24,7))
        var edges := [[[-1,0],Vector3(rect.position.x,2.3,center.y),Vector3(.2,4.6,7)],[[1,0],Vector3(rect.end.x,2.3,center.y),Vector3(.2,4.6,7)],[[0,-1],Vector3(center.x,2.3,rect.position.y),Vector3(6,4.6,.2)],[[0,1],Vector3(center.x,2.3,rect.end.y),Vector3(6,4.6,.2)]]
        for edge in edges:
            if Footprint.has(parcels,[cell[0]+edge[0][0],cell[1]+edge[0][1]]):continue
            _collision(room_geometry,edge[1],edge[2])
            # A low south cutaway keeps the build view legible; collision remains full height.
            var size: Vector3=edge[2];var pos: Vector3=edge[1]
            if edge[0]==[0,1] and editing:size.y=.65;pos.y=.325
            _box(room_geometry,pos,size,wall_paint)
            size.y=.16;pos.y=.08;_box(room_geometry,pos,size+Vector3(.02,0,.02),trim)
            var guide_pos: Vector3=edge[1]-Vector3(edge[0][0],0,edge[0][1])*.116
            guide_pos.y=.23
            var guide_size := Vector3(.022,.035,.52) if edge[2].x<1 else Vector3(.52,.035,.022)
            hall_lighting.add_guide(room_geometry,guide_pos,guide_size)
    _refresh_parcel_hints()

func _expand_at(at: Vector3) -> bool:
    var cell: Array=Footprint.at(at)
    if not Footprint.can_add(parcels,cell):notice="只能扩建相邻的空地块；起始 6 块，最多 24 块。";return false
    _remember();parcels.append(cell);_rebuild_room();_fit_hall();_sync_panel()
    notice="已增加一块 6×7 米地基；外墙已更新，可继续点相邻地块。"
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
    if data.kind=="wall":return AABB(Vector3(-float(data.length)/2,0,-.09),Vector3(float(data.length),3.2,.18))
    if data.kind=="tank":return AABB(Vector3(-3.1,0,-1.6),Vector3(6.2,3.3,3.2))
    if data.kind=="bench":return AABB(Vector3(-1,0,-.34),Vector3(2,.72,.68))
    return AABB(Vector3(-.55,0,-.55),Vector3(1.1,1.6,1.1))

func _transform(data: Dictionary) -> Transform3D:
    return Transform3D(Basis(Vector3.UP,float(data.yaw)).scaled(Vector3.ONE*float(data.scale)),Vector3(float(data.at[0]),0,float(data.at[1])))

func _valid_placement(data: Dictionary,rows: Array,ignore_id: String="",cells: Array=[]) -> bool:
    placement_error=""
    var box: AABB=_transform(data)*_bounds(data)
    if not Footprint.contains(parcels if cells.is_empty() else cells,box):placement_error="超出已扩建地基或贴到外墙。";return false
    for row in rows:
        var other: Dictionary=row.data if row.has("data") else row
        if other.id==ignore_id:continue
        var occupied: AABB=_transform(other)*_bounds(other)
        if data.kind=="wall" and other.kind=="wall":
            # T and cross junctions are intentional; overlapping parallel walls are not.
            var axis: Vector3=_transform(data).basis.x.normalized()
            var parallel: bool=absf(axis.dot(_transform(other).basis.x.normalized()))>.99
            if not parallel:continue
            if box.intersection(occupied).get_volume()>.002:placement_error="这里已有一段重叠隔墙。";return false
        elif box.grow(.12).intersects(occupied):placement_error="与展缸、家具或隔墙重叠。";return false
    return true

func _create(data: Dictionary) -> Dictionary:
    var root := Node3D.new();root.name=data.id;world.add_child(root)
    var tank
    if data.kind=="tank":
        tank=load("res://scripts/aquarium/HallTank3D.gd").new()
        tank.fish_limit=int(data.fish_count);tank.initial_content=data.get("content",{}).duplicate(true)
        root.add_child(tank);tank.position.y=.43
        tank.apply_exterior_materials(_surface(Color("132e38"),"hall_floor",Color("456e79")),_surface(Color("48747c"),"hall_wall"))
        hall_lighting.attach_tank(tank)
    elif data.kind=="wall":
        _wall_geometry(root,data)
    elif data.kind=="bench":
        var wood := _surface(Color("806547"),"hall_wood",Color.WHITE);var metal := _surface(Color("24434c"),"hall_wall")
        _box(root,Vector3(0,.48,0),Vector3(2,.12,.64),wood)
        _box(root,Vector3(0,.69,.27),Vector3(2,.08,.12),wood)
        for x in [-.72,.72]:_box(root,Vector3(x,.22,0),Vector3(.12,.44,.48),metal)
    else:
        _box(root,Vector3(0,.36,0),Vector3(1.0,.72,1.0),_surface(Color("526c70"),"hall_floor",Color("a8b9b8")))
        var catalog: Array=JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-decor-v1/catalog.json")).assets
        for spec in catalog:
            if spec.id!="stone_lantern":continue
            var model: Node3D=(load(spec.model) as PackedScene).instantiate();root.add_child(model)
            var paint := ShaderMaterial.new();paint.shader=load("res://scripts/aquarium/ThreeViewArtwork.gdshader")
            for v in ["front","right","top"]:paint.set_shader_parameter(v+"_art",load(spec.material_dir+"/stone_lantern-"+v+".png"))
            var d: Dictionary=spec.projection_bounds;paint.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
            for mesh in model.find_children("*","MeshInstance3D",true,false):
                for s in mesh.mesh.get_surface_count():mesh.set_surface_override_material(s,paint)
            model.scale=Vector3.ONE*2;model.position.y=.72
    var box := _bounds(data)
    var body: StaticBody3D
    if data.kind=="wall":body=root.get_meta("wall_body")
    else:body=_collision(root,box.get_center(),box.size,2);body.set_meta("hall_id",data.id)
    var row := {"data":data.duplicate(true),"node":root,"body":body,"tank":tank}
    if data.kind=="tank":row.data.water=WaterProfile.normalized(data.get("water",{}))
    root.transform=_transform(data)
    return row

func _wall_geometry(root: Node3D,data: Dictionary) -> void:
    var body := StaticBody3D.new();body.collision_layer=2;body.collision_mask=0;body.set_meta("hall_id",data.id);root.add_child(body);root.set_meta("wall_body",body)
    var length: float=data.length
    var pieces: Array=[]
    if data.get("door",false):
        var wing: float=(length-1.2)/2
        pieces=[[Vector3(-(length+1.2)/4,1.6,0),Vector3(wing,3.2,.18)],[Vector3((length+1.2)/4,1.6,0),Vector3(wing,3.2,.18)],[Vector3(0,2.7,0),Vector3(1.2,1,.18)]]
    else:pieces=[[Vector3(0,1.6,0),Vector3(length,3.2,.18)]]
    for piece in pieces:
        _box(root,piece[0],piece[1],wall_paint)
        var shape := CollisionShape3D.new();var box := BoxShape3D.new();box.size=piece[1];shape.shape=box;shape.position=piece[0];body.add_child(shape)
    var trim := _surface(Color("35535b"),"hall_wall")
    _box(root,Vector3(0,3.16,0),Vector3(length,.08,.22),trim)

func _refresh_wall(row: Dictionary) -> void:
    _clear_geometry(row.node);_wall_geometry(row.node,row.data);row.body=row.node.get_meta("wall_body")

func _state() -> Dictionary:
    var rows: Array=[]
    for row in objects:
        var data: Dictionary=row.data.duplicate(true)
        if data.kind=="tank":data.content=row.tank.content_state()
        rows.append(data)
    return {"schema_version":2,"parcels":parcels.duplicate(true),"floor_style":floor_style,"wall_style":wall_style,"objects":rows}

func _restore(state: Dictionary) -> void:
    parcels=state.get("parcels",Footprint.initial()).duplicate(true)
    _rebuild_room()
    var retained: Array=[]
    for data in state.objects:
        var found: Dictionary={}
        for row in objects:
            if row.data.id==data.id and row.data.kind==data.kind:found=row;break
        if found.is_empty():found=_create(data)
        else:
            if data.kind=="tank":
                if int(data.fish_count)!=int(found.data.fish_count):found.tank.set_fish_count(int(data.fish_count))
                if not data.get("content",{}).is_empty() and JSON.stringify(found.tank.content_state())!=JSON.stringify(data.content):found.tank.apply_content(data.content)
            found.data=data.duplicate(true);found.node.transform=_transform(data)
            if data.kind=="wall":_refresh_wall(found)
        if data.kind=="tank":found.data.water=WaterProfile.normalized(data.get("water",{}))
        retained.append(found)
    for row in objects:
        if not retained.has(row):row.node.hide();row.body.collision_layer=0;row.node.queue_free()
    objects=retained;selected=-1
    floor_style=int(state.floor_style);wall_style=int(state.wall_style)
    _finishes();_sync_panel()

func _remember() -> void:
    history.append(_state());if history.size()>20:history.pop_front()
    future.clear()

func _undo() -> void:
    if history.is_empty():return
    future.append(_state());_restore(history.pop_back());notice="已撤销。"

func _redo() -> void:
    if future.is_empty():return
    history.append(_state());_restore(future.pop_back());notice="已重做。"

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
    var data: Dictionary=objects[selected].data.duplicate(true)
    data.at=[snappedf(at.x,.25),snappedf(at.z,.25)]
    if not _valid_placement(data,objects,data.id):notice=placement_error;return false
    objects[selected].data=data;objects[selected].node.transform=_transform(data)
    _selection();_sync_panel();return true

func _rotate_selected(direction: float) -> bool:
    if selected<0:return false
    var data: Dictionary=objects[selected].data.duplicate(true);data.yaw+=(PI/2 if data.kind=="wall" else deg_to_rad(15))*direction
    if not _valid_placement(data,objects,data.id):notice="旋转后会碰到其他物件或墙。";return false
    _remember();objects[selected].data=data;objects[selected].node.transform=_transform(data);_selection();_sync_panel();return true

func _resize_selected(value: float) -> bool:
    if panel_sync or selected<0:return false
    var data: Dictionary=objects[selected].data.duplicate(true)
    if data.kind=="wall":data.length=snappedf(clampf(value,3 if data.get("door",false) else .5,18),.5)
    else:data.scale=clampf(value,.4,1.3)
    if not _valid_placement(data,objects,data.id):notice="放大后空间不足。";_sync_panel();return false
    _remember();objects[selected].data=data;objects[selected].node.transform=_transform(data)
    if data.kind=="wall":_refresh_wall(objects[selected])
    _selection();_sync_panel();return true

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
    if not _valid_placement(data,objects):notice=placement_error;return false
    _remember();objects.append(_create(data));selected=objects.size()-1;_set_tool("");_sync_panel();notice="已添加，可拖动调整位置。";return true

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
    if not _valid_placement(data,objects):notice=placement_error;return false
    data.id="wall-%d-%d" % [Time.get_unix_time_from_system(),id_serial];id_serial+=1
    _remember();objects.append(_create(data));selected=objects.size()-1;wall_anchor=null;_sync_panel()
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
    _remember();var row: Dictionary=objects[selected]
    row.node.hide();row.body.collision_layer=0;row.node.queue_free();objects.remove_at(selected);selected=-1;_sync_panel();notice="已删除，可撤销。"

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
    var input := Input.get_vector("hall_left","hall_right","hall_forward","hall_back")
    var direction: Vector3=player.basis*Vector3(input.x,0,input.y)
    var speed := 5.0 if Input.is_physical_key_pressed(KEY_SHIFT) else 2.7
    player.velocity.x=direction.x*speed;player.velocity.z=direction.z*speed
    if not player.is_on_floor():player.velocity.y-=18*delta
    else:player.velocity.y=0
    player.move_and_slide()

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
    if event is InputEventMouseMotion:
        pointer=event.position*Vector2(viewport.size)/canvas.size
        if editing:
            if panning:
                var right := editor_camera.global_basis.x;var forward := Vector3(right.z,0,-right.x)
                camera_target+=(-right*event.relative.x+forward*event.relative.y)*view_size/1080;_camera()
            if orbiting:yaw-=event.relative.x*.005;pitch=clampf(pitch+event.relative.y*.004,.4,1.35);_camera()
            if dragging and selected>=0:
                var at: Variant=_floor_hit(pointer)
                if at!=null:_move_selected(at+drag_offset)
            _preview(_floor_hit(pointer))
    if not event is InputEventMouseButton:return
    pointer=event.position*Vector2(viewport.size)/canvas.size
    if event.button_index==MOUSE_BUTTON_RIGHT:
        if editing:orbiting=event.pressed
        elif event.pressed:looking=true;Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
    if event.button_index==MOUSE_BUTTON_MIDDLE and editing:panning=event.pressed
    if not editing:
        if event.button_index==MOUSE_BUTTON_LEFT and event.pressed:selected=_pick(pointer);_sync_panel()
        return
    if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
        view_size=clampf(view_size*(.9 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.1),10,65);_camera();_preview(_floor_hit(pointer))
    if event.button_index==MOUSE_BUTTON_LEFT:
        if not event.pressed:dragging=false;return
        var at: Variant=_floor_hit(pointer)
        if pending_kind=="parcel":
            if at!=null:_expand_at(at);_preview(_floor_hit(pointer))
        elif pending_kind=="wall":
            if at!=null:
                if wall_anchor==null:
                    var marker := AABB(Vector3(at.x-.01,0,at.z-.01),Vector3(.02,.1,.02))
                    if Footprint.contains(parcels,marker):wall_anchor=at;notice="已选起点，点击终点建墙；Esc 取消。"
                    else:notice="起点需要在已扩建地基内。"
                else:_commit_wall(wall_anchor,at)
                _preview(at)
        elif pending_kind!="":
            if at!=null:_add_at(pending_kind,at)
        else:
            selected=_pick(pointer);_sync_panel()
            if selected>=0 and at!=null:_remember();drag_offset=objects[selected].node.position-at;dragging=true

func _unhandled_key_input(event: InputEvent) -> void:
    if active_editor!=null or not editing or not event is InputEventKey or not event.pressed or event.echo:return
    if event.ctrl_pressed:
        if event.keycode==KEY_Z:_undo()
        if event.keycode==KEY_Y:_redo()
        if event.keycode==KEY_S:_save_layout()
        return
    if pending_kind!="":
        if event.keycode in [KEY_Q,KEY_E] and pending_kind in ["tank","bench","plinth"]:
            pending_yaw+=deg_to_rad(15)*(-1 if event.keycode==KEY_Q else 1);_preview(_floor_hit(pointer))
        return
    if event.keycode==KEY_Q:_rotate_selected(-1)
    if event.keycode==KEY_E:_rotate_selected(1)
    if event.keycode==KEY_DELETE:_delete_selected()

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
    add_child(active_editor);Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    return true

func _apply_content_editor(state: Dictionary) -> void:
    for row in objects:
        if row.data.id!=editor_object_id:continue
        _remember();row.tank.apply_content(state);row.data.content=state.duplicate(true);break
    _close_content_editor();notice="缸内布景已应用；保存大厅可一起保存。"

func _close_content_editor() -> void:
    if is_instance_valid(active_editor):active_editor.hide();active_editor.queue_free()
    active_editor=null
    if is_instance_valid(editor_backdrop):editor_backdrop.hide();editor_backdrop.queue_free()
    for child in editor_hidden:
        if is_instance_valid(child):child.show()
    editor_hidden.clear();side.visible=editing;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    get_window().content_scale_size=Vector2i(1920,1080)
    DisplayServer.window_set_title("潮汐馆 · 可编辑 3D 大厅")
    editor_camera.current=editing;eye.current=not editing

func _button(parent: Control,text: String,at: Vector2,width: float,callback: Callable) -> Button:
    var button := Button.new();button.text=text;button.position=at;button.custom_minimum_size=Vector2(width,40)
    button.focus_mode=Control.FOCUS_NONE;button.pressed.connect(callback);parent.add_child(button);return button

func _label(parent: Control,text: String,at: Vector2,size:=18) -> Label:
    var label := Label.new();label.text=text;label.position=at;label.add_theme_font_size_override("font_size",size);label.modulate=Color("d3e0d7");parent.add_child(label);return label

func _ui() -> void:
    var header := ColorRect.new();header.name="HallHeader";header.color=Color("102a34");header.position=Vector2.ZERO;header.size=Vector2(1920,96);add_child(header)
    _label(header,"潮汐馆  /  可编辑 3D 大厅",Vector2(30,12),28)
    _label(header,"室内建造 · 地块扩建 / 展缸 / 隔墙 · 独立保存",Vector2(32,55),17)
    _button(header,"返回海岸",Vector2(1725,26),160,_request_return)
    mode_button=_button(header,"切换逛馆  Tab",Vector2(1000,26),180,func():_mode(not editing))
    _button(header,"展缸水体 / 近景",Vector2(780,26),200,_open_water_panel)
    _button(header,"保存大厅",Vector2(1195,26),150,_save_layout)
    _button(header,"读取大厅",Vector2(1360,26),150,func():_load_layout(save_path))
    _button(header,"撤销",Vector2(1525,26),85,_undo)
    _button(header,"重做",Vector2(1620,26),85,_redo)
    side=ColorRect.new();side.color=Color("14313b");side.position=Vector2(1570,108);side.size=Vector2(330,866);add_child(side)
    _label(side,"大厅建造",Vector2(18,10),24)
    parcel_label=_label(side,"",Vector2(18,47),17)
    _button(side,"＋ 扩建相邻地块  6×7 m",Vector2(18,77),294,func():_set_tool("parcel"))
    tank_size_choice=OptionButton.new();tank_size_choice.position=Vector2(18,127);tank_size_choice.size=Vector2(294,36)
    for label in ["小缸  3×1.5 m","中缸  3.9×1.95 m","标准缸  6×3 m"]:tank_size_choice.add_item(label)
    tank_size_choice.select(1);side.add_child(tank_size_choice)
    _button(side,"＋ 放置所选规格展缸",Vector2(18,169),294,func():_set_tool("tank"))
    wall_choice=OptionButton.new();wall_choice.position=Vector2(18,218);wall_choice.size=Vector2(294,36);wall_choice.add_item("实心隔墙  高 3.2 m");wall_choice.add_item("门洞隔墙  通道宽 1.2 m")
    wall_choice.item_selected.connect(func(index):wall_with_door=index==1;wall_anchor=null);side.add_child(wall_choice)
    _button(side,"＋ 画隔墙  起点 → 终点",Vector2(18,260),294,func():_set_tool("wall"))
    _button(side,"＋ 长凳",Vector2(18,309),142,func():_set_tool("bench"))
    _button(side,"＋ 展示台",Vector2(170,309),142,func():_set_tool("plinth"))
    _button(side,"选择 / 取消建造  Esc",Vector2(18,358),294,func():_set_tool(""))
    tool_label=_label(side,"选择物件进行编辑",Vector2(18,403),17)
    detail=_label(side,"未选中物件",Vector2(18,434),18)
    _button(side,"Q  左转",Vector2(18,490),142,func():_rotate_selected(-1))
    _button(side,"E  右转",Vector2(170,490),142,func():_rotate_selected(1))
    _label(side,"物件倍率 / 隔墙长度（米）",Vector2(18,536),17)
    size_spin=SpinBox.new();size_spin.position=Vector2(18,562);size_spin.custom_minimum_size=Vector2(294,34);size_spin.min_value=.4;size_spin.max_value=1.3;size_spin.step=.05;size_spin.value=1
    size_spin.value_changed.connect(_resize_selected);side.add_child(size_spin)
    _label(side,"展示海鱼数量（0～15）",Vector2(18,603),17)
    fish_spin=SpinBox.new();fish_spin.position=Vector2(18,629);fish_spin.custom_minimum_size=Vector2(294,34);fish_spin.max_value=15;fish_spin.step=1
    fish_spin.value_changed.connect(_fish_count_changed);side.add_child(fish_spin)
    _button(side,"编辑选中缸内的沙子与摆件",Vector2(18,674),294,_open_content_editor)
    _button(side,"删除选中物件",Vector2(18,720),294,_delete_selected)
    _button(side,"更换地砖",Vector2(18,766),142,func():_remember();floor_style=(floor_style+1)%3;_finishes())
    _button(side,"更换墙色",Vector2(170,766),142,func():_remember();wall_style=(wall_style+1)%3;_finishes())
    _button(side,"俯视全馆",Vector2(18,812),142,func():pitch=1.30;yaw=.01;_fit_hall())
    _button(side,"斜视全馆",Vector2(170,812),142,func():pitch=.83;yaw=.48;_fit_hall())
    var footer := ColorRect.new();footer.color=Color("102a34");footer.position=Vector2(0,995);footer.size=Vector2(1920,85);add_child(footer)
    status=_label(footer,notice,Vector2(30,10),18)
    _label(footer,"编辑：右键环绕 · 中键平移 · 滚轮缩放 · Q/E 转向 · Esc 取消 · Delete 删除   |   Tab 逛馆：WASD 行走 · 右键看向 · Shift 加速",Vector2(30,45),16)
    water_panel=load("res://scripts/aquarium/TankWaterPanel.gd").new();add_child(water_panel);water_panel.hide()
    water_panel.changed.connect(_water_changed);water_panel.preset_selected.connect(_water_preset)
    water_panel.interaction_started.connect(func():if not water_drag:_remember();water_drag=true)
    water_panel.interaction_ended.connect(func():water_drag=false)
    water_panel.inspect_requested.connect(_start_inspection);water_panel.return_requested.connect(_stop_inspection)
    water_panel.next_fish_requested.connect(func():inspection_fish+=1;_start_inspection(false))

func _open_water_panel() -> void:
    if selected<0 or objects[selected].tank==null:
        for i in objects.size():
            if objects[i].tank!=null:selected=i;break
    if selected<0 or objects[selected].tank==null:notice="先放置一个展缸，再调整水体。";return
    _set_tool("");dragging=false;_sync_panel();water_panel.show()

func _water_changed(key: String,value: Variant) -> void:
    if selected<0 or objects[selected].tank==null:return
    var config: Dictionary=objects[selected].data.water.duplicate(true);config[key]=value
    if not WaterProfile.valid(config):return
    if not water_drag:_remember()
    objects[selected].data.water=config
    notice="已调整这个展缸的水体外观；可撤销并保存。"

func _water_preset(index: int) -> void:
    if selected<0 or objects[selected].tank==null:return
    _remember();objects[selected].data.water=WaterProfile.preset(index);_sync_panel()

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
    _remember();objects[selected].data.fish_count=int(value);objects[selected].tank.set_fish_count(int(value));notice="已调整这个展缸的展示海鱼数量。"

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

func _process(delta: float) -> void:
    if is_instance_valid(water_renderer):water_renderer.sync(objects,delta)
    if inspecting:_update_inspection()
    statistics_clock+=delta
    if statistics_clock>.15:statistics_clock=0;status.text=notice

func _finite_number(value: Variant) -> bool:
    return (value is int or value is float) and is_finite(float(value))

func _valid_content(data: Variant) -> bool:
    if not data is Dictionary:return false
    if data.is_empty():return true
    if data.get("schema_version")!=3 or data.get("sand")!="fine_sand":return false
    if not data.get("grid") is Array or data.grid.size()!=2 or data.grid[0]!=129 or data.grid[1]!=65:return false
    if not data.get("heights") is Array or data.heights.size()!=8385 or not data.get("materials") is Array or data.materials.size()!=8385:return false
    for h in data.heights:
        if not _finite_number(h) or h<0 or h>.24:return false
    for m in data.materials:
        if not _finite_number(m) or m!=int(m) or m<0 or m>4:return false
    if not data.get("rocks") is Array or data.rocks.size()>80:return false
    var ids: Array=[]
    for path in ["res://assets/aquascape-v5/catalog.json","res://assets/aquascape-decor-v1/catalog.json"]:
        for row in JSON.parse_string(FileAccess.get_file_as_string(path)).assets:
            if not row.get("animated",false):ids.append(row.id)
    for row in data.rocks:
        if not row is Dictionary or row.get("id") not in ids or not row.get("position") is Array or row.position.size()!=3:return false
        for p in row.position:
            if not _finite_number(p):return false
        if absf(row.position[0])>.61 or absf(row.position[2])>.31 or row.position[1]< -.5 or row.position[1]>.5:return false
        if not _finite_number(row.get("scale")) or row.scale<.04 or row.scale>3 or not _finite_number(row.get("yaw")):return false
    var choice: Variant=data.get("selected_substrate",0)
    return _finite_number(choice) and choice==int(choice) and choice>=0 and choice<=4

func _valid_state(data: Variant) -> bool:
    if not data is Dictionary:return false
    var version: Variant=data.get("schema_version")
    if not _finite_number(version) or version!=int(version) or int(version) not in [1,2] or not data.get("objects") is Array or data.objects.size()>MAX_OBJECTS:return false
    var cells: Array=Footprint.initial()
    if data.schema_version==2:
        if not Footprint.valid(data.get("parcels")):return false
        cells=data.parcels
    for key in ["floor_style","wall_style"]:
        if not _finite_number(data.get(key)) or data[key]!=int(data[key]) or data[key]<0 or data[key]>2:return false
    var ids: Array=[];var rows: Array=[];var tanks := 0
    for row in data.objects:
        if not row is Dictionary or not row.get("id") is String or row.id.is_empty() or row.id in ids:return false
        if row.get("kind") not in ["tank","bench","plinth","wall"] or not row.get("name") is String or row.name.length()>80:return false
        if data.schema_version==1 and row.kind=="wall":return false
        if not row.get("at") is Array or row.at.size()!=2:return false
        for x in row.at:
            if not _finite_number(x):return false
        if not _finite_number(row.get("yaw")) or not _finite_number(row.get("scale")) or row.scale<.4 or row.scale>1.3:return false
        if row.kind=="wall":
            if not _finite_number(row.get("length")) or not row.get("door") is bool or row.scale!=1:return false
            if row.length<(3 if row.door else .5) or row.length>18:return false
            if absf(sin(float(row.yaw)*2))>.0001:return false
        if row.kind=="tank":
            tanks+=1
            if row.has("water") and not WaterProfile.valid(row.water):return false
            if tanks>MAX_TANKS or not _finite_number(row.get("fish_count")) or row.fish_count!=int(row.fish_count) or row.fish_count<0 or row.fish_count>15 or not _valid_content(row.get("content")):return false
        if not _valid_placement(row,rows,"",cells):return false
        rows.append(row);ids.append(row.id)
    return true

func _write_layout(path: String) -> bool:
    var state := _state()
    if not _valid_state(state):return false
    var file := FileAccess.open(path+".tmp",FileAccess.WRITE)
    if file==null:return false
    file.store_string(JSON.stringify(state,"",true,true));file.close()
    return DirAccess.rename_absolute(path+".tmp",path)==OK

func _save_layout() -> void:
    if read_only:notice="当前为只读预览，不写入游戏存档。";return
    var okay := _write_layout(save_path)
    if okay:saved_digest=JSON.stringify(_state()).sha256_text()
    notice="大厅与全部缸内布景已保存。" if okay else "保存失败，当前布局仍保留。"

func _load_layout(path: String) -> bool:
    if not FileAccess.file_exists(path):notice="还没有大厅存档。";return false
    var state: Variant=JSON.parse_string(FileAccess.get_file_as_string(path))
    if not _valid_state(state):notice="存档无效，当前布局保持不变。";return false
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
