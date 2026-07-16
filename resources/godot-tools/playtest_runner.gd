extends SceneTree
## Execute playtest plan JSON — headless input + screenshots + hard asserts.
## Usage:
##   godot --headless --path <project> -s <this.gd> \
##     --gf-playtest-plan=/path/plan.json \
##     --gf-screenshot-dir=/path/screenshots \
##     --gf-manifest-out=/path/manifest.json
##
## Exit codes: 0 ok · 1 error · 2 InputMap missing · 3 assertion failed

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
var _assertions: Array = []
var _started := false


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		args = OS.get_cmdline_args()
	for arg in args:
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


func _process(_delta: float) -> bool:
	if _plan.is_empty():
		return false

	if _pressing:
		if Time.get_ticks_msec() >= _press_until_ms:
			Input.action_release(_press_action)
			_pressing = false
		return false

	if _wait_target > 0:
		_frame_counter += 1
		if _frame_counter < _wait_target:
			return false
		_frame_counter = 0
		_wait_target = 0

	if not _started:
		_started = true

	if _step_index >= _steps.size():
		_finish()
		return false

	var step = _steps[_step_index]
	if typeof(step) != TYPE_DICTIONARY:
		printerr("Step ", _step_index, " is not an object")
		quit(1)
		return true

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
				return true
			if not InputMap.has_action(action):
				printerr("InputMap missing action: ", action, " (godot-developer must wire brief.controls)")
				quit(2)
				return true
			var duration := int(step.get("duration_ms", 250))
			Input.action_press(action)
			_pressing = true
			_press_action = action
			_press_until_ms = Time.get_ticks_msec() + max(1, duration)
			_step_index += 1
		"assert_action":
			_assert_action(step)
			_step_index += 1
		"assert_node":
			_assert_node(step)
			_step_index += 1
		"assert_property":
			_assert_property(step)
			_step_index += 1
		_:
			printerr("Unknown op: ", op)
			quit(1)
			return true
	return false


func _fail_assert(message: String) -> void:
	printerr("ASSERT FAIL: ", message)
	_assertions.append({"ok": false, "message": message})
	quit(3)


func _pass_assert(message: String) -> void:
	_assertions.append({"ok": true, "message": message})
	print("assert_ok:", message)


func _assert_action(step: Dictionary) -> void:
	var action := str(step.get("action", ""))
	if action.is_empty():
		_fail_assert("assert_action missing action")
		return
	if not InputMap.has_action(action):
		_fail_assert("InputMap missing action: %s" % action)
		return
	_pass_assert("action exists: %s" % action)


func _assert_node(step: Dictionary) -> void:
	var path := str(step.get("path", ""))
	if path.is_empty():
		_fail_assert("assert_node missing path")
		return
	var node := root.get_node_or_null(NodePath(path))
	if node == null:
		_fail_assert("node missing: %s" % path)
		return
	_pass_assert("node exists: %s" % path)


func _assert_property(step: Dictionary) -> void:
	var path := str(step.get("path", ""))
	var prop := str(step.get("property", ""))
	if path.is_empty() or prop.is_empty():
		_fail_assert("assert_property requires path and property")
		return
	var node := root.get_node_or_null(NodePath(path))
	if node == null:
		_fail_assert("node missing for property: %s" % path)
		return
	if not (prop in node):
		# C# / dynamic: try get() anyway
		pass
	var actual = node.get(prop)
	if step.has("equals"):
		var expected = step.get("equals")
		if not _values_equal(actual, expected):
			_fail_assert("%s.%s expected equals %s got %s" % [path, prop, str(expected), str(actual)])
			return
		_pass_assert("%s.%s equals %s" % [path, prop, str(expected)])
		return
	if step.has("neq"):
		var unexpected = step.get("neq")
		if _values_equal(actual, unexpected):
			_fail_assert("%s.%s expected neq %s" % [path, prop, str(unexpected)])
			return
		_pass_assert("%s.%s neq %s" % [path, prop, str(unexpected)])
		return
	if step.has("gte"):
		var floor_v = step.get("gte")
		if float(actual) < float(floor_v):
			_fail_assert("%s.%s expected gte %s got %s" % [path, prop, str(floor_v), str(actual)])
			return
		_pass_assert("%s.%s gte %s" % [path, prop, str(floor_v)])
		return
	if step.has("lte"):
		var ceil_v = step.get("lte")
		if float(actual) > float(ceil_v):
			_fail_assert("%s.%s expected lte %s got %s" % [path, prop, str(ceil_v), str(actual)])
			return
		_pass_assert("%s.%s lte %s" % [path, prop, str(ceil_v)])
		return
	_fail_assert("assert_property needs equals|neq|gte|lte")


func _values_equal(a: Variant, b: Variant) -> bool:
	if typeof(a) == TYPE_FLOAT or typeof(b) == TYPE_FLOAT:
		return is_equal_approx(float(a), float(b))
	return str(a) == str(b) or a == b


func _do_screenshot(name: String) -> void:
	# Dummy/headless renderer has no framebuffer — soft-skip (assert_* remain the hard gate).
	if str(DisplayServer.get_name()).to_lower().contains("headless"):
		print("screenshot_skipped:", name, " (headless display)")
		_screenshots[name] = ""
		return
	var safe := name.replace("/", "_").replace("\\", "_")
	var path := _screenshot_dir.path_join("%s.png" % safe)
	var viewport := root.get_viewport()
	if viewport == null:
		print("screenshot_skipped:", name, " (no viewport)")
		_screenshots[name] = ""
		return
	var tex := viewport.get_texture()
	if tex == null:
		print("screenshot_skipped:", name, " (no texture)")
		_screenshots[name] = ""
		return
	var img := tex.get_image()
	if img == null or img.is_empty():
		print("screenshot_skipped:", name, " (empty framebuffer)")
		_screenshots[name] = ""
		return
	var err := img.save_png(path)
	if err != OK:
		print("screenshot_skipped:", name, " (save_png failed)")
		_screenshots[name] = ""
		return
	_screenshots[name] = path
	print("screenshot:", path)


func _finish() -> void:
	var manifest := {
		"ok": true,
		"playtest_id": _plan.get("playtest_id", ""),
		"screenshots": _screenshots,
		"assertions": _assertions,
		"steps_executed": _step_index,
	}
	var text := JSON.stringify(manifest, "\t")
	print("playtest_manifest:", text)
	if not _manifest_out.is_empty():
		var f := FileAccess.open(_manifest_out, FileAccess.WRITE)
		if f:
			f.store_string(text)
	quit(0)
