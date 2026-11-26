extends RefCounted
## Derived perimeter, never persisted as user-placeable objects.
const Footprint=preload("../HallFootprint.gd")
const Architecture=preload("HallArchitecture.gd")
const Joints=preload("HallWallJoints.gd")
const DEFAULT={"profile":"plain","depth":.45,"relief":.75,"size":1.1,"finish":5}

static func settings(layout: Dictionary) -> Dictionary:
    var result := DEFAULT.duplicate()
    result.merge(layout.get("exterior_wall",{}),true)
    return result

static func valid(value: Variant) -> bool:
    if not value is Dictionary:return false
    for key in value:
        if key not in DEFAULT:return false
    var data := DEFAULT.duplicate();data.merge(value,true)
    return data.profile in ["plain","rock"] and Architecture.number(data.depth,.1,1.2) and Architecture.number(data.relief,0,1) and Architecture.number(data.size,.6,2) and Architecture.wall_id(data.finish,false)

static func walls(parcels: Array,options: Dictionary) -> Array:
    if options.get("profile","plain")!="rock":return []
    var out: Array=[]
    for cell in parcels:
        var rect := Footprint.rect(cell)
        for edge in [Vector2i.LEFT,Vector2i.RIGHT,Vector2i.UP,Vector2i.DOWN]:
            if Footprint.has(parcels,[cell[0]+edge.x,cell[1]+edge.y]):continue
            var at := rect.get_center()+Vector2(edge)*rect.size*.5
            out.append({"id":"exterior-%s-%s-%s-%s" % [cell[0],cell[1],edge.x,edge.y],
                "kind":"wall","name":"自动外墙","at":[at.x,at.y],"yaw":PI/2 if edge.x!=0 else 0.0,"scale":1.0,
                "length":rect.size.y if edge.x!=0 else rect.size.x,"height":4.6,"thickness":.2,"door":false,
                "wall_profile":"rock","wall_finish":options.get("finish",5),
                "rock_depth":options.get("depth",.45),"rock_relief":options.get("relief",.75),"rock_size":options.get("size",1.1),
                "rock_seed":posmod(int(at.x*13+at.y*37+edge.x*17),9999),"_cutaway":edge==Vector2i.DOWN})
    var ends := Joints.offsets(out.map(func(data):return Joints.wall(data)))
    for i in out.size():out[i]._wall_ends=ends[i]
    return out
