extends Node3D
## Finished layout composed from existing Foundry artwork and unchanged fish.
const LAYOUT := "res://assets/aquascape-marine-v1/layout.json"
var layout: Dictionary
var camera: Camera3D
var bed
var factory
var fish: Array=[]
var props: Array=[]
var paints: Dictionary={}
var specs: Dictionary={}
var elapsed := 0.0
var paused := false
var orbit := false
var orbit_time := 0.0
var dragging := false
var yaw := .20
var pitch := .23
var view_size := 4.8
var target := Vector3(0,1.32,0)
var water_paint: ShaderMaterial
var info: Label
var pause_button: Button
var checks: Dictionary={}
var review_active := false
var baseline: Dictionary={}

func _ready() -> void:
    get_window().content_scale_size=Vector2i(1920,1080)
    DisplayServer.window_set_title("潮汐馆 · 沉船与潮汐遗迹")
    layout=JSON.parse_string(FileAccess.get_file_as_string(LAYOUT))
    _environment()
    _substrate()
    _ornaments()
    _fish()
    _ui()
    _camera()
    _step(0)
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--capture-dir="):
            review_active=true
            call_deferred("_capture",arg.trim_prefix("--capture-dir="))

func _solid(color: Color,unshaded:=false) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color=color;m.roughness=1.0;m.metallic_specular=0
    if unshaded:m.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    return m

func _box(at: Vector3,size: Vector3,paint: Material) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    var mesh := BoxMesh.new();mesh.size=size
    node.mesh=mesh;node.position=at;node.material_override=paint
    add_child(node)
    return node

func _environment() -> void:
    var environment := WorldEnvironment.new()
    environment.environment=Environment.new()
    environment.environment.background_mode=Environment.BG_COLOR
    environment.environment.background_color=Color("081d29")
    environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color=Color("c5e7e6")
    environment.environment.ambient_light_energy=.78
    add_child(environment)
    var light := DirectionalLight3D.new()
    light.rotation_degrees=Vector3(-56,-28,0)
    light.light_color=Color("e7f5e9");light.light_energy=.75
    light.shadow_enabled=true
    add_child(light)
    var rim := _solid(Color("456b72"))
    _box(Vector3(0,-.22,0),Vector3(6.20,.40,3.20),_solid(Color("132e38")))
    _box(Vector3(0,-.012,0),Vector3(6.04,.025,3.04),rim)
    var backdrop := ShaderMaterial.new()
    backdrop.shader=load("res://scripts/aquarium/MarineBackdrop.gdshader")
    _box(Vector3(0,1.40,-1.52),Vector3(6.03,2.8,.025),backdrop)
    for y in [0.0,2.8]:
        for z in [-1.50,1.50]:_box(Vector3(0,y,z),Vector3(6.10,.032,.032),rim)
        for x in [-3.0,3.0]:_box(Vector3(x,y,0),Vector3(.032,.032,3.04),rim)
    for x in [-3.0,3.0]:
        for z in [-1.5,1.5]:_box(Vector3(x,1.4,z),Vector3(.026,2.8,.026),rim)
    var glass := _solid(Color(.24,.64,.68,.045),true)
    glass.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    glass.cull_mode=BaseMaterial3D.CULL_DISABLED
    for x in [-3.015,3.015]:_box(Vector3(x,1.40,0),Vector3(.005,2.8,3),glass)
    # Low-opacity water surface stays above fish and never covers their fronts.
    var surface := MeshInstance3D.new()
    var plane := PlaneMesh.new();plane.size=Vector2(6,3)
    surface.mesh=plane;surface.position.y=2.775
    water_paint=ShaderMaterial.new()
    water_paint.shader=load("res://shaders/aquarium_lab_surface.gdshader")
    water_paint.set_shader_parameter("strength",.12)
    water_paint.set_shader_parameter("pixel_size",.045)
    surface.material_override=water_paint
    add_child(surface)
    camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    camera.near=.02;camera.far=70
    add_child(camera)

func _substrate() -> void:
    bed=load("res://scripts/aquarium/EditableSubstrateBed.gd").new()
    add_child(bed)
    bed.setup(load("res://assets/aquascape-sand-v1/fine-sand.png"))
    bed.scale=Vector3.ONE*float(layout.substrate_scale)
    bed.blend_paint.shader=load("res://scripts/aquarium/MarineSubstrateBlend.gdshader")
    for i in 5:
        var path: String="res://assets/aquascape-sand-v1/fine-sand.png" if i==0 else "res://assets/aquascape-substrates-v2/"+bed.MATERIAL_IDS[i]+".png"
        bed.blend_paint.set_shader_parameter("substrate_"+str(i),load(path))
    for z in bed.NZ:
        for x in bed.NX:
            var wx: float=(x*bed.DX-bed.WIDTH*.5)*5
            var wz: float=(z*bed.DZ-bed.DEPTH*.5)*5
            var rear: float=clampf((.55-wz)/2.0,0,1)
            var island: float=exp(-pow((wx+1.8)/1.05,2)-pow((wz+.62)/.68,2))*.14+exp(-pow((wx-1.7)/.9,2)-pow((wz+.7)/.65,2))*.15
            bed.heights[z*bed.NX+x]=(.045+.11*rear+island)/5
            var stream: float=.25+sin(wz*1.8)*.42
            var rear_edge: float=-.76+.14*sin(wx*1.7)+.09*cos(wx*3.1)
            var left_pocket: float=pow((wx+2.55)/.58,2)+pow((wz+.25)/1.0,2)
            var right_pocket: float=pow((wx-2.55)/.58,2)+pow((wz+.25)/1.0,2)
            var gravel: bool=wz<rear_edge or left_pocket<1 or right_pocket<1
            bed.material_ids[z*bed.NX+x]=3 if gravel else (1 if absf(wx-stream)<.65 else 0)
    bed.rebuild_all()

func _ground(x: float,z: float) -> float:
    return bed.sample(x/5,z/5)*5

func _model_bounds(model: Node3D) -> AABB:
    var box := AABB();var first := true
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        var local: AABB=model.global_transform.affine_inverse()*mesh.global_transform*mesh.get_aabb()
        box=local if first else box.merge(local);first=false
    return box

func _ornaments() -> void:
    for path in ["res://assets/aquascape-v5/catalog.json","res://assets/aquascape-decor-v1/catalog.json"]:
        for row in JSON.parse_string(FileAccess.get_file_as_string(path)).assets:
            if not row.get("animated",false):specs[row.id]=row
    for row in layout.props:
        var spec: Dictionary=specs[row.id]
        var model: Node3D=(load(spec.model) as PackedScene).instantiate()
        model.name=row.id+"_%02d" % props.size()
        add_child(model)
        var box := _model_bounds(model)
        if not paints.has(row.id):
            var paint := ShaderMaterial.new()
            paint.shader=load("res://scripts/aquarium/DecorThreeViewArtwork.gdshader")
            for view in ["front","right","top"]:paint.set_shader_parameter(view+"_art",load(spec.material_dir+"/"+row.id+"-"+view+".png"))
            var d: Dictionary=spec.projection_bounds
            paint.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
            paint.set_shader_parameter("radial_jar",row.id=="terracotta_jar")
            paints[row.id]=paint
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            for s in mesh.mesh.get_surface_count():mesh.set_surface_override_material(s,paints[row.id])
        model.scale=Vector3.ONE*float(row.scale)
        model.rotation.y=float(row.yaw)
        var rotated: AABB=model.transform*box
        var at := Vector3(float(row.at[0]),0,float(row.at[1]))
        var support := _ground(at.x,at.z)
        for corner in 8:
            var q := rotated.get_endpoint(corner)
            support=minf(support,_ground(at.x+q.x,at.z+q.z))
        model.position=Vector3(at.x,support-.025-rotated.position.y,at.z)
        props.append({"id":row.id,"node":model,"bounds":box})

func _fish() -> void:
    # Reuse the exact current exhibit factory, ownership layers and Swim rig.
    # This scene changes only carrier placement, never fish geometry or skin.
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    factory._load_profiles()
    var species: Array=[]
    for row in layout.fish_species:
        for i in int(row.count):species.append(row.id)
    # Interleave colors across three water layers rather than isolate species.
    var order := [0,3,7,11,4,8,12,1,5,9,13,2,6,10,14]
    for i in order.size():
        var id: String=species[order[i]]
        var profile: Dictionary=factory.profiles[id]
        var length_m: float=profile.real_length_cm/100.0
        factory._add_fish(self,id,length_m,profile,Vector3.ZERO,i*.37)
        var row: Dictionary=factory.fish[-1]
        row["bounds"]=_model_bounds(row.model)
        row["lane"]=i/5
        row["phase"]=(i%5)/5.0+(i/5)*.115
        fish.append(row)
        var path: String="res://assets/models/fish/"+id+".glb"
        baseline[path]=FileAccess.get_sha256(path)

func _route(row: Dictionary,seconds: float) -> Vector3:
    var a: float=(seconds/float(layout.route.period_seconds)+row.phase)*TAU
    return Vector3(float(layout.route.radii_m[0])*sin(a),float(layout.route.water_layers_m[row.lane])+sin(a*2+row.lane)*float(layout.route.vertical_amplitude_m),float(layout.route.radii_m[1])*cos(a))

func _position_fish(row: Dictionary,seconds: float) -> void:
    var p := _route(row,seconds)
    var velocity := (_route(row,seconds+.02)-p).normalized()
    row.carrier.position=p
    row.carrier.rotation=Vector3(0,atan2(-velocity.z,velocity.x)+(PI if float(row.profile.head_sign)<0 else 0),0)

func _step(delta: float) -> void:
    elapsed+=delta
    for row in fish:
        row.controller.step(delta)
        _position_fish(row,elapsed)
    water_paint.set_shader_parameter("clock",elapsed)

func _process(delta: float) -> void:
    if review_active:return
    if not paused:_step(minf(delta,.05))
    if orbit:
        orbit_time+=delta
        yaw=sin(orbit_time*.12)*.44
        _camera()

func _camera() -> void:
    camera.size=view_size
    camera.position=target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*16
    camera.look_at(target)

func _preset(id: String) -> void:
    target=Vector3(0,1.32,0);view_size=4.8
    if id=="front":yaw=0;pitch=.10
    elif id=="top":yaw=.01;pitch=1.18;view_size=5.7;target.y=.7
    elif id=="wreck":yaw=.10;pitch=.30;view_size=2.0;target=Vector3(-1.50,.60,-.32)
    elif id=="ruins":yaw=.12;pitch=.24;view_size=2.1;target=Vector3(1.62,.70,-.40)
    else:yaw=.20;pitch=.23
    _camera()

func _toggle_pause() -> void:
    paused=not paused
    pause_button.text="继续游动" if paused else "暂停游动"

func _ui() -> void:
    var layer := CanvasLayer.new();add_child(layer)
    var root := Control.new();root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.mouse_filter=Control.MOUSE_FILTER_IGNORE;layer.add_child(root)
    var header := ColorRect.new();header.color=Color(.025,.09,.12,.92);header.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE);header.offset_bottom=98;header.mouse_filter=Control.MOUSE_FILTER_IGNORE;root.add_child(header)
    var title := Label.new();title.text="沉船与潮汐遗迹";title.position=Vector2(38,15);title.add_theme_font_size_override("font_size",30);title.modulate=Color("eee4c6");header.add_child(title)
    info=Label.new();info.text="6 × 3 × 2.8 m  /  15 尾海鱼  /  白沙水道与碎石后坡";info.position=Vector2(40,58);info.add_theme_font_size_override("font_size",18);info.modulate=Color("9ec3c5");header.add_child(info)
    var buttons := HBoxContainer.new();buttons.position=Vector2(900,27);buttons.add_theme_constant_override("separation",10);header.add_child(buttons)
    for item in [["全景","hero"],["正面","front"],["俯视","top"],["沉船近看","wreck"],["遗迹近看","ruins"]]:
        var b := Button.new();b.text=item[0];b.custom_minimum_size=Vector2(112,40);b.focus_mode=Control.FOCUS_NONE;b.pressed.connect(_preset.bind(item[1]));buttons.add_child(b)
    pause_button=Button.new();pause_button.text="暂停游动";pause_button.custom_minimum_size=Vector2(112,40);pause_button.focus_mode=Control.FOCUS_NONE;pause_button.pressed.connect(_toggle_pause);buttons.add_child(pause_button)
    var b := Button.new();b.text="旋转视角";b.custom_minimum_size=Vector2(112,40);b.focus_mode=Control.FOCUS_NONE;b.pressed.connect(func():orbit=not orbit);buttons.add_child(b)
    var footer := ColorRect.new();footer.color=Color(.025,.09,.12,.90);footer.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE);footer.offset_top=-75;footer.mouse_filter=Control.MOUSE_FILTER_IGNORE;root.add_child(footer)
    var label := Label.new();label.text="红皇帝鱼 3  ·  真鲷 4  ·  黑鲷 4  ·  大黄鱼 4";label.position=Vector2(40,10);label.add_theme_font_size_override("font_size",20);label.modulate=Color("dddfc9");footer.add_child(label)
    var help := Label.new();help.text="拖动环绕  ·  滚轮缩放  ·  空格暂停  ·  R 回到全景";help.position=Vector2(40,40);help.add_theme_font_size_override("font_size",16);help.modulate=Color("92afb9");footer.add_child(help)

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        if event.button_index in [MOUSE_BUTTON_LEFT,MOUSE_BUTTON_RIGHT]:dragging=event.pressed
        if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:view_size=clampf(view_size*(.9 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.1),1.3,7.0);_camera()
    if event is InputEventMouseMotion and dragging:
        orbit=false;yaw-=event.relative.x*.005;pitch=clampf(pitch+event.relative.y*.004,.05,1.40);_camera()
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode==KEY_SPACE:_toggle_pause()
        if event.keycode==KEY_R:_preset("hero")

func _check(id: String,okay: bool) -> void:
    checks[id]=okay
    print("MARINE_CHECK ",id," ",okay)

func _fish_box(row: Dictionary) -> AABB:
    # A padded rest envelope is a layout check, not a skinned-surface certificate.
    var box: AABB=row.bounds
    box=box.grow(box.size.x*.16)
    return row.model.global_transform*box

func _capture_image(directory: String,name: String) -> void:
    for i in 5:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    _check("screenshot_"+name,get_viewport().get_texture().get_image().save_png(directory+"/"+name+".png")==OK)

func _capture(directory: String) -> void:
    DirAccess.make_dir_recursive_absolute(directory)
    for i in 50:await get_tree().process_frame
    _check("four_marine_species",layout.fish_species.size()==4)
    _check("fifteen_animated_fish",fish.size()==15)
    _check("six_metre_tank",bed.WIDTH*bed.scale.x==6 and bed.DEPTH*bed.scale.z==3)
    _check("thirteen_existing_props",props.size()==13)
    _check("heightfield_chunks_still_sixteen",bed.chunks.size()==16)
    _check("no_per_grain_nodes",bed.gravel.batches.size()==16 and bed.gravel.visible_count()<=4608)
    var max_prop := 0.0
    var within_tank := true
    for prop in props:
        var box: AABB=prop.node.global_transform*prop.bounds
        max_prop=maxf(max_prop,box.end.y)
        within_tank=within_tank and box.position.x> -3 and box.end.x<3 and box.position.z> -1.5 and box.end.z<1.5
    _check("all_props_within_floor",within_tank)
    var fish_inside := true
    var clear := true
    var minimum_clearance := 100.0
    var motion := false
    var frames: Array=[]
    var initial_rotation: Quaternion=fish[0].skeleton.get_bone_pose_rotation(fish[0].skeleton.get_bone_count()-1)
    for i in 180:
        var time: float=float(i)*float(layout.route.period_seconds)/180
        for row in fish:
            _position_fish(row,time)
            var box := _fish_box(row)
            fish_inside=fish_inside and box.position.x> -3 and box.end.x<3 and box.position.z> -1.5 and box.end.z<1.5 and box.position.y>0 and box.end.y<2.775
            minimum_clearance=minf(minimum_clearance,box.position.y-max_prop)
            for prop in props:
                var occupied: AABB=prop.node.global_transform*prop.bounds
                clear=clear and not box.intersects(occupied)
    _check("sampled_padded_fish_bounds_inside_glass",fish_inside)
    _check("sampled_fish_routes_clear_of_props",clear)
    for i in 90:_step(1.0/60)
    var final_rotation: Quaternion=fish[0].skeleton.get_bone_pose_rotation(fish[0].skeleton.get_bone_count()-1)
    motion=initial_rotation.angle_to(final_rotation)>.0001
    _check("native_skeletal_swim_is_advancing",motion)
    for path in baseline:_check("unchanged_"+path.get_file(),FileAccess.get_sha256(path)==baseline[path])
    _preset("hero")
    await _capture_image(directory,"hero")
    for i in 360:_step(1.0/60)
    await _capture_image(directory,"hero-later")
    for view in ["front","top","wreck","ruins"]:
        _preset(view)
        await _capture_image(directory,view)
    _preset("hero")
    var failures: Array=[]
    for id in checks:
        if not checks[id]:failures.append(id)
    var report := {"schema_version":1,"command":"aquascape.marine-showcase-native-review","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","checks":checks,"failures":failures,"summary":{"tank_size_m":layout.tank_size_m,"fish_count":fish.size(),"species":layout.fish_species,"props":props.size(),"terrain_chunks":16,"maximum_visible_gravel":4608,"actual_visible_gravel":bed.gravel.visible_count(),"route_samples_per_fish":180,"max_prop_y_m":max_prop,"minimum_padded_fish_vertical_clearance_m":minimum_clearance,"gpu":RenderingServer.get_video_adapter_name()},"unchanged_fish_model_hashes":baseline,"visual_review":"pending","user_acceptance":"pending","limitations":["Fish geometry, material ownership and skeletal Swim helper are reused; only carrier routes change. This is not a new fish asset acceptance.","Layout checks use padded rest AABBs at 180 route samples, not exact deformed mesh collision or continuous-time proof.","The substrate retains a single heightfield and batched gravel. No grain physics or terrain caves.","A marine-themed game composition, not a regional biotope or real-world stocking recommendation."]}
    var file := FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  "));file.close()
    get_tree().quit(0 if failures.is_empty() else 1)

func _exit_tree() -> void:
    if is_instance_valid(factory):factory.free()
