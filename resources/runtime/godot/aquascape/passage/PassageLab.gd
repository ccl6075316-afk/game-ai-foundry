extends Control
## Isolated playable pilot. Never loads or modifies the normal hall/game save.
const Route=preload("res://scripts/aquarium/passage/PassageRoute.gd")
var session=preload("res://scripts/aquarium/passage/PassageSession.gd").new()
var save_path := "user://aquarium-passage-lab-v1.json"
var read_only := false
var viewport: SubViewport
var canvas: TextureRect
var world: Node3D
var player: CharacterBody3D
var eye: Camera3D
var editor_camera: Camera3D
var handles: Node3D
var preview_cover: Node3D
var editing := true
var drawing := false
var dragging := false
var orbiting := false
var looking := false
var panel_sync := false
var selected := 2
var draw_height := 0.0
var draft: Dictionary={}
var yaw := .58
var pitch := .62
var view_size := 25.0
var notice := "示例已就绪：拖动控制点，或进入通道实际走一遍。"
var side: ColorRect
var status_label: Label
var mode_button: Button
var section_choice: OptionButton
var width_spin: SpinBox
var height_spin: SpinBox
var x_spin: SpinBox
var y_spin: SpinBox
var z_spin: SpinBox
var point_label: Label

func _ready() -> void:
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    get_window().content_scale_size=Vector2i(1920,1080)
    DisplayServer.window_set_title("潮汐馆 · 路线式透明通道试建")
    viewport=SubViewport.new();viewport.size=Vector2i(1920,1080);viewport.own_world_3d=true
    viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;add_child(viewport)
    canvas=TextureRect.new();canvas.texture=viewport.get_texture();canvas.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    canvas.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;canvas.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    canvas.gui_input.connect(canvas_input);add_child(canvas)
    world=preload("res://scripts/aquarium/passage/PassageWorld.gd").new();viewport.add_child(world)
    handles=Node3D.new();world.add_child(handles)
    preview_cover=preload("res://scripts/aquarium/passage/PassageMesh.gd").new();world.add_child(preview_cover);preview_cover.hide()
    editor_camera=Camera3D.new();editor_camera.projection=Camera3D.PROJECTION_ORTHOGONAL;editor_camera.near=.04;editor_camera.far=130;world.add_child(editor_camera)
    player=CharacterBody3D.new();player.collision_layer=2;player.collision_mask=1;player.floor_snap_length=.3
    player.floor_max_angle=deg_to_rad(35);world.add_child(player)
    var shape := CollisionShape3D.new();var capsule := CapsuleShape3D.new();capsule.radius=.24;capsule.height=1.7;shape.shape=capsule;player.add_child(shape)
    eye=Camera3D.new();eye.position.y=.73;eye.fov=75;eye.near=.04;eye.far=100;player.add_child(eye)
    preload("res://scripts/aquarium/passage/PassagePanel.gd").new().build(self)
    if FileAccess.file_exists(save_path):
        var error := session.load_route(save_path)
        if not error.is_empty():notice="试建存档未载入："+error
    apply_route();editor_camera.current=true;update_camera();spawn_player()

func apply_route() -> void:
    preview_cover.hide();world.cover.show();world.apply_route(session.route)
    selected=clampi(selected,0,session.route.points.size()-1)
    update_handles();sync_panel()
    if not editing:spawn_player()

func commit(candidate: Dictionary) -> bool:
    var error := session.commit(candidate)
    if not error.is_empty():notice=error;sync_panel();return false
    drawing=false;dragging=false;draft={};apply_route();notice="通道已更新；可以实际行走、撤销或保存。";return true

func update_camera() -> void:
    editor_camera.size=view_size
    var target := Vector3(2,2,0)
    editor_camera.position=target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*45
    editor_camera.look_at(target)

func set_edit_view(top_view: bool) -> void:
    if not editing:toggle_mode()
    pitch=1.54 if top_view else .62;yaw=0.0 if top_view else .58;update_camera()

func update_handles() -> void:
    for child in handles.get_children():handles.remove_child(child);child.queue_free()
    var data: Dictionary=draft if not draft.is_empty() else session.route
    for i in data.points.size():
        var marker := MeshInstance3D.new();var mesh := SphereMesh.new();mesh.radius=.17;mesh.height=.34;mesh.radial_segments=12;mesh.rings=6
        marker.mesh=mesh;marker.position=Route.point(data.points[i])+Vector3.UP*.1
        var material := StandardMaterial3D.new();material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
        material.albedo_color=Color("ffcd72") if i==selected else Color("6fe3e7");material.no_depth_test=true
        marker.material_override=material;handles.add_child(marker)
    if data.points.size()>1:
        var line := ImmediateMesh.new();line.surface_begin(Mesh.PRIMITIVE_LINES)
        for i in data.points.size()-1:
            line.surface_add_vertex(Route.point(data.points[i])+Vector3.UP*.12)
            line.surface_add_vertex(Route.point(data.points[i+1])+Vector3.UP*.12)
        line.surface_end();var visual := MeshInstance3D.new();visual.mesh=line
        var material := StandardMaterial3D.new();material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;material.no_depth_test=true
        material.albedo_color=Color("6fe3e7") if Route.validate(data).is_empty() else Color("ef9576")
        visual.material_override=material;handles.add_child(visual)
    handles.visible=editing

func sync_panel() -> void:
    if not is_instance_valid(point_label):return
    panel_sync=true
    var data: Dictionary=draft if not draft.is_empty() else session.route
    section_choice.select(0 if data.section=="round" else 1)
    width_spin.set_value_no_signal(data.width);height_spin.set_value_no_signal(data.height)
    var has_point: bool=selected>=0 and selected<data.points.size()
    point_label.text="控制点 %d / %d" % [selected+1,data.points.size()] if has_point else "点击地面添加下一个控制点"
    if has_point:
        x_spin.set_value_no_signal(data.points[selected][0]);y_spin.set_value_no_signal(draw_height if drawing else data.points[selected][1]);z_spin.set_value_no_signal(data.points[selected][2])
    if drawing:y_spin.set_value_no_signal(draw_height)
    x_spin.editable=has_point;z_spin.editable=has_point
    mode_button.text="进入通道  Tab" if editing else "返回路线编辑  Tab"
    panel_sync=false

func _configure(key: String,value: Variant) -> void:
    if panel_sync:return
    var candidate: Dictionary=(draft if drawing else session.route).duplicate(true);candidate[key]=value
    if drawing:draft=candidate;preview_draft()
    else:commit(candidate)

func section_changed(index: int) -> void:_configure("section","round" if index==0 else "arch")
func width_changed(value: float) -> void:_configure("width",value)
func height_changed(value: float) -> void:_configure("height",value)
func point_height_changed(value: float) -> void:_point_value(1,value)
func point_x_changed(value: float) -> void:_point_value(0,value)
func point_z_changed(value: float) -> void:_point_value(2,value)

func _point_value(axis: int,value: float) -> void:
    if panel_sync:return
    if drawing and axis==1:draw_height=value;return
    var candidate: Dictionary=(draft if drawing else session.route).duplicate(true)
    if selected<0 or selected>=candidate.points.size():return
    candidate.points[selected][axis]=value
    if drawing:draft=candidate;preview_draft()
    else:commit(candidate)

func start_drawing() -> void:
    if not editing:toggle_mode()
    draft=session.route.duplicate(true);draft.points=[];drawing=true;selected=-1;draw_height=0
    pitch=1.54;yaw=0;update_camera();preview_draft()
    notice="点击放控制点；Y 框设置新点标高；两端分别到左右平台区，再点完成路线。"

func finish_drawing() -> void:
    if not drawing:notice="先点“画新路线”，或直接拖动现有控制点。";return
    commit(draft)

func preview_draft() -> void:
    update_handles();sync_panel()
    var error := Route.validate(draft)
    notice="草稿可建，点击完成路线。" if error.is_empty() else "草稿："+error
    if error.is_empty():
        preview_cover.rebuild(draft,false);preview_cover.show();world.cover.hide()
    else:preview_cover.hide();world.cover.show()

func cancel_draft() -> void:
    drawing=false;dragging=false;draft={};apply_route();notice="已取消草稿，保留已完成的路线。"

func insert_point() -> void:
    if drawing or selected<0:return
    var candidate: Dictionary=session.route.duplicate(true)
    if candidate.points.size()>=Route.MAX_POINTS:notice="本轮最多 12 个控制点。";return
    var index := mini(selected,candidate.points.size()-2)
    candidate.points.insert(index+1,Route.array(Route.point(candidate.points[index]).lerp(Route.point(candidate.points[index+1]),.5)))
    if commit(candidate):selected=index+1;update_handles();sync_panel()

func delete_point() -> void:
    if drawing or selected<0:return
    var candidate: Dictionary=session.route.duplicate(true)
    if candidate.points.size()<=2:notice="路线至少保留两个控制点。";return
    candidate.points.remove_at(selected);commit(candidate)

func undo() -> void:
    if drawing or dragging:cancel_draft();return
    if session.undo():apply_route();notice="已撤销。"

func redo() -> void:
    if drawing or dragging:cancel_draft();return
    if session.redo():apply_route();notice="已重做。"

func save_route() -> void:
    if drawing or dragging:notice="请先完成或取消草稿，再保存。";return
    if read_only:notice="审核只读会话，不写入试建存档。";return
    notice="试建路线已保存，未修改大厅和鱼库存。" if session.save(save_path) else "试建保存失败，当前路线仍保留。"

func load_route() -> void:
    var error := session.load_route(save_path)
    if not error.is_empty():notice=error;return
    drawing=false;dragging=false;draft={};apply_route();notice="已读取试建路线。"

func reset_route() -> void:commit(Route.initial())

func toggle_mode() -> void:
    if drawing or dragging:cancel_draft()
    editing=not editing;side.visible=editing;handles.visible=editing
    editor_camera.current=editing;eye.current=not editing;looking=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    if not editing:spawn_player()
    sync_panel()

func spawn_player() -> void:
    if world.path.is_empty():return
    player.position=world.path[0]+Vector3(0,.88,0);player.velocity=Vector3.ZERO
    var direction: Vector3=world.path[1]-world.path[0];player.rotation.y=atan2(-direction.x,-direction.z);eye.rotation.x=0
    notice="已回到入口；WASD 行走，右键看向，R 随时复位。"

func walk_step(direction: Vector3,delta: float) -> void:
    var speed := 4.5 if Input.is_physical_key_pressed(KEY_SHIFT) else 3.0
    player.velocity.x=direction.x*speed;player.velocity.z=direction.z*speed
    player.velocity.y=0 if player.is_on_floor() else player.velocity.y-18*delta
    player.move_and_slide()
    if player.position.y< -3:spawn_player()

func _physics_process(delta: float) -> void:
    if editing:return
    var input := Vector2(float(Input.is_physical_key_pressed(KEY_D))-float(Input.is_physical_key_pressed(KEY_A)),float(Input.is_physical_key_pressed(KEY_S))-float(Input.is_physical_key_pressed(KEY_W)))
    walk_step(player.basis*Vector3(input.normalized().x,0,input.normalized().y),delta)

func _project(position_value: Vector2,height: float) -> Variant:
    var screen := position_value*Vector2(viewport.size)/canvas.size
    var origin := editor_camera.project_ray_origin(screen);var direction := editor_camera.project_ray_normal(screen)
    if absf(direction.y)<.001:return null
    return origin+direction*((height-origin.y)/direction.y)

func canvas_input(event: InputEvent) -> void:
    if not editing:
        if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_RIGHT:looking=event.pressed;Input.mouse_mode=Input.MOUSE_MODE_CAPTURED if looking else Input.MOUSE_MODE_VISIBLE
        return
    if event is InputEventMouseMotion:
        if orbiting:yaw-=event.relative.x*.004;pitch=clampf(pitch+event.relative.y*.004,.25,1.54);update_camera()
        if dragging:
            var hit: Variant=_project(event.position,draft.points[selected][1])
            if hit!=null:
                draft.points[selected][0]=snappedf(clampf(hit.x,-14,14),.1);draft.points[selected][2]=snappedf(clampf(hit.z,-4,4),.1);preview_draft()
    if not event is InputEventMouseButton:return
    if event.button_index==MOUSE_BUTTON_RIGHT:orbiting=event.pressed
    if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:view_size=clampf(view_size*(.9 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.1),16,42);update_camera()
    if event.button_index!=MOUSE_BUTTON_LEFT:return
    if not event.pressed:
        if dragging:
            if not commit(draft):dragging=false;draft={};apply_route()
        return
    if drawing:
        if draft.points.size()>=Route.MAX_POINTS:notice="本轮最多 12 个控制点。";return
        var hit: Variant=_project(event.position,draw_height)
        if hit!=null:draft.points.append([snappedf(clampf(hit.x,-14,14),.1),draw_height,snappedf(clampf(hit.z,-4,4),.1)]);selected=draft.points.size()-1;preview_draft()
        return
    var screen: Vector2=event.position*Vector2(viewport.size)/canvas.size
    var best := 28.0;var found := -1
    for i in session.route.points.size():
        var distance: float=screen.distance_to(editor_camera.unproject_position(Route.point(session.route.points[i])+Vector3.UP*.1))
        if distance<best:best=distance;found=i
    if found>=0:selected=found;draft=session.route.duplicate(true);dragging=true;update_handles();sync_panel()

func _input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and not editing and looking:
        player.rotation.y-=event.relative.x*.003;eye.rotation.x=clampf(eye.rotation.x-event.relative.y*.003,-1.4,1.4)
    if event is InputEventMouseButton and not event.pressed and event.button_index==MOUSE_BUTTON_RIGHT:orbiting=false;looking=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode==KEY_TAB:toggle_mode();get_viewport().set_input_as_handled()
        if event.keycode==KEY_ESCAPE:
            if drawing or dragging:cancel_draft()
            looking=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
        if event.keycode==KEY_R and not editing:spawn_player()
        if editing and event.ctrl_pressed and event.keycode==KEY_Z:undo()
        if editing and event.ctrl_pressed and event.keycode==KEY_Y:redo()
        if event.ctrl_pressed and event.keycode==KEY_S:save_route()

func _process(_delta: float) -> void:
    if is_instance_valid(status_label):status_label.text=notice

func _exit_tree() -> void:
    Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
