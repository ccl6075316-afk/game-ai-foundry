extends RefCounted
## Layout schema and placement rules shared by load and editor; no scene mutation.
const Footprint=preload("res://scripts/aquarium/HallFootprint.gd")
const Storeys=preload("res://scripts/aquarium/hall/HallStoreys.gd")
const WaterProfile=preload("res://scripts/aquarium/TankWaterProfile.gd")
const MAX_OBJECTS=80
const MAX_TANKS=8
var placement_error := ""

func _bounds(data: Dictionary) -> AABB:
    if data.kind=="stair":return Storeys.stair_bounds()
    if data.kind=="wall":return AABB(Vector3(-float(data.length)/2,0,-.09),Vector3(float(data.length),3.2,.18))
    if data.kind=="tank":return AABB(Vector3(-3.1,0,-1.6),Vector3(6.2,3.3,3.2))
    if data.kind=="bench":return AABB(Vector3(-1,0,-.34),Vector3(2,.72,.68))
    return AABB(Vector3(-.55,0,-.55),Vector3(1.1,1.6,1.1))

func _transform(data: Dictionary) -> Transform3D:
    return Transform3D(Basis(Vector3.UP,float(data.yaw)).scaled(Vector3.ONE*float(data.scale)),
        Vector3(float(data.at[0]),Storeys.elevation(Storeys.level(data)),float(data.at[1])))

func _clearance_boxes(data: Dictionary,box: AABB) -> Array[AABB]:
    if data.kind!="stair":return [box]
    var pose := _transform(data)
    return [box,pose*Storeys.stair_landing(false),pose*Storeys.stair_landing(true)]

func _valid_placement(data: Dictionary,rows: Array,ignore_id: String="",cells: Array=[]) -> bool:
    placement_error=""
    var box: AABB=_transform(data)*_bounds(data)
    var spaces := _clearance_boxes(data,box)
    for space in spaces:
        if not Footprint.contains(Footprint.initial() if cells.is_empty() else cells,space):
            placement_error="超出已扩建地基或贴到外墙。";return false
    for row in rows:
        var other: Dictionary=row.data if row.has("data") else row
        if other.id==ignore_id:continue
        var occupied: AABB=_transform(other)*_bounds(other)
        if data.kind=="wall" and other.kind=="wall":
            # T and cross junctions are intentional; overlapping parallel walls are not.
            var axis: Vector3=_transform(data).basis.x.normalized()
            var parallel: bool=absf(axis.dot(_transform(other).basis.x.normalized()))>.99
            if not parallel:continue
            if box.intersection(occupied).get_volume()>.002:placement_error="这里已有一段重叠隔墙。";return false
        else:
            for a in spaces:
                for b in _clearance_boxes(other,occupied):
                    # Clearance is horizontal. A room directly above another may share the same footprint.
                    if a.grow(.12).intersects(b) and a.position.y<b.end.y and b.position.y<a.end.y:
                        placement_error="与现有物件、楼梯或楼梯出口重叠。";return false
    return true

func _valid_level_support(data: Dictionary,tiles: Dictionary) -> bool:
    var storey := Storeys.level(data)
    var pose := _transform(data)
    var footprint := pose*_bounds(data)
    if storey>0:
        var support := pose*Storeys.stair_landing(false) if data.kind=="stair" else footprint
        for cell in Storeys.cells_in(support,storey):
            if not tiles.has(cell):
                placement_error="请先铺好这一层的承托地板。"
                return false
    if data.kind=="stair" or footprint.end.y>Storeys.elevation(storey+1)-Storeys.SLAB+.0001:
        for cell in Storeys.cells_in(footprint,storey+1):
            if tiles.has(cell):
                placement_error="这里需要为楼梯留开口。" if data.kind=="stair" else "物件会穿过上层楼板。"
                return false
    return true

func _valid_storeys(layout: Dictionary) -> bool:
    var tiles: Variant=layout.get("floor_tiles")
    if not tiles is Array or tiles.size()>Footprint.LIMIT*int(Footprint.CELL.x*Footprint.CELL.y)*Storeys.MAX_LEVEL:return false
    var occupied := {}
    for tile in tiles:
        if not Storeys.valid_tile(tile):return false
        var cell := Storeys.key(tile)
        if occupied.has(cell) or not Footprint.contains(layout.parcels,Storeys.slab_bounds(cell),0):
            placement_error="地板需铺在已扩建地基的范围内。";return false
        occupied[cell]=true
    for row in layout.objects:
        if not _valid_level_support(row,occupied):return false
    return true

func _finite_number(value: Variant) -> bool:
    return (value is int or value is float) and is_finite(float(value))

func _valid_content(data: Variant) -> bool:
    if not data is Dictionary:return false
    if data.is_empty():return true
    if data.get("schema_version")!=3 or data.get("sand")!="fine_sand":return false
    if not data.get("grid") is Array or data.grid.size()!=2 or data.grid[0]!=129 or data.grid[1]!=65:return false
    if not data.get("heights") is Array or data.heights.size()!=8385 or not data.get("materials") is Array or data.materials.size()!=8385:return false
    for h in data.heights:
        if not _finite_number(h) or h<0 or h>.24:return false
    for m in data.materials:
        if not _finite_number(m) or m!=int(m) or m<0 or m>4:return false
    if not data.get("rocks") is Array or data.rocks.size()>80:return false
    var ids: Array=[]
    for path in ["res://assets/aquascape-v5/catalog.json","res://assets/aquascape-decor-v1/catalog.json"]:
        for row in JSON.parse_string(FileAccess.get_file_as_string(path)).assets:
            if not row.get("animated",false):ids.append(row.id)
    for row in data.rocks:
        if not row is Dictionary or not preload("res://scripts/aquarium/editor/PropTransform.gd").valid(row):return false
        if not row is Dictionary or row.get("id") not in ids or not row.get("position") is Array or row.position.size()!=3:return false
        for p in row.position:
            if not _finite_number(p):return false
        if absf(row.position[0])>.61 or absf(row.position[2])>.31 or row.position[1]< -.5 or row.position[1]>.5:return false
        if not _finite_number(row.get("scale")) or row.scale<.04 or row.scale>3 or not _finite_number(row.get("yaw")):return false
    var choice: Variant=data.get("selected_substrate",0)
    return _finite_number(choice) and choice==int(choice) and choice>=0 and choice<=4

func _valid_state(data: Variant,content_ids: Variant=null) -> bool:
    if not data is Dictionary:return false
    var version: Variant=data.get("schema_version")
    if not _finite_number(version) or version!=int(version) or int(version) not in [1,2,3] or not data.get("objects") is Array or data.objects.size()>MAX_OBJECTS:return false
    var cells: Array=Footprint.initial()
    if version>=2:
        if not Footprint.valid(data.get("parcels")):return false
        cells=data.parcels
    if version<3 and data.has("floor_tiles"):return false
    for key in ["floor_style","wall_style"]:
        if not _finite_number(data.get(key)) or data[key]!=int(data[key]) or data[key]<0 or data[key]>2:return false
    var ids: Array=[];var rows: Array=[];var tanks := 0
    for row in data.objects:
        if not row is Dictionary or not row.get("id") is String or row.id.is_empty() or row.id in ids:return false
        if row.get("kind") not in ["tank","bench","plinth","wall","stair"] or not row.get("name") is String or row.name.length()>80:return false
        var level: Variant=row.get("level",0)
        if not _finite_number(level) or level!=int(level) or level<0 or level>Storeys.MAX_LEVEL:return false
        if version<3 and (level!=0 or row.kind=="stair"):return false
        if data.schema_version==1 and row.kind=="wall":return false
        if not row.get("at") is Array or row.at.size()!=2:return false
        for x in row.at:
            if not _finite_number(x):return false
        if not _finite_number(row.get("yaw")) or not _finite_number(row.get("scale")) or row.scale<.4 or row.scale>1.3:return false
        if row.kind=="stair" and (level>=Storeys.MAX_LEVEL or row.scale!=1
            or absf(sin(float(row.yaw)*2))>.0001 or row.at[0]!=roundf(row.at[0]) or row.at[1]!=roundf(row.at[1])):
            return false
        if row.kind=="wall":
            if not _finite_number(row.get("length")) or not row.get("door") is bool or row.scale!=1:return false
            if row.length<(3 if row.door else .5) or row.length>18:return false
            if absf(sin(float(row.yaw)*2))>.0001:return false
        if row.kind=="tank":
            tanks+=1
            if row.has("water") and not WaterProfile.valid(row.water):return false
            if tanks>MAX_TANKS or not _finite_number(row.get("fish_count")) or row.fish_count!=int(row.fish_count) or row.fish_count<0 or row.fish_count>15 or not row.get("content") is Dictionary:return false
            if (content_ids==null or row.id in content_ids) and not _valid_content(row.content):return false
        if not _valid_placement(row,rows,"",cells):return false
        rows.append(row);ids.append(row.id)
    return version<3 or _valid_storeys(data)
