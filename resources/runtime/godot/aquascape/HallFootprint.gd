extends RefCounted
## Authored foundation cells, independent of exhibit transforms and camera.
const CELL := Vector2(6,7)
const ORIGIN := Vector2(-9,-7)

static func initial() -> Array:
    return [[0,0],[1,0],[2,0],[0,1],[1,1],[2,1]]

static func key(cell: Array) -> Vector2i:
    return Vector2i(int(cell[0]),int(cell[1]))

static func rect(cell: Array) -> Rect2:
    return Rect2(ORIGIN+Vector2(key(cell))*CELL,CELL)

static func at(point: Vector3) -> Array:
    var p := (Vector2(point.x,point.z)-ORIGIN)/CELL
    return [int(floor(p.x)),int(floor(p.y))]

static func has(cells: Array,cell: Array) -> bool:
    for owned in cells:
        if key(owned)==key(cell):return true
    return false

static func neighbors(cell: Array) -> Array:
    var p := key(cell)
    return [[p.x-1,p.y],[p.x+1,p.y],[p.x,p.y-1],[p.x,p.y+1]]

static func can_add(cells: Array,cell: Array) -> bool:
    return not has(cells,cell)

static func candidates(cells: Array) -> Array:
    var occupied := {}
    var result := {}
    for cell in cells:
        occupied[key(cell)] = true
    for cell in cells:
        for next in neighbors(cell):
            var p := key(next)
            if not occupied.has(p):result[p] = next
    return result.values()

static func valid_coordinate(value: Variant) -> bool:
    # Parcel and slab keys use signed 32-bit Godot grid coordinates.
    return (value is int or value is float) and is_finite(float(value)) and value >= -2147483648 and value <= 2147483647 and value == int(value)

static func valid(cells: Variant) -> bool:
    if not cells is Array or cells.is_empty():return false
    var seen := {}
    for cell in cells:
        if not cell is Array or cell.size()!=2:return false
        if not valid_coordinate(cell[0]) or not valid_coordinate(cell[1]):return false
        var p := key(cell)
        if seen.has(p):return false
        seen[p]=true
    for cell in initial():
        if not seen.has(key(cell)):return false
    return true

static func contains(cells: Array,box: AABB,margin: float=.18) -> bool:
    # Sum coverage rather than accepting the outer rectangle of an L-shaped hall.
    var wanted := Rect2(Vector2(box.position.x-margin,box.position.z-margin),Vector2(box.size.x+2*margin,box.size.z+2*margin))
    var covered := 0.0
    for cell in cells:
        var overlap := wanted.intersection(rect(cell))
        if overlap.has_area():covered+=overlap.get_area()
    return absf(covered-wanted.get_area())<.0005

static func extent(cells: Array) -> Rect2:
    var result := rect(cells[0])
    for cell in cells:result=result.merge(rect(cell))
    return result
