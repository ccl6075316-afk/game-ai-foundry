extends RefCounted
## Authored foundation cells, independent of exhibit transforms and camera.
const CELL := Vector2(6,7)
const ORIGIN := Vector2(-9,-7)
const MIN_CELL := Vector2i(-2,-2)
const MAX_CELL := Vector2i(4,3)
const LIMIT := 24

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

static func in_range(cell: Array) -> bool:
    var p := key(cell)
    return p.x>=MIN_CELL.x and p.y>=MIN_CELL.y and p.x<=MAX_CELL.x and p.y<=MAX_CELL.y

static func neighbors(cell: Array) -> Array:
    var p := key(cell)
    return [[p.x-1,p.y],[p.x+1,p.y],[p.x,p.y-1],[p.x,p.y+1]]

static func can_add(cells: Array,cell: Array) -> bool:
    if cells.size()>=LIMIT or not in_range(cell) or has(cells,cell):return false
    for near in neighbors(cell):
        if has(cells,near):return true
    return false

static func candidates(cells: Array) -> Array:
    var result: Array=[]
    for cell in cells:
        for next in neighbors(cell):
            if can_add(cells,next) and not has(result,next):result.append(next)
    return result

static func valid(cells: Variant) -> bool:
    if not cells is Array or cells.is_empty() or cells.size()>LIMIT:return false
    var seen: Dictionary={}
    for cell in cells:
        if not cell is Array or cell.size()!=2:return false
        for n in cell:
            if not (n is int or n is float) or not is_finite(float(n)) or n!=int(n) or absf(float(n))>10:return false
        if not in_range(cell) or seen.has(key(cell)):return false
        seen[key(cell)]=true
    # The initial six parcels are never sold or silently relocated.
    for cell in initial():
        if not seen.has(key(cell)):return false
    var reached: Dictionary={key(cells[0]):true}
    var queue: Array=[cells[0]]
    while not queue.is_empty():
        var cell: Array=queue.pop_front()
        for n in neighbors(cell):
            var p := key(n)
            if seen.has(p) and not reached.has(p):reached[p]=true;queue.append(n)
    return reached.size()==cells.size()

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
