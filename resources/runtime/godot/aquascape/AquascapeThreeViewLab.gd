extends "res://scripts/aquarium/AquascapeArtLab.gd"
## Three-view hull trial. Plants and the comparison fish reuse existing assets.
var auto_rotate := false
var capture_active := false

func _build() -> void:
    DisplayServer.window_set_title("潮汐馆 · 三视图材质试作 V3")
    _box(Vector3(0,-.045,0),Vector3(1.4,.08,.72),_solid(Color("203b3e")))
    _box(Vector3(0,0,0),Vector3(1.37,.018,.69),_solid(Color("80765c")))
    scenery=Node3D.new()
    scenery.name="ThreeViewScenery"
    world.add_child(scenery)
    var build_report: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-v3/build.validation.json"))
    var dimensions: Dictionary={}
    var floors: Dictionary={}
    for row in build_report.outputs:
        dimensions[row.id]=row.projection_bounds
        floors[row.id]=.0095-row.actual_bounds_m[0][1]
    for row in [["rock",Vector3(-.32,.012,-.035),true],["driftwood",Vector3(.19,.012,.04),true],["anubias",Vector3(-.32,.171,-.04),false],["java_fern",Vector3(-.46,.171,-.07),false]]:
        var directory: String="aquascape-v3" if row[2] else "aquascape-v2"
        var packed: PackedScene=load("res://assets/"+directory+"/"+row[0]+".glb")
        var model: Node3D=packed.instantiate()
        model.name=row[0]
        scenery.add_child(model)
        model.position=row[1]
        if row[2]:model.position.y=floors[row[0]]
        art_nodes[row[0]]=model
        if not row[2]:
            model.position.y=_top_surface(art_nodes["rock"],model.position.x,model.position.z)+.001
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            var originals: Array=[]
            for surface in mesh.mesh.get_surface_count():
                var material: Material
                if row[2]:
                    var mapped := ShaderMaterial.new()
                    mapped.shader=load("res://scripts/aquarium/ThreeViewArtwork.gdshader")
                    for view in ["front","right","top"]:
                        mapped.set_shader_parameter(view+"_art",load("res://assets/aquascape-v3/"+row[0]+"-"+view+".png"))
                    var d: Dictionary=dimensions[row[0]]
                    mapped.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
                    material=mapped
                else:
                    var painted: StandardMaterial3D=mesh.get_active_material(surface).duplicate()
                    painted.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
                    painted.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
                    material=painted
                originals.append(material)
                mesh.set_surface_override_material(surface,material)
            art_originals[mesh]=originals
    fish_stock=preload("res://scripts/aquarium/AquariumFishStock.gd").new()
    add_child(fish_stock)
    var entry: Dictionary=fish_stock.add_stock(world,"bluegill",Vector3(.36,.43,-.06),0.0)
    entry.carrier.position=Vector3(.36,.43,-.06)
    entry.carrier.rotation=Vector3.ZERO
    entry.player.pause()
    yaw=.30;pitch=.30;view_size=1.16;target=Vector3(0,.24,0)

func _top_surface(model: Node3D, x: float, z: float) -> float:
    var highest := .012
    var point := Vector2(x,z)
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        for surface in mesh.mesh.get_surface_count():
            var arrays: Array=mesh.mesh.surface_get_arrays(surface)
            var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
            var indices: PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
            var count: int=indices.size() if not indices.is_empty() else vertices.size()
            for i in range(0,count,3):
                var a: Vector3=mesh.global_transform*vertices[indices[i] if not indices.is_empty() else i]
                var b: Vector3=mesh.global_transform*vertices[indices[i+1] if not indices.is_empty() else i+1]
                var c: Vector3=mesh.global_transform*vertices[indices[i+2] if not indices.is_empty() else i+2]
                var aa := Vector2(a.x,a.z);var bb := Vector2(b.x,b.z);var cc := Vector2(c.x,c.z)
                var denominator: float=(bb-aa).cross(cc-aa)
                if absf(denominator)<.000000001:continue
                var u: float=(point-aa).cross(cc-aa)/denominator
                var v: float=(bb-aa).cross(point-aa)/denominator
                if u>=0 and v>=0 and u+v<=1:
                    highest=maxf(highest,a.y+(b.y-a.y)*u+(c.y-a.y)*v)
    return highest

func _ui() -> void:
    super._ui()
    for label in find_children("*","Label",true,false):
        if label.text.begins_with("A Q U A S C A P E"):
            label.text="A Q U A S C A P E   V 3    /    三 视 图 材 质 试 作"
        if label.text.begins_with("拖动旋转"):
            label.text="拖动旋转 · 滚轮缩放 · 空格自动旋转 · R 复位      1 材质   2 灰模   3 格纹   4 俯视   5 背面"
    _mode(0)

func _mode(value: int) -> void:
    super._mode(value)
    if is_instance_valid(mode_label):
        mode_label.text=["三向生图贴图","三视轮廓灰模","映射格纹"][value]+" · 岩石 / 沉木试作，水草沿用 V2"

func _process(delta: float) -> void:
    if auto_rotate and not dragging and not capture_active:
        yaw+=delta*.22
        _camera()

func _unhandled_key_input(event: InputEvent) -> void:
    super._unhandled_key_input(event)
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode==KEY_SPACE:auto_rotate=not auto_rotate
        if event.keycode==KEY_R:
            yaw=.30;pitch=.30;view_size=1.16;target=Vector3(0,.24,0);_mode(0);_camera()

func _capture(directory: String) -> void:
    capture_active=true
    DirAccess.make_dir_recursive_absolute(directory)
    for i in 12:await get_tree().process_frame
    var outputs: Array=[]
    var views := [
        ["01-overview",0,.30,.30,1.16,Vector3(0,.24,0)],
        ["02-gray",1,.30,.30,1.16,Vector3(0,.24,0)],
        ["03-front",0,0,0,1.16,Vector3(0,.24,0)],
        ["04-back",0,PI+.25,.30,1.16,Vector3(0,.24,0)],
        ["05-top",0,0,1.50,1.16,Vector3(0,.18,0)],
        ["06-right",0,PI/2,.15,1.16,Vector3(0,.24,0)],
        ["07-rock",0,-.42,.55,.54,Vector3(-.32,.09,-.035)],
        ["08-wood",0,.48,.25,.69,Vector3(.19,.17,.04)],
        ["09-wood-gray",1,1.2,.45,.69,Vector3(.19,.17,.04)]
    ]
    var failed := false
    for row in views:
        _mode(row[1]);yaw=row[2];pitch=row[3];view_size=row[4];target=row[5];_camera()
        for i in 4:await get_tree().process_frame
        await RenderingServer.frame_post_draw
        var path: String=directory+"/"+row[0]+".png"
        var err := get_viewport().get_texture().get_image().save_png(path)
        failed=failed or err!=OK
        outputs.append({"path":path,"error":err})
    var data := {"schema_version":1,"command":"aquascape.three-view-render","ok":not failed,"status":"done","next_action":"human_review","outputs":outputs,"failures":[],"visual_review":"pending","user_acceptance":"pending","scope":"Actual Godot GPU scenery material trial. V3 rock/wood, V2 plants, original fixed fish."}
    var file := FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(data,"  "))
    print(JSON.stringify(data))
    get_tree().quit(1 if failed else 0)
