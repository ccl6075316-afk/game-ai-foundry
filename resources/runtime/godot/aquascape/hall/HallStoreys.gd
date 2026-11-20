extends RefCounted
## Shared world-space dimensions for floor cells and stairs.
const Footprint = preload("res://scripts/aquarium/HallFootprint.gd")
const HEIGHT := 3.6
const SLAB := .22
const RUN := 6.0
const WIDTH := 2.0
const RAIL := 1.05
const MAX_LEVEL := 80

static func level(row: Dictionary) -> int:
    return int(row.get("level",0))

static func elevation(index: int) -> float:
    return index*HEIGHT

static func top_level(state: Dictionary) -> int:
    var result := 0
    for row in state.objects:
        result=maxi(result,level(row)+(1 if row.kind=="stair" else 0))
    for tile in state.get("floor_tiles",[]):
        result=maxi(result,int(tile[1]))
    return result

static func valid_tile(tile: Variant) -> bool:
    if not tile is Array or tile.size()!=3:return false
    for n in tile:
        if not Footprint.valid_coordinate(n):return false
    return tile[1]>=1 and tile[1]<=MAX_LEVEL

static func key(tile: Array) -> Vector3i:
    return Vector3i(int(tile[0]),int(tile[1]),int(tile[2]))

static func index(tiles: Array) -> Dictionary:
    var result := {}
    for tile in tiles:result[key(tile)]=true
    return result

static func slab_bounds(cell: Vector3i) -> AABB:
    return AABB(Vector3(cell.x,elevation(cell.y)-SLAB,cell.z),Vector3(1,SLAB,1))

static func cells_in(box: AABB,storey: int) -> Array[Vector3i]:
    var result: Array[Vector3i]=[]
    for z in range(floori(box.position.z+.0001),ceili(box.end.z-.0001)):
        for x in range(floori(box.position.x+.0001),ceili(box.end.x-.0001)):
            result.append(Vector3i(x,storey,z))
    return result

static func stair_bounds() -> AABB:
    return AABB(Vector3(-RUN*.5,0,-WIDTH*.5),Vector3(RUN,HEIGHT+RAIL,WIDTH))

static func stair_landing(upper: bool) -> AABB:
    return AABB(Vector3(RUN*.5 if upper else -RUN*.5-1,HEIGHT if upper else 0,-WIDTH*.5),
        Vector3(1,2.0,WIDTH))
