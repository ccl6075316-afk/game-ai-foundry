extends Node3D
const Interior = preload("ShellInterior.gd")
const Algae = preload("StoneAlgae.gd")
const Current = preload("RootedCurrent.gd")
const Design = preload("ShellDesign.gd")
const Factory = preload("../FishInstanceFactory.gd")
static var profiles: Dictionary={}
var factory: RefCounted
var lamp := OmniLight3D.new()
var props: Array[Dictionary]=[]
var swimmers: Array[Dictionary]=[]
var elapsed:=0.0
var light_layer:=0

func _ready() -> void:
    # The hall floor and neighbouring exhibits must keep their own lighting.
    var occupied:=0
    for other in get_tree().get_nodes_in_group("shell_lamp_receivers"):
        if other.get_viewport()==get_viewport() and not other.is_queued_for_deletion():
            occupied |= other.light_layer
    for bit in range(1,20):
        if not occupied & (1<<bit):
            light_layer=1<<bit
            break
    add_to_group("shell_lamp_receivers")
    lamp.light_cull_mask=light_layer
    (get_parent() as MeshInstance3D).layers=light_layer | 1
    add_child(lamp)
    set_process(false)

func sync(data: Dictionary,bed: Dictionary) -> void:
    var box:=Interior.bounds(data.design)
    var path:=Design.contour(data.design)
    var height:float=data.design.height
    lamp.position=Vector3(box.get_center().x,height*.84,box.get_center().y)
    lamp.omni_range=maxf(box.size.length()*.7,height)
    lamp.omni_attenuation=.8
    lamp.light_energy=bed.get("brightness",1.0)*1.5
    lamp.light_color={"neutral":Color("#f3faff"),"warm":Color("#ffc27c"),"cool":Color("#8fdcff")}[bed.get("tint","neutral")]
    reconcile(props,bed.get("props",[]),false)
    reconcile(swimmers,bed.get("fish",[]),true)
    for entry in props:
        entry.root.transform=Interior.prop_pose(entry.item,box,path,bed,height,entry.bounds)
    var bed_top:=float(bed.depth_cm)*.01
    for h in bed.get("heights",[]):bed_top=maxf(bed_top,float(bed.depth_cm)*.01+h*Interior.waterline(height))
    for entry in swimmers:
        var p:=box.position+box.size*Vector2(entry.item.u,entry.item.v)
        entry.center=Vector3(p.x,lerpf(bed_top,Interior.waterline(height),.54),p.y)
        entry.radius=minf(Interior.clearance(p,path)-entry.length*.61,entry.length*1.4)
        if entry.has("arapaima"):entry.arapaima.fit(entry,box,bed,height,props)
    set_process(not swimmers.is_empty())
    if not swimmers.is_empty():_process(0)

func reconcile(entries: Array[Dictionary],items: Array,fish: bool) -> void:
    # Match each occurrence once. Changing sand or light keeps every rig alive.
    var remaining:=entries.duplicate()
    entries.clear()
    for item in items:
        var index:=remaining.find_custom(func(e):return e.item==item)
        if index>=0:entries.append(remaining.pop_at(index));continue
        var entry:=make_fish(item,entries.size()) if fish else make_prop(item)
        if not entry.is_empty():entries.append(entry)
    for old in remaining:
        old.root.hide()
        old.root.queue_free()

func resume_fish_from(other: Node3D) -> void:
    if other==null:return
    var remaining: Array=other.swimmers.duplicate()
    for entry in swimmers:
        if not entry.has("arapaima"):continue
        var index:=remaining.find_custom(func(e):return e.item==entry.item)
        if index>=0:
            entry.arapaima.resume_from(remaining.pop_at(index).arapaima)
            entry.arapaima.advance(entry,0.0)

func make_prop(item: Dictionary) -> Dictionary:
    var asset:Dictionary=Interior.assets()[item.id]
    var model: Node3D=(load(asset.model) as PackedScene).instantiate()
    var anchor:=Node3D.new()
    add_child(anchor);anchor.add_child(model)
    var box:=AABB()
    var first:=true
    for child: MeshInstance3D in model.find_children("*","MeshInstance3D",true,false):
        child.layers=light_layer | 1
        if asset.has("rooted_current"):
            Current.apply(child, asset.rooted_current)
        var extent: AABB=(anchor.global_transform.affine_inverse()*child.global_transform)*child.get_aabb()
        box=extent if first else box.merge(extent)
        first=false
    if item.get("algae",false) and Interior.supports_algae(item.id):
        for mesh: MeshInstance3D in model.find_children("*","MeshInstance3D",true,false):
            Algae.apply(mesh)
    var factor:=1.0/maxf(.001,box.size[box.size.max_axis_index()])
    var original_transform:=model.transform
    model.scale*=factor
    model.position-=Vector3(box.get_center().x,box.position.y,box.get_center().z)*factor
    return {"item":item,"root":anchor,"bounds":(model.transform*original_transform.affine_inverse())*box}

func make_fish(item: Dictionary,index: int) -> Dictionary:
    if factory==null:factory=Factory.new()
    if profiles.is_empty():profiles=factory.load_profiles()
    var length_m:=Interior.length_m(item.id)
    var phase:=fmod(index*2.4+item.u*7.0,TAU)
    var rig:Dictionary=factory.create_display(self,item.id,length_m,profiles[item.id],Vector3.ZERO,phase)
    if rig.is_empty():return {}
    for mesh: MeshInstance3D in rig.model.find_children("*","MeshInstance3D",true,false):
        mesh.layers=light_layer | 1
    var entry: Dictionary={"item":item,"root":rig.carrier,"controller":rig.controller,"length":length_m,"sign":rig.profile.head_sign,"phase":phase}
    if item.id=="arapaima":
        entry.arapaima=preload("ArapaimaTankMotion.gd").new()
        var release=factory._release(factory.model_path(item.id),item.id)
        entry.arapaima.setup(rig,phase,factory._recipe(release,item.id))
    return entry

func _process(delta: float) -> void:
    if not is_visible_in_tree():return
    elapsed+=delta
    for entry in swimmers:
        if entry.has("arapaima"):
            entry.arapaima.advance(entry,delta)
            continue
        entry.controller.step(delta)
        var a:float=entry.phase+elapsed*.58
        var tangent:=Vector2(-sin(a),cos(a))*float(entry.sign)
        entry.root.transform=Transform3D(Basis(Vector3.UP,-tangent.angle()),entry.center+entry.radius*Vector3(cos(a),0,sin(a)))
