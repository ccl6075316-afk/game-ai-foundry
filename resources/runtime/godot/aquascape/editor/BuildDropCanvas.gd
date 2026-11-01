extends TextureRect
signal asset_dropped(id: String,at: Vector2)
var build_scope := ""
var accepts_assets := true

func _can_drop_data(_at: Vector2,data: Variant) -> bool:
    return accepts_assets and data is Dictionary and data.get("scope")==build_scope and data.get("build_asset") is String

func _drop_data(at: Vector2,data: Variant) -> void:
    if not _can_drop_data(at,data):return
    data.placed=true;asset_dropped.emit(data.build_asset,at)
