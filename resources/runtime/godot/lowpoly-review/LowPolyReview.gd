extends Control
## Interactive review only: assembles retained low-poly recipes in memory.
const REVIEW="res://../plans/reviews/fish-lowpoly-v2"
var factory
var entries=[]
var cameras=[]
var viewports=[]
var panels:Array[SubViewportContainer]=[]
var active_panel=-1
var pan_mode=true
var last_zoom_trace={}
var paused=false
var rotating=false
var dragging=false
var panning=false
var yaw=0.0
var pitch=0.0
var zoom=1.0
var pan=Vector3.ZERO
var head_focus=false
var pause_button:Button
var rotation_button:Button
var pan_button:Button
var status:Label
var initial_counts=[]

func button(row:HBoxContainer,title:String,callback:Callable) -> Button:
    var b=Button.new();b.text=title;b.pressed.connect(callback);row.add_child(b);return b

func _ready() -> void:
    pan_mode=not ("--rotate-left" in OS.get_cmdline_user_args())
    DisplayServer.window_set_title("梭鲈四版本对照 · 原版 / 992 / 2991 / 6000 三角面")
    var background=ColorRect.new();background.color=Color("101e29");background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);background.mouse_filter=Control.MOUSE_FILTER_IGNORE;add_child(background)
    var margin=MarginContainer.new();margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    for side in ["left","right","top","bottom"]:margin.add_theme_constant_override("margin_"+side,12)
    add_child(margin)
    var layout=VBoxContainer.new();margin.add_child(layout)
    var title=Label.new();title.text="梭鲈 · 整鱼面数对照";title.add_theme_font_size_override("font_size",24);layout.add_child(title)
    var help=Label.new();help.text=("左键：平移（可切换旋转）" if pan_mode else "左键：旋转（可切换平移）")+"  右键/中键/Shift+左键：平移  滚轮：围绕指针缩放  WASD/方向键：平移  空格：暂停";layout.add_child(help)
    var row=HBoxContainer.new();layout.add_child(row)
    pause_button=button(row,"暂停游动",toggle_pause)
    pan_button=button(row,"平移模式",func():pan_mode=pan_button.button_pressed)
    pan_button.toggle_mode=true;pan_button.button_pressed=pan_mode
    pan_button.tooltip_text="开启时左键拖动平移；关闭时左键拖动旋转。右键和中键始终平移。"
    rotation_button=button(row,"自动旋转：关",func():rotating=not rotating;rotation_button.text="自动旋转：开" if rotating else "自动旋转：关")
    button(row,"整鱼",func():head_focus=false;reset_view())
    button(row,"嘴部近景",func():head_focus=true;reset_view())
    button(row,"侧面",func():yaw=0;pitch=0;update_cameras())
    button(row,"正面",func():yaw=PI/2;pitch=0;update_cameras())
    button(row,"俯视",func():yaw=0;pitch=1.5;update_cameras())
    button(row,"复位",reset_view)
    var actions=OptionButton.new()
    for name in ["游动 Swim","转向 Turn","上浮 Ascend","下潜 Dive"]:actions.add_item(name)
    actions.item_selected.connect(func(index:int):
        for entry in entries:entry.controller.set_action(["Swim","Turn","Ascend","Dive"][index],true))
    row.add_child(actions)
    var grid=GridContainer.new();grid.columns=2;grid.size_flags_vertical=Control.SIZE_EXPAND_FILL;layout.add_child(grid)
    status=Label.new();status.text="正在准备四个版本……";layout.add_child(status)
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var transport=preload("res://scripts/aquarium/lowpoly_review/LowPolyFishTransport.gd").new()
    for budget in [0,1000,3000,6000]:
        var column=VBoxContainer.new();column.size_flags_horizontal=Control.SIZE_EXPAND_FILL;column.size_flags_vertical=Control.SIZE_EXPAND_FILL;grid.add_child(column)
        var label=Label.new();label.add_theme_font_size_override("font_size",18);column.add_child(label)
        var container=SubViewportContainer.new();container.stretch=true;container.size_flags_horizontal=Control.SIZE_EXPAND_FILL;container.size_flags_vertical=Control.SIZE_EXPAND_FILL
        container.mouse_filter=Control.MOUSE_FILTER_STOP;column.add_child(container);panels.append(container)
        var viewport=SubViewport.new();viewport.own_world_3d=true;viewport.size=Vector2i(760,400);container.add_child(viewport);viewports.append(viewport)
        var world=Node3D.new();viewport.add_child(world)
        var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("183b4a");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.8;world.add_child(env)
        var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-30,0);world.add_child(light)
        var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=100;world.add_child(camera);camera.current=true;cameras.append(camera)
        factory._add_fish(world,"zander",float(factory.profiles.zander.real_length_cm)/100.,factory.profiles.zander)
        var entry=factory.fish[-1];entry.player.pause();entry.carrier.transform=Transform3D.IDENTITY;entries.append(entry)
        var recipe_hash=""
        if budget>0:
            var path=REVIEW.path_join("low-"+str(budget)+".json");var data=JSON.parse_string(FileAccess.get_file_as_string(path))
            transport.apply(entry.model,data);recipe_hash=FileAccess.get_sha256(path)
        var triangles=0;var vertices=0
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            if not mesh.visible:continue
            for si in mesh.mesh.get_surface_count():
                var a=mesh.mesh.surface_get_arrays(si);triangles+=a[Mesh.ARRAY_INDEX].size()/3;vertices+=a[Mesh.ARRAY_VERTEX].size()
        assert(triangles=={0:212360,1000:992,3000:2991,6000:6000}[budget])
        initial_counts.append({"budget":budget,"triangles":triangles,"vertices":vertices,"recipe_sha256":recipe_hash})
        label.text=("原版" if budget==0 else "实验候选")+" · "+str(triangles)+" 三角面 / "+str(vertices)+" 顶点"
    status.text="四个版本同步相机、光照与动作。实验候选的嘴唇折痕、局部穿插尚未修复；正式鱼未替换。"
    update_cameras()
    for frame in 12:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var directory=ProjectSettings.globalize_path(REVIEW).simplify_path()
    assert(directory.begins_with(ProjectSettings.globalize_path("res://../plans/reviews").simplify_path()+"/"))
    var screenshot=directory.path_join("interactive.png")
    get_viewport().get_texture().get_image().save_png(screenshot)
    var record={"schema_version":1,"status":"running","next_action":"human_review","accepted":false,"production_assets_changed":false,"pid":OS.get_process_id(),"scene":"res://scenes/fish_lowpoly_review.tscn","counts":initial_counts,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"transport_sha256":FileAccess.get_sha256("res://scripts/aquarium/lowpoly_review/LowPolyFishTransport.gd"),"screenshot_sha256":FileAccess.get_sha256(screenshot),"navigation":"Root-viewport input; left-pan default, right/middle/shift-left pan, cursor-anchored zoom, WASD/arrows pan.","scope":"Interactive candidate review, no final fish acceptance or performance claim."}
    var file=FileAccess.open(directory.path_join("interactive.validation.json"),FileAccess.WRITE);file.store_string(JSON.stringify(record,"  "));file.close()
    print("LOWPOLY_INTERACTIVE_READY ",JSON.stringify(initial_counts))

func _process(delta:float) -> void:
    for entry in entries:
        if not paused:entry.controller.step(minf(delta,.05))
        entry.carrier.transform=Transform3D.IDENTITY
    if rotating:yaw+=delta*.3
    if not cameras.is_empty():
        var horizontal=int(Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT))-int(Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT))
        var vertical=int(Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN))-int(Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP))
        if horizontal!=0 or vertical!=0:move_pan(Vector2(horizontal,vertical)*350.*delta,0)
    if not entries.is_empty():update_cameras()

func toggle_pause() -> void:
    paused=not paused;pause_button.text="继续游动" if paused else "暂停游动"

func reset_view() -> void:
    yaw=0;pitch=0;zoom=1;pan=Vector3.ZERO;update_cameras()

func update_cameras() -> void:
    if entries.is_empty():return
    var center=Vector3.ZERO;var size=float(entries[0].length_m)*.8
    if head_focus:
        var lips=entries[0].model.find_child("Source_lips139",true,false) as MeshInstance3D
        var box=lips.global_transform*lips.get_aabb();center=box.get_center();size=box.size.length()*1.2
    center+=pan
    var direction=Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))
    for camera in cameras:
        camera.size=size*zoom;camera.position=center+direction*2.;camera.look_at(center)

func panel_at(position:Vector2) -> int:
    for i in panels.size():
        if panels[i].get_global_rect().has_point(position):return i
    return -1

func move_pan(relative:Vector2,index:int) -> void:
    var camera=cameras[index]
    pan+=(-camera.global_basis.x*relative.x+camera.global_basis.y*relative.y)*camera.size/maxf(panels[index].size.y,1.)

func cursor_world(position:Vector2,index:int) -> Vector3:
    var local=position-panels[index].get_global_rect().position
    var normalized=local/panels[index].size-Vector2(.5,.5)
    var camera=cameras[index]
    # Compute the orthographic target plane immediately: project_position can
    # still use the preceding rendered projection after changing camera.size.
    var height=camera.size
    var width=height*panels[index].size.x/panels[index].size.y
    return camera.position-camera.global_basis.z*2.+camera.global_basis.x*normalized.x*width-camera.global_basis.y*normalized.y*height

func cursor_zoom(position:Vector2,index:int,factor:float) -> void:
    var before=cursor_world(position,index)
    var old_pan=pan
    zoom=clampf(zoom*factor,.04,8.0);update_cameras()
    var shifted=cursor_world(position,index)
    pan+=before-shifted;update_cameras()
    last_zoom_trace={"before":str(before),"shifted":str(shifted),"after":str(cursor_world(position,index)),"old_pan":str(old_pan),"pan":str(pan),"zoom":zoom,"camera_size":cameras[index].size}

func _input(event:InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode==KEY_SPACE:toggle_pause();get_viewport().set_input_as_handled()
        if event.keycode==KEY_R:reset_view()
    # Handle navigation on the root viewport. SubViewportContainer can forward
    # events before gui_input, so container-only handlers are not reliable here.
    if event is InputEventMouseButton:
        if not event.pressed and event.button_index in [MOUSE_BUTTON_LEFT,MOUSE_BUTTON_RIGHT,MOUSE_BUTTON_MIDDLE]:
            dragging=false;panning=false;active_panel=-1
        var index=panel_at(event.position)
        if index<0 or not event.pressed:return
        if event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
            cursor_zoom(event.position,index,.87 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.15)
            get_viewport().set_input_as_handled()
        elif event.button_index in [MOUSE_BUTTON_LEFT,MOUSE_BUTTON_RIGHT,MOUSE_BUTTON_MIDDLE]:
            active_panel=index
            panning=event.button_index!=MOUSE_BUTTON_LEFT or event.shift_pressed or pan_mode
            dragging=not panning
            get_viewport().set_input_as_handled()
    if event is InputEventMouseMotion and active_panel>=0:
        if dragging:yaw-=event.relative.x*.008;pitch=clampf(pitch+event.relative.y*.008,-1.53,1.53)
        if panning:move_pan(event.relative,active_panel)
        update_cameras();get_viewport().set_input_as_handled()

func _exit_tree() -> void:
    if is_instance_valid(factory):factory.free()
