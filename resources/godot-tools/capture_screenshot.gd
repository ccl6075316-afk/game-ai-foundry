extends SceneTree
## Headless screenshot capture for gamefactory CLI.
## Usage:
##   godot --headless --path <project> -s <this.gd> \
##     --gf-screenshot-out=/path/out.png --gf-wait-frames=8

const DEFAULT_WAIT := 8

var _output_path := ""
var _wait_frames := DEFAULT_WAIT
var _frame_count := 0
var _captured := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--gf-screenshot-out="):
			_output_path = arg.trim_prefix("--gf-screenshot-out=")
		elif arg.begins_with("--gf-wait-frames="):
			_wait_frames = max(1, int(arg.trim_prefix("--gf-wait-frames=")))

	if _output_path.is_empty():
		printerr("Missing --gf-screenshot-out=")
		quit(1)
		return

	var main_scene: String = str(ProjectSettings.get_setting("application/run/main_scene", ""))
	if main_scene.is_empty():
		printerr("No application/run/main_scene in project.godot")
		quit(1)
		return

	var err := change_scene_to_file(main_scene)
	if err != OK:
		printerr("change_scene_to_file failed: ", err)
		quit(1)


func _idle(_delta: float) -> void:
	if _captured:
		return
	_frame_count += 1
	if _frame_count < _wait_frames:
		return
	_captured = true

	var viewport := root.get_viewport()
	if viewport == null:
		printerr("No root viewport")
		quit(1)
		return

	var tex := viewport.get_texture()
	if tex == null:
		printerr("No viewport texture (headless driver issue?)")
		quit(1)
		return

	var img := tex.get_image()
	if img == null or img.is_empty():
		printerr("Empty framebuffer image")
		quit(1)
		return

	var save_err := img.save_png(_output_path)
	if save_err != OK:
		printerr("save_png failed: ", save_err)
		quit(1)
		return

	print("screenshot:", _output_path)
	quit(0)
