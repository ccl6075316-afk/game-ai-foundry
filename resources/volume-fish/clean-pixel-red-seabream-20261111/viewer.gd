extends "../../scripts/volume-fish/portable/FishListViewer.gd"

func run() -> void:
    await super.run()
    if catalog.get("mode", "") == "interactive":
        var screen_index := int(catalog.get("window_screen", DisplayServer.get_primary_screen()))
        root.current_screen = screen_index
        var screen_position := DisplayServer.screen_get_position(screen_index)
        var screen_size := DisplayServer.screen_get_size(screen_index)
        root.position = screen_position + (screen_size - root.size) / 2
        var placement := {"ok":root.current_screen == screen_index,"screen":root.current_screen,"screen_position":[screen_position.x,screen_position.y],"window_position":[root.position.x,root.position.y],"window_size":[root.size.x,root.size.y]}
        FileAccess.open(output_directory.path_join("window-placement.json"),FileAccess.WRITE).store_string(JSON.stringify(placement,"  "))

func _select_fish(index: int) -> void:
    super._select_fish(index)
    if ready_for_input:
        root.title = "真鲷 / 黑鲷 · Godot 已验收成品"
        _apply_camera(config.camera)

func _apply_camera(settings: Dictionary) -> void:
    super._apply_camera(settings)
    tracked_center = bounds.get_center()
