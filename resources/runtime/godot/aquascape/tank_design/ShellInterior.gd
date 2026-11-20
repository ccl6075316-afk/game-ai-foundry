extends RefCounted
## Interior positions are fractions of the footprint bounds, independent of the hall transform.
const Design = preload("ShellDesign.gd")
const Fish = preload("../FishDisplayCatalog.gd")
const GRID := 24
static var decor: Dictionary = {}
static var lengths: Dictionary = {}

static func assets() -> Dictionary:
    if decor.is_empty():
        for item in JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-v5/catalog.json")).assets:
            decor[item.id] = item
    return decor

static func length_m(id: String) -> float:
    if lengths.is_empty():
        var profiles: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
        for key in profiles:
            lengths[key] = profiles[key].real_length_cm * .01
    return lengths.get(id, 0.0)

static func valid(bed: Dictionary) -> bool:
    var heights = bed.get("heights", [])
    if not heights is Array or (heights.size() != 0 and heights.size() != (GRID+1)*(GRID+1)):return false
    for h in heights:
        if not Design.number(h) or absf(h)>1:return false
    var intensity = bed.get("brightness",1.0)
    if not Design.number(intensity) or intensity<0 or intensity>3 or bed.get("tint","neutral") not in ["neutral","warm","cool"]:return false
    for key in ["props","fish"]:
        var list = bed.get(key,[])
        if not list is Array:return false
        for item in list:
            if not item is Dictionary or not item.get("id") is String:return false
            if key=="props" and not assets().has(item.id):return false
            if key=="fish" and (item.id not in Fish.SPECIES or not item.get("stock","") is String):return false
            for axis in ["u","v"]:
                if not Design.number(item.get(axis)) or item[axis]<0 or item[axis]>1:return false
    return true

static func bounds(design: Dictionary) -> Rect2:
    var b := Design.bounds(design)
    return Rect2(b.position.x,b.position.z,b.size.x,b.size.z)

static func clearance(p: Vector2,path: PackedVector2Array) -> float:
    if not Geometry2D.is_point_in_polygon(p,path):return 0
    var result := INF
    for i in path.size():
        result=minf(result,p.distance_to(Geometry2D.get_closest_point_to_segment(p,path[i],path[(i+1)%path.size()])))
    return result

static func waterline(height: float) -> float:
    return height-minf(.09,height*.05)

static func floor_y(uv: Vector2, bed: Dictionary, height: float) -> float:
    var base := float(bed.depth_cm)*.01
    var heights: Array=bed.get("heights",[])
    if heights.is_empty():return base
    var grid := uv.clamp(Vector2.ZERO,Vector2.ONE)*GRID
    var x := mini(floori(grid.x),GRID-1)
    var z := mini(floori(grid.y),GRID-1)
    var i := z*(GRID+1)+x
    var lower := lerpf(heights[i],heights[i+1],grid.x-x)
    var upper := lerpf(heights[i+GRID+1],heights[i+GRID+2],grid.x-x)
    return clampf(base+lerpf(lower,upper,grid.y-z)*waterline(height),.005,waterline(height)*.76)

static func sculpt(bed: Dictionary, uv: Vector2, extent: Vector2, raise: bool, radius: float, height: float) -> void:
    var heights: Array = bed.get("heights",[]).duplicate()
    if heights.is_empty():
        heights.resize((GRID+1)*(GRID+1))
        heights.fill(0.0)
    for z in GRID+1:
        for x in GRID+1:
            var distance := ((Vector2(x,z)/GRID-uv)*extent).length()
            if distance>=radius:continue
            var i:=z*(GRID+1)+x
            var strength := .05*(1-smoothstep(0,radius,distance))/waterline(height)
            var base := float(bed.depth_cm)*.01
            heights[i]=clampf(heights[i]+(strength if raise else -strength),(.005-base)/waterline(height),.76-base/waterline(height))
    bed.heights=heights

static func swim_clearance(species: String) -> float:
    return maxf(.01,length_m(species)*.78)

static func swim_position(design: Dictionary,bed: Dictionary,species: String) -> Variant:
    if not fish_depth_ok(design,bed,{"id":species}):return null
    var path:=Design.contour(design)
    var box:=bounds(design)
    var required:=swim_clearance(species)
    var positions:=PackedVector2Array()
    for fish in bed.get("fish",[]):
        positions.append(box.position+box.size*Vector2(fish.u,fish.v))
    var candidates:=PackedVector2Array([box.get_center()])
    for y in range(1,12):
        for x in range(1,12):
            candidates.append(box.position+box.size*Vector2(x,y)/12)
    # Narrow pockets in a concave outline can fall between the grid points.
    for pocket in Geometry2D.offset_polygon(path,-required):
        var triangles:=Geometry2D.triangulate_polygon(pocket)
        for i in range(0,triangles.size(),3):
            candidates.append((pocket[triangles[i]]+pocket[triangles[i+1]]+pocket[triangles[i+2]])/3)
    var highest:=-INF
    var best:Variant=null
    for point in candidates:
        var gap:=clearance(point,path)
        if gap<required:continue
        var score:=gap
        for other in positions:score=minf(score,point.distance_to(other))
        if score>highest:
            highest=score
            best=(point-box.position)/box.size
    return best

static func fits(design: Dictionary, bed: Dictionary) -> bool:
    var path:=Design.contour(design)
    var box:=bounds(design)
    for key in ["fish","props"]:
        for item in bed.get(key,[]):
            var gap:=clearance(box.position+box.size*Vector2(item.u,item.v),path)
            if gap<.01:return false
            if key=="fish" and (gap<swim_clearance(item.id) or not fish_depth_ok(design,bed,item)):return false
    return true

static func fish_depth_ok(design: Dictionary,bed: Dictionary,item: Dictionary) -> bool:
    var max_floor:=float(bed.depth_cm)*.01
    for h in bed.get("heights",[]):max_floor=maxf(max_floor,float(bed.depth_cm)*.01+h*waterline(design.height))
    return waterline(design.height)-max_floor>=length_m(item.id)*.58
