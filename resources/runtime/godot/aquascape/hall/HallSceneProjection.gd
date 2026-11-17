extends RefCounted
## Materialize a document into live geometry. No UI, history or file writes.
const WaterProfile=preload("res://scripts/aquarium/TankWaterProfile.gd")
const Footprint=preload("res://scripts/aquarium/HallFootprint.gd")
const Storeys=preload("res://scripts/aquarium/hall/HallStoreys.gd")
var world: Node3D
var rules: RefCounted
var surface: Callable
var hall_lighting: Node3D
var wall_paint: StandardMaterial3D
var room_geometry: Node3D
var floor_geometry: Node3D
var floor_guides: Node3D
var lower_floor_reference: Node3D
var reference_floor_paint: StandardMaterial3D
var reference_wall_paint: StandardMaterial3D
var reference_object_paint: StandardMaterial3D
var reference_tank_rim_paint: StandardMaterial3D

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
        var exhibit_origin := Node3D.new();exhibit_origin.position.y=.43;root.add_child(exhibit_origin)
        # Fish can remain visible over the translucent lower-storey tank frame.
        var fish_visuals := Node3D.new();fish_visuals.name="FishVisuals";exhibit_origin.add_child(fish_visuals)
        tank.fish_visuals=fish_visuals;exhibit_origin.add_child(tank)
        tank.apply_exterior_materials(_surface(Color("132e38"),"hall_floor",Color("456e79")),_surface(Color("48747c"),"hall_wall"))
        hall_lighting.attach_tank(tank)
    elif data.kind=="wall":
        _wall_geometry(root,data)
    elif data.kind=="stair":
        _stair_geometry(root,data)
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
    elif data.kind=="stair":body=root.get_meta("stair_body")
    else:body=_collision(root,box.get_center(),box.size,2);body.set_meta("hall_id",data.id)
    var row := {"data":data.duplicate(true),"node":root,"body":body,"tank":tank}
    if data.kind=="tank":row.data.water=WaterProfile.normalized(data.get("water",{}))
    root.transform=_transform(data)
    return row

func _stair_geometry(root: Node3D,data: Dictionary) -> void:
    var tread := _surface(Color("708681"),"hall_floor",Color("b3c1bd"))
    var edge := _surface(Color("34515b"),"hall_wall")
    edge.emission_enabled=true;edge.emission=Color("5f8c90");edge.emission_energy_multiplier=.32
    var steps := 20
    var half_run := Storeys.RUN*.5
    var half_width := Storeys.WIDTH*.5
    var depth := Storeys.RUN/steps
    var rise := Storeys.HEIGHT/steps
    for i in steps:
        var x := -half_run+(float(i)+.5)*depth
        var top := (i+1)*rise
        _box(root,Vector3(x,top*.5,0),Vector3(depth,top,Storeys.WIDTH),tread)
        _box(root,Vector3(x-depth*.5+.025,top+.008,0),Vector3(.05,.015,Storeys.WIDTH),edge)
    var body := StaticBody3D.new()
    body.collision_layer=2;body.collision_mask=0;body.set_meta("hall_id",data.id)
    root.add_child(body);root.set_meta("stair_body",body)
    # A continuous collision surface lets CharacterBody3D traverse the full flight.
    var ramp := ConvexPolygonShape3D.new()
    var points := PackedVector3Array()
    for z in [-half_width,half_width]:
        points.append(Vector3(-half_run,-.05,z))
        points.append(Vector3(half_run,-.05,z))
        points.append(Vector3(half_run,Storeys.HEIGHT,z))
        points.append(Vector3(-half_run,0,z))
    ramp.points=points
    var ramp_shape := CollisionShape3D.new();ramp_shape.shape=ramp;body.add_child(ramp_shape)
    var angle := atan2(Storeys.HEIGHT,Storeys.RUN)
    var rail_length := Vector2(Storeys.RUN,Storeys.HEIGHT).length()
    for side in [-1,1]:
        var z: float=side*(half_width-.045)
        var rail := _box(root,Vector3(0,Storeys.HEIGHT*.5+Storeys.RAIL-.05,z),Vector3(rail_length,.09,.10),edge)
        rail.rotation.z=angle
        for i in 6:
            var t := float(i)/5
            _box(root,Vector3(lerpf(-half_run+.07,half_run-.07,t),
                Storeys.HEIGHT*t+Storeys.RAIL*.5,z),Vector3(.07,Storeys.RAIL,.07),edge)
        var barrier := CollisionShape3D.new();var barrier_box := BoxShape3D.new()
        barrier_box.size=Vector3(rail_length,.94,.10);barrier.shape=barrier_box
        barrier.position=Vector3(0,Storeys.HEIGHT*.5+.5,z);barrier.rotation.z=angle;body.add_child(barrier)

func rebuild_floors(tiles: Array,floor_paint: Material) -> void:
    if not is_instance_valid(floor_geometry):
        floor_geometry=Node3D.new();floor_geometry.name="UpperFloorSlabs";world.add_child(floor_geometry)
    _clear_geometry(floor_geometry)
    var strips := {}
    for tile in tiles:
        var cell := Storeys.key(tile)
        var row := Vector2i(cell.y,cell.z)
        if not strips.has(row):strips[row]=[]
        strips[row].append(cell.x)
    var levels := {}
    for row: Vector2i in strips:
        if not levels.has(row.x):
            var level := Node3D.new();level.set_meta("level",row.x);floor_geometry.add_child(level)
            levels[row.x]=level
        var xs: Array=strips[row]
        xs.sort()
        var start: int=xs[0]
        for i in range(1,xs.size()+1):
            if i<xs.size() and xs[i]==xs[i-1]+1:continue
            var width: float=xs[i-1]-start+1
            var size := Vector3(width,Storeys.SLAB,1)
            var p := Vector3(start+width*.5,Storeys.elevation(row.x)-Storeys.SLAB*.5,row.y+.5)
            _box(levels[row.x],p,size,floor_paint)
            _collision(levels[row.x],p,size)
            if i<xs.size():start=xs[i]

func show_floors(storey: int,editing: bool) -> void:
    room_geometry.visible=not editing or storey==0
    if is_instance_valid(floor_geometry):
        for node in floor_geometry.get_children():
            node.visible=not editing or int(node.get_meta("level"))==storey

func show_floor_below(storey: int,editing: bool,objects: Array) -> void:
    if not is_instance_valid(lower_floor_reference):
        lower_floor_reference=Node3D.new();lower_floor_reference.name="LowerFloorReference"
        world.add_child(lower_floor_reference)
        reference_floor_paint=_reference_paint(Color(.29,.41,.55,.28),-30)
        reference_wall_paint=_reference_paint(Color(.40,.50,.61,.27),-29)
        reference_object_paint=_reference_paint(Color(.35,.48,.52,.32),-28)
        reference_tank_rim_paint=_reference_paint(Color(.44,.64,.69,.53),-27)
    _clear_geometry(lower_floor_reference)
    lower_floor_reference.visible=editing and storey>0
    if not lower_floor_reference.visible:return

    var below := storey-1
    if below==0:
        for source in room_geometry.get_children():
            if not source is MeshInstance3D or source.name=="LowGuideLight":continue
            # Keep the taller ground perimeter below the active construction plane.
            var size: Vector3=source.mesh.size
            var at: Vector3=source.position
            var excess := maxf(0,at.y+size.y*.5-Storeys.HEIGHT)
            size.y-=excess;at.y-=excess*.5
            var paint := reference_floor_paint if at.y<0 else reference_wall_paint
            var copy := _box(lower_floor_reference,at,size,paint)
            copy.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    elif is_instance_valid(floor_geometry):
        for level in floor_geometry.get_children():
            if int(level.get_meta("level"))!=below:continue
            for source in level.get_children():
                if source is MeshInstance3D:_reference_mesh(source,reference_floor_paint)

    for row in objects:
        if Storeys.level(row.data)!=below or row.data.kind=="stair":continue
        if row.tank!=null:
            # Keep the tank footprint and frame readable without the live water composite.
            _reference_mesh(row.tank.exterior_base,reference_object_paint)
            for rim in row.tank.exterior_rim:_reference_mesh(rim,reference_tank_rim_paint)
            for source in row.tank.get_children():
                if source is MeshInstance3D and source.material_override==row.tank.water_paint:
                    _reference_mesh(source,reference_floor_paint)
        else:
            var paint := reference_wall_paint if row.data.kind=="wall" else reference_object_paint
            for source in row.node.find_children("*","MeshInstance3D",true,false):
                _reference_mesh(source,paint)

func _reference_paint(color: Color,priority: int) -> StandardMaterial3D:
    var paint := StandardMaterial3D.new()
    paint.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    paint.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    paint.albedo_color=color
    paint.render_priority=priority
    return paint

func _reference_mesh(source: MeshInstance3D,paint: Material) -> void:
    var copy := MeshInstance3D.new()
    copy.mesh=source.mesh;copy.material_override=paint
    copy.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    lower_floor_reference.add_child(copy)
    copy.global_transform=source.global_transform

func show_floor_guides(storey: int,editing: bool,parcels: Array,objects: Array,tiles: Dictionary) -> void:
    if not is_instance_valid(floor_guides):
        floor_guides=Node3D.new();floor_guides.name="FloorBuildGuides";world.add_child(floor_guides)
    _clear_geometry(floor_guides)
    if not editing or storey==0:return
    var y := Storeys.elevation(storey)+.018
    var paint := StandardMaterial3D.new()
    paint.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    paint.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    paint.albedo_color=Color(.39,.65,.71,.38)
    var grid := ImmediateMesh.new();grid.surface_begin(Mesh.PRIMITIVE_LINES,paint)
    for cell in parcels:
        var p := Footprint.rect(cell)
        for x in range(int(p.position.x),int(p.end.x)+1):
            grid.surface_add_vertex(Vector3(x,y,p.position.y));grid.surface_add_vertex(Vector3(x,y,p.end.y))
        for z in range(int(p.position.y),int(p.end.y)+1):
            grid.surface_add_vertex(Vector3(p.position.x,y,z));grid.surface_add_vertex(Vector3(p.end.x,y,z))
    grid.surface_end()
    var lines := MeshInstance3D.new();lines.mesh=grid
    lines.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;floor_guides.add_child(lines)
    var outline_vertices: Array[Vector3]=[]
    for spot: Vector3i in tiles:
        if spot.y!=storey:continue
        var p := Vector3(spot.x,y+.012,spot.z)
        for side in [[Vector3i(-1,0,0),Vector3.ZERO,Vector3.BACK],
            [Vector3i(1,0,0),Vector3.RIGHT,Vector3(1,0,1)],
            [Vector3i(0,0,-1),Vector3.ZERO,Vector3.RIGHT],
            [Vector3i(0,0,1),Vector3.BACK,Vector3(1,0,1)]]:
            if tiles.has(spot+side[0]):continue
            outline_vertices.append(p+side[1]);outline_vertices.append(p+side[2])
    if not outline_vertices.is_empty():
        var border := paint.duplicate() as StandardMaterial3D
        border.albedo_color=Color(.46,.87,.77,.92)
        var outline := ImmediateMesh.new();outline.surface_begin(Mesh.PRIMITIVE_LINES,border)
        for vertex in outline_vertices:outline.surface_add_vertex(vertex)
        outline.surface_end()
        var border_mesh := MeshInstance3D.new();border_mesh.mesh=outline
        border_mesh.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;floor_guides.add_child(border_mesh)
    var marker := paint.duplicate() as StandardMaterial3D;marker.albedo_color=Color(.97,.72,.36,.58)
    for row in objects:
        var data: Dictionary=row.data
        if data.kind!="stair" or Storeys.level(data)+1!=storey:continue
        for spot in Storeys.cells_in(_transform(data)*Storeys.stair_landing(true),storey):
            if tiles.has(spot):continue
            var guide := _box(floor_guides,Vector3(spot.x+.5,y+.01,spot.z+.5),Vector3(.92,.018,.92),marker)
            guide.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

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
