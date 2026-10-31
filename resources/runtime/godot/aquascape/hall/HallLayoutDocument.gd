extends RefCounted
## Authoritative layout values only: never stores Node, UI or filesystem objects.
const Footprint=preload("res://scripts/aquarium/HallFootprint.gd")
const WaterProfile=preload("res://scripts/aquarium/TankWaterProfile.gd")
var _data: Dictionary={"schema_version":2,"parcels":Footprint.initial(),"floor_style":0,"wall_style":0,"objects":[]}
var revision := 0

func snapshot() -> Dictionary:
    return _data.duplicate(true)

func object_data(id: String) -> Dictionary:
    for row in _data.objects:
        if row.id==id:return row.duplicate(true)
    return {}

func replace(state: Variant,rules: RefCounted) -> bool:
    # Validate the original version before normalizing, so v1 cannot smuggle walls.
    if not _value_tree(state) or not rules._valid_state(state):return false
    _install(state)
    return true

func commit_command(state: Dictionary,rules: RefCounted,payload: Dictionary,content_ids: Array) -> bool:
    # Dispatcher assembled this candidate from our isolated snapshot + payload.
    # Unchanged content has already passed full validation. Do not rescan every
    # sand sample on each mouse-move; load/undo/replace still validate all data.
    if not _value_tree(payload) or not rules._valid_state(state,content_ids):return false
    _install(state)
    return true

func _install(state: Dictionary) -> void:
    var normalized: Dictionary=state.duplicate(true)
    normalized.schema_version=2
    normalized.parcels=normalized.get("parcels",Footprint.initial())
    for row in normalized.objects:
        if row.kind=="tank":row.water=WaterProfile.normalized(row.get("water",{}))
    _data=normalized;revision+=1

func materialize_initial_content(contents: Dictionary,rules: RefCounted) -> void:
    # The procedural default is resolved once after creation, not on each save.
    for row in _data.objects:
        if row.kind=="tank" and row.content.is_empty() and contents.has(row.id):
            if _value_tree(contents[row.id]) and rules._valid_content(contents[row.id]):
                row.content=contents[row.id].duplicate(true);revision+=1

func _value_tree(value: Variant) -> bool:
    if value is Dictionary:
        for key in value:
            if not (key is String or key is StringName) or not _value_tree(value[key]):return false
        return true
    if value is Array:
        for item in value:
            if not _value_tree(item):return false
        return true
    return value==null or value is String or value is bool or value is int or (value is float and is_finite(value))

func parcels() -> Array:
    return _data.parcels.duplicate(true)

func style(key: String) -> int:
    return int(_data[key])

func set_style_for_legacy_review(key: String,value: int) -> void:
    # Compatibility for old review scripts; production UI uses commands.
    assert(key in ["floor_style","wall_style"] and value>=0 and value<=2)
    _data[key]=value;revision+=1
