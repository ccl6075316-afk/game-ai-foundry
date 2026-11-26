extends RefCounted
## A floor graph per elevation, joined only by complete, unobstructed stair landings.
const FloorNav=preload("HallVisitorNavigation.gd")
const Storeys=preload("../hall/HallStoreys.gd")
const Rules=preload("../hall/HallLayoutRules.gd")
const Architecture=preload("../hall/HallArchitecture.gd")
const RADIUS=FloorNav.RADIUS
var graph := AStar3D.new()
var cells: Array[Vector3i]=[]
var points := {}
var ids := {}
var layers := {}
var components := {}
var destinations := {}
var viewing_goals := {}
var rebuild_usec := 0
var revision := 0

func rebuild(parcels: Array,rows: Array,tiles: Array=[]) -> void:
    var started := Time.get_ticks_usec();revision+=1
    graph.clear();cells.clear();points.clear();ids.clear();layers.clear();components.clear();destinations.clear();viewing_goals.clear()
    var floors := {0:null}
    for tile in tiles:
        var level := int(tile[1])
        if not floors.has(level):floors[level]={}
        floors[level][Vector2i(tile[0],tile[2])]=true
    var rules := Rules.new()
    for level in floors:
        var obstacles: Array=[]
        var y := Storeys.elevation(level)
        for row in rows:
            var data: Dictionary=row.get("data",row)
            var bounds: AABB=rules._transform(data)*rules._bounds(data)
            if bounds.end.y<=y+.03 or bounds.position.y>=y+1.8:continue
            if data.kind=="stair" and Storeys.level(data)!=level:continue
            var item := data.duplicate(true)
            if data.kind=="wall":item._nav_wall_y=y-bounds.position.y
            if data.kind=="wall" and Architecture.opening(data)=="door":
                var hole := Architecture.aperture(data)
                if y<bounds.position.y+hole.position.y or y+1.8>bounds.position.y+hole.end.y:item.opening="none";item.door=false
            obstacles.append(item)
        var plane := FloorNav.new();plane.rebuild(parcels,obstacles,floors[level]);layers[level]=plane
        for cell in plane.cells:
            var key := Vector3i(cell.x,level,cell.y)
            var point := Vector3(cell.x*FloorNav.CELL,y,cell.y*FloorNav.CELL)
            var id := graph.get_available_point_id();graph.add_point(id,point)
            ids[key]=id;points[key]=point;cells.append(key)
        for cell in plane.cells:
            var key := Vector3i(cell.x,level,cell.y)
            for direction in [Vector3i.RIGHT,Vector3i.BACK]:
                if ids.has(key+direction):graph.connect_points(ids[key],ids[key+direction])
    for row in rows:
        var data: Dictionary=row.get("data",row)
        if data.kind!="stair":continue
        var level := Storeys.level(data)
        if not layers.has(level) or not layers.has(level+1):continue
        var pose: Transform3D=rules._transform(data)
        var lanes: Array=[]
        for side in [-.4,.4]:
            var lower: Vector3=pose*Vector3(-Storeys.RUN*.5-.6,0,side)
            var upper: Vector3=pose*Vector3(Storeys.RUN*.5+.6,Storeys.HEIGHT,side)
            var a := Vector3i(roundi(lower.x/FloorNav.CELL),level,roundi(lower.z/FloorNav.CELL))
            var b := Vector3i(roundi(upper.x/FloorNav.CELL),level+1,roundi(upper.z/FloorNav.CELL))
            if not ids.has(a) or not ids.has(b):continue
            var lane: Array[int]=[ids[a]]
            for i in 31:
                var t := float(i)/30
                var id := graph.get_available_point_id()
                graph.add_point(id,pose*Vector3(lerpf(-Storeys.RUN*.5,Storeys.RUN*.5,t),Storeys.HEIGHT*t,side))
                graph.connect_points(lane[-1],id);lane.append(id)
            graph.connect_points(lane[-1],ids[b]);lane.append(ids[b]);lanes.append(lane)
        if lanes.size()==2:
            for i in range(1,lanes[0].size()-1):graph.connect_points(lanes[0][i],lanes[1][i])
    _components()
    for key: Vector3i in cells:
        var component: int=components[ids[key]]
        if not destinations.has(component):destinations[component]=[]
        destinations[component].append(points[key])
    for row in rows:
        var data: Dictionary=row.get("data",row)
        if data.kind not in ["tank","shell"]:continue
        var box: AABB=rules._transform(data)*rules._bounds(data)
        var level := Storeys.level(data)
        var face := Vector3(box.get_center().x,Storeys.elevation(level),box.get_center().z)
        for edge in 4:
            for i in 3:
                var t := float(i+1)/4
                var p := Vector3(lerpf(box.position.x,box.end.x,t),face.y,box.position.z-.9)
                if edge==1:p.z=box.end.z+.9
                if edge>=2:p=Vector3(box.position.x-.9 if edge==2 else box.end.x+.9,face.y,lerpf(box.position.z,box.end.z,t))
                var key := Vector3i(roundi(p.x/FloorNav.CELL),level,roundi(p.z/FloorNav.CELL))
                if not ids.has(key):continue
                var component: int=components[ids[key]]
                if not viewing_goals.has(component):viewing_goals[component]=[]
                viewing_goals[component].append({"point":points[key],"face":face})
    rebuild_usec=Time.get_ticks_usec()-started

func _components() -> void:
    var component := 0
    for start in graph.get_point_ids():
        if components.has(start):continue
        var queue: Array[int]=[start];components[start]=component;var cursor := 0
        while cursor<queue.size():
            var id: int=queue[cursor];cursor+=1
            for next in graph.get_point_connections(id):
                if not components.has(next):components[next]=component;queue.append(next)
        component+=1

func position_of(cell: Vector3i) -> Vector3:
    return points[cell]

func nearest(point: Vector3) -> int:
    if graph.get_point_count()==0:return -1
    var id := graph.get_closest_point(point)
    return id if graph.get_point_position(id).distance_to(point)<.65 else -1

func route(start: Vector3,finish: Vector3) -> PackedVector3Array:
    var a := nearest(start);var b := nearest(finish)
    if a<0 or b<0 or components[a]!=components[b]:return PackedVector3Array()
    return graph.get_point_path(a,b)

func choose_goal(point: Vector3,rng: RandomNumberGenerator) -> Dictionary:
    var id := nearest(point)
    if id<0:return {}
    var component: int=components[id]
    var targets: Array=viewing_goals.get(component,[])
    if not targets.is_empty():return targets[rng.randi_range(0,targets.size()-1)]
    var available: Array=destinations.get(component,[])
    if available.is_empty():return {}
    var target: Vector3=available[rng.randi_range(0,available.size()-1)]
    return {"point":target,"face":target,"wander":true}

func is_walkable(point: Vector3) -> bool:
    return nearest(point)>=0

func point_clear(point: Vector3,_radius: float=RADIUS) -> bool:
    return is_walkable(point)
