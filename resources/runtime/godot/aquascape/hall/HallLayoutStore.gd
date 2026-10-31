extends RefCounted
## Disk boundary: validate before touching destination, preserve full precision.
static func write_layout(path: String,state: Dictionary,rules: RefCounted) -> bool:
    if not rules._valid_state(state):return false
    var file := FileAccess.open(path+".tmp",FileAccess.WRITE)
    if file==null:return false
    file.store_string(JSON.stringify(state,"",true,true));file.close()
    return DirAccess.rename_absolute(path+".tmp",path)==OK

static func read_layout(path: String,rules: RefCounted) -> Variant:
    if not FileAccess.file_exists(path):return null
    var state: Variant=JSON.parse_string(FileAccess.get_file_as_string(path))
    return state if rules._valid_state(state) else null
