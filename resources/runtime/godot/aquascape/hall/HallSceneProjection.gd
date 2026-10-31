extends RefCounted
## Materialize a document into live geometry. No UI, history or file writes.
const WaterProfile=preload("res://scripts/aquarium/TankWaterProfile.gd")
const Footprint=preload("res://scripts/aquarium/HallFootprint.gd")
var world: Node3D
var rules: RefCounted
var surface: Callable
var hall_lighting: Node3D
var wall_paint: StandardMaterial3D
var room_geometry: Node3D

func _init(scene_world: Node3D,layout_rules: RefCounted,material_factory: Callable,lighting: Node3D) -> void:
    world=scene_world;rules=layout_rules;surface=material_factory;hall_lighting=lighting

func _surface(color: Color,art: String,art_tint: Color=Color.TRANSPARENT) -> StandardMaterial3D:
    return surface.call(color,art,art_tint)

func _bounds(data: Dictionary) -> AABB:
    return rules._bounds(data)

func _transform(data: Dictionary) -> Transform3D:
    return rules._transform(data)

func _box(parent: Node3D,at: Vector3,size: Vector3,paint: Material) -> MeshInstance3D:
    var node := MeshInstance3D.new();var box := BoxMesh.new();box.size=size
    node.mesh=box;node.material_override=paint;node.position=at;parent.add_child(node)
    return node

func _collision(parent: Node3D,at: Vector3,size: Vector3,layer:=1) -> StaticBody3D:
    var body := StaticBody3D.new();body.collision_layer=layer;body.collision_mask=0;parent.add_child(body)
    var shape := CollisionShape3D.new();var box := BoxShape3D.new();box.size=size
    shape.shape=box;shape.position=at;body.add_child(shape)
    return body

func _clear_geometry(node: Node3D) -> void:
    for child in node.get_children():
        if child is StaticBody3D:child.collision_layer=0
        node.remove_child(child);child.queue_free()

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

func rebuild_room(parcels: Array,editing: bool,floor_paint: Material,room_wall_paint: StandardMaterial3D) -> void:
    wall_paint=room_wall_paint
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

func apply_layout(objects: Array,state: Dictionary,change: Dictionary={}) -> Array:
    var retained: Array=[]
    for data in state.objects:
        var found: Dictionary={}
        for row in objects:
            if row.data.id==data.id and row.data.kind==data.kind:found=row;break
        if found.is_empty():found=_create(data)
        elif change.is_empty() or (change.get("kind")=="patch" and change.get("id")==data.id):
            var fields: Array=change.get("fields",[])
            if data.kind=="tank":
                if (change.is_empty() or "fish_count" in fields) and int(data.fish_count)!=int(found.data.fish_count):found.tank.set_fish_count(int(data.fish_count))
                if (change.is_empty() or "content" in fields) and not data.get("content",{}).is_empty() and JSON.stringify(found.tank.content_state())!=JSON.stringify(data.content):found.tank.apply_content(data.content)
            found.data=data.duplicate(true);found.node.transform=_transform(data)
            if data.kind=="wall" and (change.is_empty() or "length" in fields or "door" in fields):_refresh_wall(found)
        if data.kind=="tank":found.data.water=WaterProfile.normalized(data.get("water",{}))
        retained.append(found)
    for row in objects:
        if not retained.has(row):row.node.hide();row.body.collision_layer=0;row.node.queue_free()
    return retained

func initial_contents(rows: Array) -> Dictionary:
    var contents: Dictionary={}
    for row in rows:
        if row.tank!=null and row.data.content.is_empty():contents[row.data.id]=row.tank.content_state()
    return contents
