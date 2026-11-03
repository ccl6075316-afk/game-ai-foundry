extends "portable/FishAssetViewer.gd"
func _capture_declared() -> void:
    _toggle_gray()
    await super._capture_declared()
