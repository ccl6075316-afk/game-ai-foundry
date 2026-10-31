extends RefCounted
## One validated mutation boundary. No input, rendering, live fish or disk access.
const Footprint=preload("res://scripts/aquarium/HallFootprint.gd")
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
                if not rules._finite_number(coordinate) or coordinate!=int(coordinate):return {"ok":false,"error":"地块坐标无效。"}
            if not Footprint.can_add(next.parcels,cell):return {"ok":false,"error":"只能扩建相邻的空地块；起始 6 块，最多 24 块。"}
            next.parcels.append(payload.cell.duplicate())
        "style":
            if payload.get("key") not in ["floor_style","wall_style"]:return {"ok":false,"error":"未知表面样式。"}
            next[payload.key]=payload.get("value")
        _:
            return {"ok":false,"error":"未知建造操作。"}
    rules.placement_error=""
    var content_ids: Array=[id] if kind=="add" or "content" in fields else []
    if not document.commit_command(next,rules,payload,content_ids):return {"ok":false,"error":rules.placement_error if not rules.placement_error.is_empty() else "布局或物件参数无效。"}
    if remember:history.remember(before)
    return {"ok":true,"kind":kind,"id":id,"fields":fields}

func remember() -> void:
    history.remember(document.snapshot())

func undo() -> bool:
    var state: Variant=history.undo(document.snapshot())
    return state!=null and document.replace(state,rules)

func redo() -> bool:
    var state: Variant=history.redo(document.snapshot())
    return state!=null and document.replace(state,rules)
