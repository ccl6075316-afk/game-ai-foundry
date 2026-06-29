extends SceneTree
## Execute playtest plan JSON — headless input + screenshots.
## Usage:
##   godot --headless --path <project> -s <this.gd> \
##     --gf-playtest-plan=/path/plan.json \
##     --gf-screenshot-dir=/path/screenshots \
##     --gf-manifest-out=/path/manifest.json

var _plan: Dictionary = {}
var _screenshot_dir := ""
var _manifest_out := ""
var _steps: Array = []
var _step_index := 0
var _frame_counter := 0
var _wait_target := 0
var _pressing := false
var _press_action := ""
var _press_until_ms := 0
var _screenshots: Dictionary = {}
var _started := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--gf-playtest-plan="):
			_load_plan(arg.trim_prefix("--gf-playtest-plan="))
		elif arg.begins_with("--gf-screenshot-dir="):
			_screenshot_dir = arg.trim_prefix("--gf-screenshot-dir=")
		elif arg.begins_with("--gf-manifest-out="):
			_manifest_out = arg.trim_prefix("--gf-manifest-out=")

	if _plan.is_empty():
		printerr("Missing or invalid --gf-playtest-plan=")
		quit(1)
		return
	if _screenshot_dir.is_empty():
		printerr("Missing --gf-screenshot-dir=")
		quit(1)
		return

	DirAccess.make_dir_recursive_absolute(_screenshot_dir)

	var main_scene: String = str(ProjectSettings.get_setting("application/run/main_scene", ""))
	if main_scene.is_empty():
		printerr("No application/run/main_scene")
		quit(1)
		return

	var err := change_scene_to_file(main_scene)
	if err != OK:
		printerr("change_scene_to_file failed: ", err)
		quit(1)


func _load_plan(path: String) -> void:
	if not FileAccess.file_exists(path):
		printerr("Plan file not found: ", path)
		return
	var text := FileAccess.get_file_as_string(path)
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		printerr("Plan JSON must be an object")
		return
	_plan = parsed
	_steps = _plan.get("steps", [])
	if _steps.is_empty():
		printerr("Plan has no steps")
		_plan = {}


func _idle(_delta: float) -> void:
	if _plan.is_empty():
		return

	if _pressing:
		if Time.get_ticks_msec() >= _press_until_ms:
			Input.action_release(_press_action)
			_pressing = false
		return

	if _wait_target > 0:
		_frame_counter += 1
		if _frame_counter < _wait_target:
			return
		_frame_counter = 0
		_wait_target = 0

	if not _started:
		_started = true

	if _step_index >= _steps.size():
		_finish()
		return

	var step = _steps[_step_index]
	if typeof(step) != TYPE_DICTIONARY:
		printerr("Step ", _step_index, " is not an object")
		quit(1)
		return

	var op: String = str(step.get("op", ""))
	match op:
		"wait_frames":
			_wait_target = max(1, int(step.get("frames", 1)))
			_step_index += 1
		"screenshot":
			_do_screenshot(str(step.get("name", "frame_%d" % _step_index)))
			_step_index += 1
		"press":
			var action := str(step.get("action", ""))
			if action.is_empty():
				printerr("press step missing action")
				quit(1)
				return
			if not InputMap.has_action(action):
				printerr("InputMap missing action: ", action, " (godot-developer must wire brief.controls)")
				quit(2)
				return
			var duration := int(step.get("duration_ms", 250))
			Input.action_press(action)
			_pressing = true
			_press_action = action
			_press_until_ms = Time.get_ticks_msec() + max(1, duration)
			_step_index += 1
		_:
			printerr("Unknown op: ", op)
			quit(1)


func _do_screenshot(name: String) -> void:
	var safe := name.replace("/", "_").replace("\\", "_")
	var path := _screenshot_dir.path_join("%s.png" % safe)
	var viewport := root.get_viewport()
	if viewport == null:
		printerr("No viewport for screenshot")
		quit(1)
		return
	var tex := viewport.get_texture()
	if tex == null:
		printerr("No viewport texture")
		quit(1)
		return
	var img := tex.get_image()
	if img == null or img.is_empty():
		printerr("Empty framebuffer at screenshot ", name)
		quit(1)
		return
	var err := img.save_png(path)
	if err != OK:
		printerr("save_png failed: ", path)
		quit(1)
		return
	_screenshots[name] = path
	print("screenshot:", path)


func _finish() -> void:
	var manifest := {
		"ok": true,
		"playtest_id": _plan.get("playtest_id", ""),
		"screenshots": _screenshots,
		"steps_executed": _step_index,
	}
	var text := JSON.stringify(manifest, "\t")
	print("playtest_manifest:", text)
	if not _manifest_out.is_empty():
		var f := FileAccess.open(_manifest_out, FileAccess.WRITE)
		if f:
			f.store_string(text)
	quit(0)
