extends "res://scripts/aquarium/SandPlacementLab.gd"
const SUBSTRATE_BED = preload("res://scripts/aquarium/EditableSubstrateBed.gd")
const SUBSTRATE_NAMES := ["浅米细沙","白色石英砂","深色水草泥","自然混合砾砂","灰色小碎石"]
const SUBSTRATE_SAVE := "user://aquascape-substrates-v2.json"
var substrate_buttons: Array[Button]=[]
var substrate_label: Label

func _ready() -> void:
    super._ready()
    var previous=bed
    previous.hide();previous.queue_free()
    bed=SUBSTRATE_BED.new()
    bed.name="EditableSubstrateV2"
    world.add_child(bed)
    bed.setup(load("res://assets/aquascape-sand-v1/fine-sand.png"))
    DisplayServer.window_set_title("潮汐馆 · 五种底床混铺实验")
    _choose_substrate(0)
    for arg in OS.get_cmdline_user_args():
        if arg=="--mixed-demo":_mixed_demo()

func _ui() -> void:
    super._ui()
    tool_buttons.pour.text="1  铺设 / 堆高"
    tool_buttons.remove.text="2  移除底床"
    for button in find_children("*","Button",true,false):
        if button.text=="示例坡景":
            button.text="混铺示例"
            for connection in button.get_signal_connection_list("pressed"):button.pressed.disconnect(connection.callable)
            button.pressed.connect(func():_remember();_mixed_demo())
    for label in find_children("*","Label",true,false):
        if label.text.begins_with("A Q U A S C A P E"):label.text="A Q U A S C A P E   /   底床混铺实验"
        if label.text.begins_with("一种细沙"):label.text="五种底材 · 局部混铺 · 沙路与砾石 · 两种造景石"
    var strip := ColorRect.new()
    strip.position=Vector2(26,102)
    strip.size=Vector2(1080,104)
    strip.color=Color("132c31")
    add_child(strip)
    for i in 5:
        var b := _button(strip,SUBSTRATE_NAMES[i],Vector2(10+i*214,9),204,func():_choose_substrate(i))
        b.toggle_mode=true
        substrate_buttons.append(b)
    var paint_button := _button(strip,"7  只换底材",Vector2(10,57),155,func():_set_tool("paint"))
    paint_button.toggle_mode=true
    tool_buttons["paint"]=paint_button
    substrate_label=_text(strip,"先选材料，再倒沙或局部换底材；不同底材可以混铺。",Vector2(180,64),16,Color("b9cdbb"))

func _choose_substrate(index: int) -> void:
    if not bed is SUBSTRATE_BED:return
    bed.active_material=index
    if tool not in ["pour","paint"]:_set_tool("pour")
    for i in substrate_buttons.size():substrate_buttons[i].button_pressed=i==index
    substrate_label.text="当前："+SUBSTRATE_NAMES[index]+" · 倒沙会堆高，7 只换底材保留原坡形。"
    notice="已选择"+SUBSTRATE_NAMES[index]+"，在缸底局部铺设。"

func _set_tool(value: String) -> void:
    super._set_tool(value)
    if value=="paint":notice="按住左键局部换底材，保持原有高度；可以铺出沙路与砾石区。"

func _update_cursor() -> void:
    if tool=="paint":
        tool="pour";super._update_cursor();tool="paint"
    else:super._update_cursor()

func _unhandled_key_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_7:_set_tool("paint")
    else:super._unhandled_key_input(event)

func _state() -> Dictionary:
    var data := super._state()
    data.schema_version=2
    data["materials"]=Array(bed.material_ids)
    data["selected_substrate"]=bed.active_material
    return data

func _restore(data: Dictionary) -> void:
    bed.material_ids.resize(BED.NX*BED.NZ)
    if data.has("materials"):bed.material_ids=PackedByteArray(data.materials)
    else:bed.material_ids.fill(0)
    bed.active_material=int(data.get("selected_substrate",0))
    super._restore(data)
    _choose_substrate(bed.active_material)

func _save_user() -> void:
    notice="混铺实验已保存。" if _write_save(SUBSTRATE_SAVE) else "保存失败。"

func _load_user() -> void:
    if FileAccess.file_exists(SUBSTRATE_SAVE):notice="已读取混铺实验。" if _read_save(SUBSTRATE_SAVE) else "混铺存档无效，保留当前实验。"
    elif FileAccess.file_exists(SAVE_PATH):notice="已导入上一版铺沙实验。" if _read_save(SAVE_PATH) else "上一版存档无效，保留当前实验。"
    else:notice="没有可读取的有效混铺存档。"

func _read_save(path: String) -> bool:
    if not FileAccess.file_exists(path):return false
    var data: Variant=JSON.parse_string(FileAccess.get_file_as_string(path))
    if not data is Dictionary:return false
    if (data.get("schema_version")!=1 and data.get("schema_version")!=2) or data.get("sand")!="fine_sand":return false
    if not data.get("grid") is Array or data.grid.size()!=2 or data.grid[0]!=BED.NX or data.grid[1]!=BED.NZ:return false
    if not data.get("heights") is Array or data.heights.size()!=BED.NX*BED.NZ or not data.get("rocks") is Array or data.rocks.size()>80:return false
    for h in data.heights:
        if not (h is float or h is int) or not is_finite(h) or h<0 or h>BED.MAX_HEIGHT:return false
    if data.schema_version==2:
        if not data.get("materials") is Array or data.materials.size()!=BED.NX*BED.NZ:return false
        for id in data.materials:
            if not (id is float or id is int) or not is_finite(id) or id!=int(id) or id<0 or id>4:return false
        var selected_id: Variant=data.get("selected_substrate",0)
        if not (selected_id is float or selected_id is int) or not is_finite(selected_id) or selected_id!=int(selected_id) or selected_id<0 or selected_id>4:return false
    for row in data.rocks:
        if not row is Dictionary or not row.get("id") in ROCK_IDS:return false
        if not row.get("position") is Array or row.position.size()!=3:return false
        for p in row.position:
            if not (p is float or p is int) or not is_finite(p):return false
        if absf(row.position[0])>.61 or absf(row.position[2])>.31:return false
        if not (row.get("scale") is float or row.get("scale") is int) or not is_finite(row.scale) or row.scale<.4 or row.scale>1.6:return false
        if not (row.get("yaw") is float or row.get("yaw") is int) or not is_finite(row.yaw):return false
    _remember();_restore(data)
    return true

func _mixed_demo() -> void:
    _demo(false)
    for z in BED.NZ:
        for x in BED.NX:
            var px: float=x*BED.DX-.6
            var pz: float=z*BED.DZ-.3
            var path_center: float=.12*sin((pz+.3)*5)-.02
            bed.material_ids[z*BED.NX+x]=1 if absf(px-path_center)<.095 else (2 if px<path_center else (3 if pz<.06 else 4))
    bed.rebuild_all()
    _choose_substrate(1)
    _set_tool("paint")
    notice="混铺示例：石英砂小路、深色水草泥、砾砂与小碎石；可继续修改。"
