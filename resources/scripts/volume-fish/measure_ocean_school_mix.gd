extends SceneTree
## Same seeded exhibit, no feed or close camera. Neighbour IDs are invariant to
## rigid rotation and translation of a complete shoal.
func _initialize() -> void:
    run.call_deferred()

func nearest_four(points:PackedVector3Array,member:int) -> Array:
    var nearest:=[[INF,-1],[INF,-1],[INF,-1],[INF,-1]]
    for j in points.size():
        if j==member: continue
        var d:=points[member].distance_squared_to(points[j])
        for k in 4:
            if d<nearest[k][0]:
                nearest.insert(k,[d,j])
                nearest.pop_back()
                break
    return nearest.map(func(p):return p[1])

func run() -> void:
    var tank=load("res://scenes/ocean_school_review.tscn").instantiate()
    root.add_child(tank)
    tank.set_process(false)
    var initial:Dictionary={}
    for tick in 1801:
        if tick>0: tank._move_animals(1./60.)
        if tick not in [0,600,1800]: continue
        var retained:=0
        var total:=0
        for g in range(0,tank.schools.size(),5):
            var s:Dictionary=tank.schools[g]
            var points:=PackedVector3Array()
            for i in s.slots.size():
                points.append(tank.member_center(s,i,s.node.multimesh.get_instance_transform(i)))
            for j in 6:
                var i:=int((j+.5)*points.size()/6.)
                var id:int=s.first_id+i
                var neighbours:=nearest_four(points,i)
                if tick==0: initial[id]=neighbours
                for other in neighbours:
                    retained+=int(other in initial[id])
                    total+=1
        print("OCEAN_MIX seconds=",tick/60," fish=",initial.size()," new_neighbours=",total-retained," of ",total)
    quit()
