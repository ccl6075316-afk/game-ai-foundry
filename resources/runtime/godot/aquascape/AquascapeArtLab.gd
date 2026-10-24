extends "res://scripts/aquarium/AquascapeLab.gd"
## Reuses review controls only. All scenery comes from generated-art GLBs.
var art_materials: Array=[]
var art_nodes: Dictionary={}
var art_originals: Dictionary={}

func _build() -> void:
    DisplayServer.window_set_title("潮汐馆 · 原画驱动置景 V2")
    _box(Vector3(0,-.045,0),Vector3(1.25,.08,.66),_solid(Color("203b3e")))
    _box(Vector3(0,0,0),Vector3(1.22,.018,.63),_solid(Color("80765c")))
    scenery=Node3D.new()
    scenery.name="GeneratedArtworkScenery"
    world.add_child(scenery)
    for row in [["rock",Vector3(-.28,.01,-.04)],["driftwood",Vector3(.13,.01,.07)],["anubias",Vector3(-.09,.095,.125)],["java_fern",Vector3(-.28,.145,.005)]]:
        var packed: PackedScene=load("res://assets/aquascape-v2/"+row[0]+".glb")
        var model: Node3D=packed.instantiate()
        model.name=row[0]
        scenery.add_child(model)
        model.position=row[1]
        art_nodes[row[0]]=model
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            var originals: Array=[]
            for surface in mesh.mesh.get_surface_count():
                var mat: Material=mesh.get_active_material(surface)
                var copy: StandardMaterial3D=mat.duplicate()
                copy.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
                copy.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
                copy.metallic=0
                copy.metallic_specular=0
                copy.roughness=1
                originals.append(copy)
                mesh.set_surface_override_material(surface,copy)
            art_originals[mesh]=originals
    fish_stock=preload("res://scripts/aquarium/AquariumFishStock.gd").new()
    add_child(fish_stock)
    var entry: Dictionary=fish_stock.add_stock(world,"bluegill",Vector3(.36,.33,-.02),0.0)
    entry.carrier.position=Vector3(.36,.33,-.02)
    entry.carrier.rotation=Vector3.ZERO
    entry.player.pause()
    yaw=.20;pitch=.20;view_size=1.05;target=Vector3(0,.19,0)

func _ui() -> void:
    super._ui()
    for label in find_children("*","Label",true,false):
        if label.text.begins_with("A Q U A S C A P E"):
            label.text="A Q U A S C A P E   V 2    /    原 画 驱 动 置 景"
    mode_label.text="原画贴图 · 推断体积试验 / 待视觉审查"

func _mode(value: int) -> void:
    mode=value
    for mesh in art_originals:
        var originals: Array=art_originals[mesh]
        for surface in originals.size():
            if value==0:
                mesh.set_surface_override_material(surface,originals[surface])
            elif value==1:
                mesh.set_surface_override_material(surface,_solid(Color("8f9d9b")))
            else:
                var checker := ShaderMaterial.new()
                var shader := Shader.new()
                shader.code="""shader_type spatial;
                void fragment(){float q=mod(floor(UV.x*16.0)+floor(UV.y*16.0),2.0);ALBEDO=mix(vec3(.06,.25,.3),vec3(.85,.57,.20),q);ROUGHNESS=1.0;SPECULAR=0.0;}"""
                checker.shader=shader
                mesh.set_surface_override_material(surface,checker)
    if is_instance_valid(mode_label):mode_label.text=["原画贴图","实体灰模","映射格纹"][value]+" · 推断体积试验 / 待视觉审查"

func _unhandled_key_input(event: InputEvent) -> void:
    super._unhandled_key_input(event)
    if event is InputEventKey and event.pressed and event.keycode==KEY_R:
        yaw=.20;pitch=.20;view_size=1.05;target=Vector3(0,.19,0);_mode(0);_camera()

func _capture(directory: String) -> void:
    DirAccess.make_dir_recursive_absolute(directory)
    for i in 8:await get_tree().process_frame
    var outputs: Array=[]
    var views := [
        ["01-overview",0,.20,.20,1.05,Vector3(0,.19,0)],
        ["02-gray",1,.20,.20,1.05,Vector3(0,.19,0)],
        ["03-checker",2,.20,.20,1.05,Vector3(0,.19,0)],
        ["04-front",0,0,0,1.05,Vector3(0,.19,0)],
        ["05-back",0,PI+.20,.2,1.05,Vector3(0,.19,0)],
        ["06-top",0,0,1.46,1.05,Vector3(0,.14,0)],
        ["07-plants",0,.1,.15,.62,Vector3(-.18,.26,.03)],
        ["08-wood",0,.15,.10,.62,Vector3(.1,.15,.07)],
        ["09-side-gray",1,1.35,.15,.62,Vector3(-.12,.16,0)]
    ]
    for row in views:
        _mode(row[1]);yaw=row[2];pitch=row[3];view_size=row[4];target=row[5];_camera()
        for i in 3:await get_tree().process_frame
        await RenderingServer.frame_post_draw
        var path: String=directory+"/"+row[0]+".png"
        var err := get_viewport().get_texture().get_image().save_png(path)
        outputs.append({"path":path,"error":err})
    var triangles := 0
    var mesh_count := 0
    var invalid := 0
    for mesh in scenery.find_children("*","MeshInstance3D",true,false):
        mesh_count+=1
        for surface in mesh.mesh.get_surface_count():
            var a: Array=mesh.mesh.surface_get_arrays(surface)
            triangles+=(a[Mesh.ARRAY_INDEX].size() if a[Mesh.ARRAY_INDEX]!=null else a[Mesh.ARRAY_VERTEX].size())/3
            for v in a[Mesh.ARRAY_VERTEX]:
                if not v.is_finite():invalid+=1
    var data := {"command":"aquascape.art-v2-render","ok":invalid==0,"status":"done","next_action":"human_review","outputs":outputs,"failures":[],"summary":{"meshes":mesh_count,"triangles":triangles,"invalid_vertices":invalid,"source_materials":"Actual generated complete objects and individual leaf paintings"},"limitations":["Solid depth inferred from contour distance. Top orthographic reference generation did not pass visual review.","This is an artwork-led 3D experiment, not an approved full reconstruction."],"visual_review":"pending","user_acceptance":"pending"}
    var file := FileAccess.open(directory+"/validation-report.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(data,"  "))
    print(JSON.stringify(data))
    get_tree().quit()
