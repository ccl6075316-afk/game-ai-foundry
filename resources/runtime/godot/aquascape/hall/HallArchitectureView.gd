extends Node3D
## Derived geometry only. Ceiling coverage, floor finishes and guards share the layout.
const Storeys=preload("HallStoreys.gd")
const Architecture=preload("HallArchitecture.gd")
var projection: RefCounted
var materials: Array[Material]=[]

func rebuild(layout: Dictionary,source: RefCounted,floor_paint: Material) -> void:
    projection=source
    for child in get_children():
        remove_child(child);child.queue_free()
    if materials.is_empty():
        materials.resize(Architecture.FINISH_NAMES.size());materials[0]=floor_paint
        var slate := ShaderMaterial.new();slate.shader=preload("../reviews/HallExhibitFloor.gdshader");materials[1]=slate
    # Merge adjacent cells into strips rather than one draw call per square metre.
    for field in ["floor_finishes","ceilings"]:
        var strips := {}
        for cell in layout.get(field,[]):
            var key := Vector3(cell[1],cell[2],cell[3])
            if not strips.has(key):strips[key]=[]
            strips[key].append(int(cell[0]))
        for key: Vector3 in strips:
            var xs: Array=strips[key];xs.sort()
            var start: int=xs[0]
            for i in range(1,xs.size()+1):
                if i<xs.size() and xs[i]==xs[i-1]+1:continue
                var width: float=xs[i-1]-start+1
                var holder := Node3D.new();holder.set_meta("level",int(key.x));holder.set_meta("ceiling",field=="ceilings");add_child(holder)
                var ceiling: bool=field=="ceilings"
                var y := Storeys.elevation(int(key.x))+(key.z+.08 if ceiling else .005)
                var paint: Material=source.wall_paint if ceiling else _finish_material(int(key.z))
                var size := Vector3(width,.16 if ceiling else .008,1)
                source._box(holder,Vector3(start+width*.5,y,key.y+.5),size,paint)
                if ceiling:source._collision(holder,Vector3(start+width*.5,y,key.y+.5),size)
                if i<xs.size():start=xs[i]
    var tiles := Storeys.index(layout.get("floor_tiles",[]))
    var rail_paint: Material=source._surface(Color("405b63"),"hall_wall")
    for cell: Vector3i in tiles:
        for direction in [Vector3i.LEFT,Vector3i.RIGHT,Vector3i.FORWARD,Vector3i.BACK]:
            if tiles.has(cell+direction):continue
            var p := Vector3(cell.x+.5,Storeys.elevation(cell.y),cell.z+.5)+Vector3(direction)*.5
            var stair_exit := false
            for object in layout.objects:
                if object.kind!="stair" or Storeys.level(object)+1!=cell.y:continue
                var local: Vector3=source._transform(object).affine_inverse()*p
                if absf(local.x-Storeys.RUN*.5)<.06 and absf(local.z)<Storeys.WIDTH*.5+.01:stair_exit=true;break
            if stair_exit:continue
            var holder := Node3D.new();holder.set_meta("level",cell.y);holder.set_meta("guard",true);add_child(holder)
            var along := Vector3(0,0,1) if direction.x!=0 else Vector3(1,0,0)
            var size := Vector3(.07,.07,1) if direction.x!=0 else Vector3(1,.07,.07)
            source._box(holder,p+Vector3.UP*1.05,size,rail_paint)
            source._box(holder,p+Vector3.UP*.5,size,rail_paint)
            for sign in [-1,1]:source._box(holder,p+along*sign*.46+Vector3.UP*.52,Vector3(.06,1.04,.06),rail_paint)
            size.y=1.1
            source._collision(holder,p+Vector3.UP*.55,size)

    _batch_guards(rail_paint)

func _finish_material(index: int) -> Material:
    # Load only finishes actually painted in this hall, then reuse across strips.
    if materials[index]==null:
        var paint := ShaderMaterial.new();paint.shader=preload("../HallFloor3D.gdshader")
        paint.set_shader_parameter("floor_art",load(Architecture.FINISH_TEXTURES[index]))
        paint.set_shader_parameter("artwork_repeat_metres",Architecture.FINISH_REPEAT_METRES[index])
        paint.set_shader_parameter("tile_color",Color(.4667,.5529,.5451));materials[index]=paint
    return materials[index]

func _batch_guards(paint: Material) -> void:
    var instances := {}
    for holder in get_children():
        if not holder.get_meta("guard",false):continue
        var level: int=holder.get_meta("level")
        if not instances.has(level):instances[level]=[]
        for child in holder.get_children():
            if not child is MeshInstance3D:continue
            instances[level].append(Transform3D(child.basis.scaled(child.mesh.size),child.position))
            holder.remove_child(child);child.queue_free()
    for level in instances:
        var holder := Node3D.new();holder.set_meta("level",level);add_child(holder)
        var mesh := BoxMesh.new();mesh.size=Vector3.ONE;mesh.material=paint
        var batch := MultiMesh.new();batch.transform_format=MultiMesh.TRANSFORM_3D;batch.mesh=mesh
        batch.instance_count=instances[level].size()
        for i in batch.instance_count:batch.set_instance_transform(i,instances[level][i])
        var node := MultiMeshInstance3D.new();node.multimesh=batch;holder.add_child(node)

func set_view(level: int,editing: bool) -> void:
    for child in get_children():
        child.visible=not editing or (not child.get_meta("ceiling",false) and child.get_meta("level")==level)
        for body in child.get_children():
            if body is StaticBody3D:body.collision_layer=1 if child.visible else 0
