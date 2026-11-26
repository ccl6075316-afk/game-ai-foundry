extends RefCounted
## One validated mutation boundary. No input, rendering, live fish or disk access.
const Footprint=preload("res://scripts/aquarium/HallFootprint.gd")
const Storeys=preload("res://scripts/aquarium/hall/HallStoreys.gd")
var document: RefCounted
var rules: RefCounted
var history: RefCounted

func _init(layout: RefCounted,validation: RefCounted,edits: RefCounted) -> void:
    document=layout;rules=validation;history=edits

func execute(kind: String,payload: Dictionary,remember: bool=true,expected_revision: int=-1) -> Dictionary:
    if expected_revision>=0 and expected_revision!=document.revision:return {"ok":false,"error":"布局已改变，请重新预览。"}
    var before: Dictionary=document.snapshot()
    var next: Dictionary=before.duplicate(true)
    var id: String=payload.get("id","")
    var index := -1
    for i in next.objects.size():
        if next.objects[i].id==id:index=i;break
    var fields: Array=[]
    match kind:
        "add":
            if not payload.get("object") is Dictionary:return {"ok":false,"error":"缺少物件数据。"}
            next.objects.append(payload.object.duplicate(true));id=str(payload.object.get("id",""))
            if payload.object.get("kind")=="stair" or payload.object.get("level",0)!=0:
                next.schema_version=3
                next.floor_tiles=next.get("floor_tiles",[])
        "patch":
            if index<0 or not payload.get("patch") is Dictionary:return {"ok":false,"error":"物件已不存在。"}
            if payload.patch.has("id") or payload.patch.has("kind"):return {"ok":false,"error":"不能修改物件标识和种类。"}
            fields=payload.patch.keys()
            for key in fields:next.objects[index][key]=payload.patch[key]
        "remove":
            if index<0:return {"ok":false,"error":"物件已不存在。"}
            next.objects.remove_at(index)
        "expand":
            var cell: Variant=payload.get("cell")
            if not cell is Array or cell.size()!=2:return {"ok":false,"error":"地块坐标无效。"}
            for coordinate in cell:
                if not Footprint.valid_coordinate(coordinate):return {"ok":false,"error":"地块坐标无效。"}
            if not Footprint.can_add(next.parcels,cell):return {"ok":false,"error":"这里已经铺过地块了。"}
            next.parcels.append(payload.cell.duplicate())
        "style":
            if payload.get("key") not in ["floor_style","wall_style","wall_finish"]:return {"ok":false,"error":"未知表面样式。"}
            next[payload.key]=payload.get("value")
        "exterior":
            if not payload.get("patch") is Dictionary:return {"ok":false,"error":"外墙参数无效。"}
            next.exterior_wall=preload("HallExteriorWall.gd").settings(next)
            next.exterior_wall.merge(payload.patch,true)
        "region":
            var proposal := preload("HallArchitecture.gd").region_proposal(next,payload)
            if not proposal.ok:return proposal
            next=proposal.layout
        "floor":
            var proposal := floor_proposal(next,payload)
            if not proposal.ok:return proposal
            if not proposal.changed:return {"ok":false,"error":"选区里的地板已经是这个状态。"}
            next=proposal.layout
        _:
            return {"ok":false,"error":"未知建造操作。"}
    rules.placement_error=""
    var content_ids: Array=[id] if kind=="add" or "content" in fields else []
    if not document.commit_command(next,rules,payload,content_ids):return {"ok":false,"error":rules.placement_error if not rules.placement_error.is_empty() else "布局或物件参数无效。"}
    if remember:history.remember(before)
    return {"ok":true,"kind":kind,"id":id,"fields":fields}

func floor_proposal(layout: Dictionary,payload: Dictionary) -> Dictionary:
    var start: Variant=payload.get("start")
    var end: Variant=payload.get("end")
    if not Storeys.valid_tile(start) or not Storeys.valid_tile(end) or start[1]!=end[1] or not payload.get("erase") is bool:
        return {"ok":false,"error":"请选择上层地板范围。"}
    var a := Storeys.key(start)
    var b := Storeys.key(end)
    if a.y>Storeys.top_level(layout):
        return {"ok":false,"error":"先放楼梯，再到上一层铺地板。"}
    var lo := a.min(b)
    var hi := a.max(b)
    var region := AABB(Vector3(lo.x,0,lo.z),Vector3(hi.x-lo.x+1,1,hi.z-lo.z+1))
    if not Footprint.contains(layout.parcels,region,0):
        return {"ok":false,"error":"选区超出已扩建地基。"}
    var tiles := Storeys.index(layout.get("floor_tiles",[]))
    var changed := false
    for cell in Storeys.cells_in(region,a.y):
        if payload.erase:
            changed=tiles.erase(cell) or changed
        elif not tiles.has(cell):
            tiles[cell]=true;changed=true
    var candidate := layout.duplicate()
    candidate.schema_version=3
    candidate.floor_tiles=[]
    for cell in tiles:candidate.floor_tiles.append([cell.x,cell.y,cell.z])
    for field in ["floor_finishes","ceilings"]:
        candidate[field]=candidate.get(field,[]).filter(func(row):return row[1]==0 or tiles.has(Storeys.key(row)))
    rules.placement_error=""
    if not rules._valid_storeys(candidate):return {"ok":false,"error":rules.placement_error}
    return {"ok":true,"layout":candidate,"changed":changed}

func remember() -> void:
    history.remember(document.snapshot())

func undo() -> bool:
    var state: Variant=history.undo(document.snapshot())
    return state!=null and document.replace(state,rules)

func redo() -> bool:
    var state: Variant=history.redo(document.snapshot())
    return state!=null and document.replace(state,rules)
