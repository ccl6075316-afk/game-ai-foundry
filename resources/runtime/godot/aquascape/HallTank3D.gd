extends "res://scripts/aquarium/MarineShowcase.gd"
## Embeddable exhibit: the hall owns camera, environment, input and UI.
var fish_limit := 8
var initial_content: Dictionary={}
var content_snapshot: Dictionary={}
var exterior_base: MeshInstance3D
var exterior_rim: Array=[]
var backdrop_paint: ShaderMaterial

func _ready() -> void:
    layout=JSON.parse_string(FileAccess.get_file_as_string(LAYOUT))
    _environment()
    _substrate()
    _ornaments()
    if not initial_content.is_empty():apply_content(initial_content)
    _fish()
    _step(0)

func _environment() -> void:
    var rim := _solid(Color("48747c"))
    exterior_base=_box(Vector3(0,-.22,0),Vector3(6.16,.40,3.16),_solid(Color("132e38")))
    exterior_rim.append(_box(Vector3(0,-.012,0),Vector3(6.04,.025,3.04),rim))
    backdrop_paint=ShaderMaterial.new();backdrop_paint.shader=load("res://scripts/aquarium/MarineBackdrop.gdshader")
    _box(Vector3(0,1.40,-1.52),Vector3(6.03,2.8,.025),backdrop_paint)
    for y in [0.0,2.8]:
        for z in [-1.50,1.50]:exterior_rim.append(_box(Vector3(0,y,z),Vector3(6.08,.028,.028),rim))
        for x in [-3.0,3.0]:exterior_rim.append(_box(Vector3(x,y,0),Vector3(.028,.028,3.04),rim))
    for x in [-3.0,3.0]:
        for z in [-1.5,1.5]:exterior_rim.append(_box(Vector3(x,1.4,z),Vector3(.022,2.8,.022),rim))
    var plane := PlaneMesh.new();plane.size=Vector2(6,3)
    var surface := MeshInstance3D.new();surface.mesh=plane;surface.position.y=2.775
    water_paint=ShaderMaterial.new();water_paint.shader=load("res://shaders/aquarium_lab_surface.gdshader")
    # The shared water-volume pass handles the surface interface and interior.
    water_paint.set_shader_parameter("strength",0.0);water_paint.set_shader_parameter("pixel_size",.045)
    surface.material_override=water_paint;add_child(surface)

func apply_exterior_materials(base: Material,rim: Material) -> void:
    exterior_base.material_override=base
    for mesh in exterior_rim:mesh.material_override=rim

func _ui() -> void:pass
func _camera() -> void:pass
func _unhandled_input(_event: InputEvent) -> void:pass

func _fish() -> void:
    if fish_limit<=0:return
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    factory._load_profiles()
    var species := ["red_emperor","red_seabream","black_seabream","yellow_croaker"]
    for i in fish_limit:
        var id: String=species[i%species.size()]
        var profile: Dictionary=factory.profiles[id]
        factory._add_fish(self,id,float(profile.real_length_cm)/100,profile,Vector3.ZERO,i*.37)
        var row: Dictionary=factory.fish[-1]
        row["bounds"]=_model_bounds(row.model)
        row["lane"]=i%3
        row["phase"]=float(i)/maxi(1,fish_limit)
        fish.append(row)

func set_fish_count(count: int) -> void:
    for row in fish:row.carrier.hide();row.carrier.queue_free()
    fish.clear()
    if is_instance_valid(factory):factory.free()
    factory=null;fish_limit=clampi(count,0,15)
    _fish()

func content_state() -> Dictionary:
    if not content_snapshot.is_empty():return content_snapshot.duplicate(true)
    var rocks: Array=[]
    for row in props:
        var p: Vector3=row.node.position/5
        rocks.append({"id":row.id,"position":[p.x,p.y,p.z],"scale":row.node.scale.x/5,"yaw":row.node.rotation.y})
    return {"schema_version":3,"sand":"fine_sand","grid":[bed.NX,bed.NZ],"heights":Array(bed.heights),"materials":Array(bed.material_ids),"selected_substrate":bed.active_material,"rocks":rocks}

func apply_content(state: Dictionary) -> void:
    # Keep authored edit coordinates; repeated float32 render transform
    # conversion must not drift the saved document or break undo equality.
    content_snapshot=state.duplicate(true)
    bed.heights=PackedFloat32Array(state.heights)
    bed.material_ids=PackedByteArray(state.materials)
    bed.active_material=int(state.get("selected_substrate",0))
    bed.rebuild_all()
    for row in props:row.node.hide();row.node.queue_free()
    props.clear()
    for row in state.rocks:
        var spec: Dictionary=specs[row.id]
        var model: Node3D=(load(spec.model) as PackedScene).instantiate();add_child(model)
        var box := _model_bounds(model)
        if not paints.has(row.id):
            var paint := ShaderMaterial.new();paint.shader=load("res://scripts/aquarium/DecorThreeViewArtwork.gdshader")
            for view in ["front","right","top"]:paint.set_shader_parameter(view+"_art",load(spec.material_dir+"/"+row.id+"-"+view+".png"))
            var d: Dictionary=spec.projection_bounds
            paint.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
            paint.set_shader_parameter("radial_jar",row.id=="terracotta_jar")
            paint.set_shader_parameter("right_art_on_rear",row.id=="coconut_shelter")
            paints[row.id]=paint
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            for s in mesh.mesh.get_surface_count():mesh.set_surface_override_material(s,paints[row.id])
        model.scale=Vector3.ONE*float(row.scale)*5
        model.rotation.y=float(row.yaw)
        model.position=Vector3(float(row.position[0]),float(row.position[1]),float(row.position[2]))*5
        props.append({"id":row.id,"node":model,"bounds":box})
