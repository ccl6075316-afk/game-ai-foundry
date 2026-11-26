extends RefCounted
## Additive layout fields: old saves keep their original sizes and finishes.
const Storeys = preload("HallStoreys.gd")
const Footprint = preload("../HallFootprint.gd")
const REGION_TOOLS = ["finish", "finish_erase", "ceiling", "ceiling_erase"]
const FINISH_NAMES = ["原有瓷砖", "错缝板岩", "木质地板", "浅色水磨石", "米色石灰岩", "蓝绿马赛克", "深色防滑地砖"]
# Stable saved IDs: append new entries; never reorder the original three.
const FINISH_TEXTURES = ["res://assets/aquarium-hall-style-v3/hall_floor.png", "",
    "res://assets/aquarium-hall-style-v3/hall_wood.png",
    "res://assets/hall-materials-v1/terrazzo.png", "res://assets/hall-materials-v1/limestone.png",
    "res://assets/hall-materials-v1/mosaic.png", "res://assets/hall-materials-v1/rubber.png"]
const FINISH_REPEAT_METRES = [2.0,2.0,2.0,1.0,2.0,.8,.5]
const WALL_NAMES = ["原有墙面", "灰白抹灰", "青蓝长条砖", "暖木饰面", "砂色砌石", "自然灰岩"]
const WALL_TEXTURES = ["res://assets/aquarium-hall-style-v3/hall_wall.png",
    "res://assets/hall-materials-v1/plaster.png", "res://assets/hall-materials-v1/ceramic.png",
    "res://assets/hall-materials-v1/wood_panel.png", "res://assets/hall-materials-v1/sandstone_wall.png", "res://assets/hall-materials-v1/rock_wall.png"]
const WALL_REPEATS = [Vector2(2,2),Vector2(2,2),Vector2(1.6,.8),Vector2(1.2,2.4),Vector2(2,1.2),Vector2(2.5,2.5)]
const WALL_PROFILES = ["plain", "wainscot", "pilaster", "recessed", "rock"]
const WALL_PROFILE_NAMES = ["素墙", "墙裙与压顶", "凸出壁柱", "凹面框格", "立体岩壁"]

static func wall_depth(data: Dictionary) -> float:
    if data.get("wall_profile", "plain")=="rock":return float(data.get("thickness",.18))+2*float(data.get("rock_depth",.65))
    return float(data.get("thickness",.18))+{"plain":.04,"wainscot":.16,"pilaster":.32,"recessed":.14}.get(data.get("wall_profile","plain"),.04)

static func wall_core_depth(data: Dictionary) -> float:
    var depth := float(data.get("thickness",.18))
    return maxf(.08,depth-.1) if data.get("wall_profile","plain")=="recessed" else depth

static func wall_id(value: Variant,inherit: bool=true) -> bool:
    return number(value,-1 if inherit else 0,WALL_NAMES.size()-1) and value==int(value)

static func height(data: Dictionary) -> float:
    return float(data.get("height",3.2))

static func opening(data: Dictionary) -> String:
    return str(data.get("opening","door" if data.get("door",false) else "none"))

static func aperture(data: Dictionary) -> Rect2:
    var width := float(data.get("opening_width",1.2))
    return Rect2(float(data.get("opening_offset",0.0))-width*.5,
        float(data.get("sill",1.0)) if opening(data)=="window" else 0.0,
        width,float(data.get("opening_height",2.2)))

static func number(value: Variant,lo: float,hi: float) -> bool:
    return (value is float or value is int) and is_finite(value) and value>=lo and value<=hi

static func valid_object(data: Dictionary) -> bool:
    if data.kind not in ["wall","column"]:return true
    if not number(data.get("height",3.2),.8 if data.kind=="wall" else 2.4,20):return false
    if data.kind=="column":
        return number(data.get("width",.6),.3,2) and data.get("round",false) is bool
    if not number(data.get("thickness",.18),.12,1.2) or data.get("wall_profile","plain") not in WALL_PROFILES:return false
    if not number(data.get("rock_depth",.65),.1,1.2) or not number(data.get("rock_relief",.75),0,1) or not number(data.get("rock_size",1.1),.6,2):return false
    if not number(data.get("rock_seed",7),0,9999) or data.get("rock_seed",7)!=int(data.get("rock_seed",7)):return false
    if not wall_id(data.get("wall_finish",-1)) or not wall_id(data.get("trim_finish",-1)):return false
    if opening(data) not in ["none","door","window"]:return false
    if not number(data.get("opening_width",1.2),.8,12) or not number(data.get("opening_height",2.2),.6,15):return false
    if not number(data.get("opening_offset",0),-9,9) or not number(data.get("sill",1.0),.3,5):return false
    if opening(data)=="none":return true
    var hole := aperture(data)
    return hole.position.x>=-float(data.length)*.5+.15 and hole.end.x<=float(data.length)*.5-.15 and hole.end.y<=height(data)-.15 and (opening(data)!="door" or hole.size.y>=2.0)

static func supported(layout: Dictionary,cell: Vector3i,tiles: Dictionary) -> bool:
    return Footprint.contains(layout.get("parcels",Footprint.initial()),Storeys.slab_bounds(cell),0) and (cell.y==0 or tiles.has(cell))

static func valid_regions(layout: Dictionary,rules: RefCounted) -> bool:
    var tiles := Storeys.index(layout.get("floor_tiles",[]))
    for field in ["floor_finishes","ceilings"]:
        var rows: Variant=layout.get(field,[])
        if not rows is Array or rows.size()>layout.get("parcels",Footprint.initial()).size()*42*(Storeys.MAX_LEVEL+1):return false
        var seen := {}
        for row in rows:
            if not row is Array or row.size()!=4:return false
            for i in 3:
                if not Footprint.valid_coordinate(row[i]):return false
            var cell := Storeys.key(row)
            if cell.y<0 or cell.y>Storeys.MAX_LEVEL or seen.has(cell) or not supported(layout,cell,tiles):return false
            seen[cell]=true
            if field=="floor_finishes":
                if not number(row[3],0,FINISH_NAMES.size()-1) or row[3]!=int(row[3]):return false
            else:
                if not number(row[3],2.4,20):return false
                var slab := AABB(Vector3(cell.x,Storeys.elevation(cell.y)+float(row[3]),cell.z),Vector3(1,.16,1))
                for object in layout.objects:
                    var box: AABB=rules._transform(object)*rules._bounds(object)
                    if slab.intersection(box).get_volume()>.00001:
                        rules.placement_error="天花板会穿过物件，请提高天花或取消该区域覆盖。";return false
                for upper in range(cell.y+1,Storeys.MAX_LEVEL+1):
                    if Storeys.elevation(upper)>slab.end.y:break
                    if tiles.has(Vector3i(cell.x,upper,cell.z)):
                        rules.placement_error="这里已有上层楼板作为天花，请取消额外覆盖。";return false
    return true

static func region_proposal(layout: Dictionary,payload: Dictionary) -> Dictionary:
    var tool: String=payload.get("tool","")
    if tool not in REGION_TOOLS:return {"ok":false,"error":"未知区域工具。"}
    for key in ["start","end"]:
        var row: Variant=payload.get(key)
        if not row is Array or row.size()!=3:return {"ok":false,"error":"区域坐标无效。"}
        for n in row:
            if not Footprint.valid_coordinate(n):return {"ok":false,"error":"区域坐标无效。"}
    var a := Storeys.key(payload.start);var b := Storeys.key(payload.end)
    if a.y!=b.y or a.y<0 or a.y>Storeys.MAX_LEVEL:return {"ok":false,"error":"请选择同一楼层。"}
    var lo := a.min(b);var hi := a.max(b)
    var area_limit: int=layout.parcels.size()*42
    if hi.x-lo.x+1>area_limit or hi.z-lo.z+1>area_limit or (hi.x-lo.x+1)*(hi.z-lo.z+1)>area_limit:return {"ok":false,"error":"选区超出场馆。"}
    var field := "ceilings" if tool.begins_with("ceiling") else "floor_finishes"
    var value: Variant=payload.get("value",0)
    var indexed := {}
    for row in layout.get(field,[]):indexed[Storeys.key(row)]=row
    var tiles := Storeys.index(layout.get("floor_tiles",[]))
    for z in range(lo.z,hi.z+1):
        for x in range(lo.x,hi.x+1):
            var cell := Vector3i(x,a.y,z)
            if not supported(layout,cell,tiles):return {"ok":false,"error":"只能在已有地面或楼板上设置区域。"}
            if tool.ends_with("erase"):indexed.erase(cell)
            else:indexed[cell]=[x,a.y,z,value]
    var result := layout.duplicate(true)
    result[field]=indexed.values()
    return {"ok":true,"layout":result}
