extends RefCounted
const Route=preload("res://scripts/aquarium/passage/PassageRoute.gd")
const History=preload("res://scripts/aquarium/hall/HallEditHistory.gd")
var route: Dictionary=Route.initial()
var history=History.new()
var saved_digest := ""

func commit(candidate: Dictionary,remember:=true) -> String:
    var error := Route.validate(candidate)
    if not error.is_empty():return error
    if remember:history.remember(route)
    route=candidate.duplicate(true)
    return ""

func undo() -> bool:
    var value: Variant=history.undo(route)
    if value==null:return false
    route=value;return true

func redo() -> bool:
    var value: Variant=history.redo(route)
    if value==null:return false
    route=value;return true

func save(path: String) -> bool:
    if not Route.validate(route).is_empty():return false
    var file := FileAccess.open(path+".tmp",FileAccess.WRITE)
    if file==null:return false
    file.store_string(JSON.stringify(route,"",true,true));file.close()
    if DirAccess.rename_absolute(path+".tmp",path)!=OK:return false
    saved_digest=JSON.stringify(route);return true

func load_route(path: String) -> String:
    if not FileAccess.file_exists(path):return "还没有试建存档。"
    var value: Variant=JSON.parse_string(FileAccess.get_file_as_string(path))
    var error := Route.validate(value)
    if not error.is_empty():return error
    commit(value);saved_digest=JSON.stringify(route);return ""
