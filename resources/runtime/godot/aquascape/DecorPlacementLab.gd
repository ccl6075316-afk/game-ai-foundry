extends "res://scripts/aquarium/SubstratePlacementLab.gd"
const DECOR_SAVE := "user://aquascape-decor-v1.json"
var decor_entries: Array=[]
var decor_buttons: Array[Button]=[]
var decor_focus := false
var decor_target := Vector3.ZERO

func _ready() -> void:
    for path in ["res://assets/aquascape-decor-v1/catalog.json","res://assets/aquascape-v5/catalog.json"]:
        for row in JSON.parse_string(FileAccess.get_file_as_string(path)).assets:
            if not row.get("animated",false):decor_entries.append(row)
    super._ready()
    for row in decor_entries:rock_specs[row.id]=row
    DisplayServer.window_set_title("潮汐馆 · %d种造景与自由布缸" % decor_entries.size())
    for arg in OS.get_cmdline_user_args():
        if arg=="--decor-demo":_decor_gallery()
        if arg.begins_with("--catalog-check-dir="):call_deferred("_catalog_check",arg.trim_prefix("--catalog-check-dir="))

func _ui() -> void:
    super._ui()
    for label in find_children("*","Label",true,false):
        if label.text.begins_with("A Q U A S C A P E"):label.text="A Q U A S C A P E   /   小装饰布缸实验"
        if label.text.begins_with("五种底材"):label.text="%d种造景 · 五种底床 · 上方列表可滚动，选择石头、沉木和人工摆件" % decor_entries.size()
    var strip := ColorRect.new()
    strip.position=Vector2(26,214)
    strip.size=Vector2(1080,86)
    strip.color=Color("132c31")
    add_child(strip)
    var scroll := ScrollContainer.new();scroll.size=Vector2(1080,86);strip.add_child(scroll)
    var grid := GridContainer.new();grid.columns=5;grid.add_theme_constant_override("h_separation",10);grid.add_theme_constant_override("v_separation",6);scroll.add_child(grid)
    for i in decor_entries.size():
        var row: Dictionary=decor_entries[i]
        var id: String=row.id
        var button := _button(grid,row.name_zh,Vector2.ZERO,204,func():_set_tool(id))
        button.custom_minimum_size.y=34
        button.toggle_mode=true
        decor_buttons.append(button)
    tool_buttons.select.text="4  选取 / 移动摆件"
    for button in find_children("*","Button",true,false):
        if button.text=="混铺示例":
            button.text="造景总览"
            for connection in button.get_signal_connection_list("pressed"):button.pressed.disconnect(connection.callable)
            button.pressed.connect(func():_remember();_decor_gallery())

func _camera() -> void:
    camera.size=view_size
    var target: Vector3=decor_target if decor_focus else Vector3(.19,.17,0)
    camera.position=target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*3
    camera.look_at(target)

func _is_decor(id: String) -> bool:
    for row in decor_entries:
        if row.id==id:return true
    return false

func _rock_model(id: String) -> Dictionary:
    var built := super._rock_model(id)
    if _is_decor(id):
        var paint: ShaderMaterial=rock_paints[id]
        paint.shader=load("res://scripts/aquarium/DecorThreeViewArtwork.gdshader")
        var spec: Dictionary=rock_specs[id]
        for view in ["front","right","top"]:paint.set_shader_parameter(view+"_art",load(spec.material_dir+"/"+id+"-"+view+".png"))
        var d: Dictionary=spec.projection_bounds
        paint.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
        paint.set_shader_parameter("right_art_on_rear",id=="coconut_shelter")
        paint.set_shader_parameter("radial_jar",id=="terracotta_jar")
    return built

func _set_tool(value: String) -> void:
    var is_decor := _is_decor(value)
    super._set_tool("decor" if is_decor else value)
    for i in decor_buttons.size():decor_buttons[i].button_pressed=is_decor and decor_entries[i].id==value
    if value=="select":notice="点击摆件并拖动；Q/E 旋转，Shift＋滚轮缩放，Delete 删除。"
    if not is_decor:return
    var built := _rock_model(value)
    ghost=built.node
    ghost_bounds=built.bounds
    ghost_id=value
    ghost_scale=.65
    ghost_yaw=0
    world.add_child(ghost)
    for mesh in ghost.find_children("*","MeshInstance3D",true,false):mesh.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    notice="摆放"+rock_specs[value].name_zh+" · 左键放下 · Q/E 旋转 · Shift＋滚轮缩放"
    _update_cursor()

func _support(at: Vector3,box: AABB,factor: float) -> float:
    var height: float=bed.sample(at.x,at.z)
    for delta in [Vector2(-1,-1),Vector2(1,-1),Vector2(-1,1),Vector2(1,1)]:
        height=minf(height,bed.sample(at.x+delta.x*box.size.x*factor*.22,at.z+delta.y*box.size.z*factor*.22))
    return height-.008*minf(1.0,factor)-box.position.y*factor

func _input_canvas(event: InputEvent) -> void:
    if tool=="decor" and event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
        pointer=event.position;_update_cursor()
        if event.pressed and hit!=null:
            if rocks.size()>=80:notice="本实验最多放置 80 件摆件。";return
            _remember();_add_rock(ghost_id,hit,ghost_scale,ghost_yaw)
        return
    super._input_canvas(event)

func _state() -> Dictionary:
    var data := super._state()
    data.schema_version=3
    return data

func _save_user() -> void:
    notice="布缸实验已保存。" if _write_save(DECOR_SAVE) else "保存失败。"

func _load_user() -> void:
    var source: String=DECOR_SAVE if FileAccess.file_exists(DECOR_SAVE) else (SUBSTRATE_SAVE if FileAccess.file_exists(SUBSTRATE_SAVE) else SAVE_PATH)
    notice="已读取布缸实验。" if _read_save(source) else "没有可读取的有效存档，保留当前实验。"

func _read_save(path: String) -> bool:
    if not FileAccess.file_exists(path):return false
    var data: Variant=JSON.parse_string(FileAccess.get_file_as_string(path))
    if not data is Dictionary:return false
    if data.get("schema_version")!=1 and data.get("schema_version")!=2 and data.get("schema_version")!=3:return false
    if data.get("sand")!="fine_sand" or not data.get("grid") is Array or data.grid.size()!=2 or data.grid[0]!=BED.NX or data.grid[1]!=BED.NZ:return false
    if not data.get("heights") is Array or data.heights.size()!=BED.NX*BED.NZ or not data.get("rocks") is Array or data.rocks.size()>80:return false
    for h in data.heights:
        if not (h is float or h is int) or not is_finite(h) or h<0 or h>BED.MAX_HEIGHT:return false
    if data.schema_version>=2:
        if not data.get("materials") is Array or data.materials.size()!=BED.NX*BED.NZ:return false
        for id in data.materials:
            if not (id is float or id is int) or not is_finite(id) or id!=int(id) or id<0 or id>4:return false
        var choice: Variant=data.get("selected_substrate",0)
        if not (choice is float or choice is int) or not is_finite(choice) or choice!=int(choice) or choice<0 or choice>4:return false
    for row in data.rocks:
        if not row is Dictionary or not rock_specs.has(row.get("id")):return false
        if not row.get("position") is Array or row.position.size()!=3:return false
        for p in row.position:
            if not (p is float or p is int) or not is_finite(p):return false
        if absf(row.position[0])>.61 or absf(row.position[2])>.31:return false
        if not (row.get("scale") is float or row.get("scale") is int) or not is_finite(row.scale) or row.scale<.4 or row.scale>1.6:return false
        if not (row.get("yaw") is float or row.get("yaw") is int) or not is_finite(row.yaw):return false
    _remember();_restore(data)
    return true

func _decor_gallery() -> void:
    decor_focus=false
    bed.visible=true
    for child in world.get_children():
        if child is MeshInstance3D:child.visible=true
    _set_tool("pour")
    for row in rocks:row.node.hide();row.node.queue_free()
    rocks.clear();selected=-1
    bed.active_material=0;bed.reset(.025)
    for z in BED.NZ:
        for x in BED.NX:bed.material_ids[z*BED.NX+x]=clampi(int(x/float(BED.NX)*5),0,4)
    bed.rebuild_all()
    var rows: int=ceili(decor_entries.size()/5.0)
    for i in decor_entries.size():
        var spec: Dictionary=decor_entries[i];var box: Dictionary=spec.projection_bounds
        var factor: float=minf(.55,minf(.18/box.width,(.48/rows)/box.depth))
        _add_rock(spec.id,Vector3((i%5-2)*.235,0,(float(i/5)-(rows-1)*.5)*(.50/rows)),factor,0)
    yaw=.12;pitch=.62;view_size=1.32;_camera()
    notice="%d种造景总览 · 选上方物件摆放，4 选取移动 · Q/E 旋转 · Shift＋滚轮缩放" % decor_entries.size()

func _catalog_check(directory: String) -> void:
    DirAccess.make_dir_recursive_absolute(directory)
    var failures: Array=[];var added: Array=[]
    for row in decor_entries:
        if row.get("geometry_revision","")!="budget-first-v11":continue
        _set_tool(row.id)
        if ghost==null or ghost_id!=row.id:failures.append(row.id+": selection failed")
        _add_rock(row.id,Vector3((added.size()%5-2)*.20,0,(added.size()/5-.5)*.24),.45,0)
        added.append(row.id)
    _set_tool("select")
    var path := directory+"/placement-state.json"
    var wrote: bool=_write_save(path);var restored: bool=wrote and _read_save(path)
    for id in added:
        if rocks.filter(func(r):return r.id==id).is_empty():failures.append(id+": missing after restore")
    if not restored:failures.append("Placement state roundtrip failed")
    for i in 5:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    get_viewport().get_texture().get_image().save_png(directory+"/placement.png")
    var okay: bool=failures.is_empty() and added.size()==10 and decor_entries.size()==30
    var file := FileAccess.open(directory+"/placement.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify({"command":"aquascape.expansion-placement-roundtrip","ok":okay,"status":"done" if okay else "failed","next_action":"human_review" if okay else "fix_input","catalog_entries":decor_entries.size(),"new_ids":added,"selection_placement_and_restore":restored,"outputs":[path,directory+"/placement.png"],"failures":failures,"user_acceptance":"pending"},"  "));file.close();get_tree().quit(0 if okay else 1)

func _focus_decor(index: int,view: String) -> void:
    decor_focus=true
    var row: Dictionary=rocks[index]
    for i in rocks.size():rocks[i].node.visible=i==index
    bed.visible=false
    for child in world.get_children():
        if child is MeshInstance3D:child.visible=false
    row.node.scale=Vector3.ONE
    row.node.rotation=Vector3.ZERO
    row.node.position=Vector3(0,-row.bounds.position.y,0)
    yaw=.18;pitch=.20
    if view=="right":yaw=PI/2;pitch=.10
    if view=="back":yaw=PI+.18
    if view=="top":yaw=.01;pitch=1.48
    view_size=maxf(.13,maxf(row.bounds.size.x,row.bounds.size.y)*2.3)
    var right := Vector3(cos(yaw),0,-sin(yaw))
    var up := Vector3(-sin(yaw)*sin(pitch),cos(pitch),-cos(yaw)*sin(pitch))
    decor_target=row.node.position+row.bounds.get_center()+right*view_size*.14+up*view_size*.12
    _camera()
    for mesh in row.node.find_children("*","MeshInstance3D",true,false):
        for s in mesh.mesh.get_surface_count():
            if view=="gray":
                var gray := StandardMaterial3D.new()
                gray.albedo_color=Color("8eaaa6");gray.roughness=1.0;gray.metallic_specular=0
                mesh.set_surface_override_material(s,gray)
            else:mesh.set_surface_override_material(s,rock_paints[row.id])

func _process(delta: float) -> void:
    super._process(delta)
    if capture_active:return
    detail_label.text=detail_label.text.replace("块石头","件摆件")
    selected_label.text="摆件："+(rock_specs[rocks[selected].id].name_zh+"  %.2f×" % rocks[selected].factor if selected>=0 else "点击选取后可移动")
