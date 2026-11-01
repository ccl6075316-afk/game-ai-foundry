extends SceneTree
## Save the already-reviewed native clip as an exact engine resource, avoiding
## scene-import animation optimization. No geometry or source animation edit.
func _initialize() -> void:
	var args := OS.get_cmdline_user_args();assert(args.size() == 2)
	var path := "res://assets/models/fish/blacktip_reef_shark.glb"
	assert(FileAccess.get_sha256(path) == "f87b661e0d19fb803d5271284319b45c7c2721498a9ebf1b14cfe2e85f5785fd")
	var document := GLTFDocument.new();var state := GLTFState.new()
	assert(document.append_from_file(path,state) == OK)
	var model := document.generate_scene(state)
	var player := model.find_children("*","AnimationPlayer",true,false)[0] as AnimationPlayer
	var clip := player.get_animation("Swim")
	assert(clip != null and clip.get_track_count() > 0)
	DirAccess.make_dir_recursive_absolute(args[0].get_base_dir())
	if not FileAccess.file_exists(args[0]):assert(ResourceSaver.save(clip,args[0]) == OK)
	var reloaded := ResourceLoader.load(args[0],"Animation",ResourceLoader.CACHE_MODE_IGNORE) as Animation
	assert(reloaded != null and reloaded.get_track_count() == clip.get_track_count())
	var maximum_time_error := 0.0
	var maximum_value_error := 0.0
	for t in clip.get_track_count():
		assert(clip.track_get_path(t) == reloaded.track_get_path(t) and clip.track_get_key_count(t) == reloaded.track_get_key_count(t))
		for k in clip.track_get_key_count(t):
			maximum_time_error = maxf(maximum_time_error,absf(clip.track_get_key_time(t,k)-reloaded.track_get_key_time(t,k)))
			var a: Variant = clip.track_get_key_value(t,k);var b: Variant = reloaded.track_get_key_value(t,k)
			var difference := 0.0
			if a is Vector3: difference = a.distance_to(b)
			elif a is Quaternion: difference = Vector4(a.x-b.x,a.y-b.y,a.z-b.z,a.w-b.w).length()
			else: difference = absf(float(a)-float(b))
			maximum_value_error = maxf(maximum_value_error,difference)
	var passed := maximum_time_error <= 0.000001 and maximum_value_error <= 0.000001
	FileAccess.open(args[1],FileAccess.WRITE).store_string(JSON.stringify({"ok":passed,"kind":"native_clip_engine_resource_parity","source_model_sha256":FileAccess.get_sha256(path),"resource":args[0],"resource_sha256":FileAccess.get_sha256(args[0]),"tracks":clip.get_track_count(),"maximum_key_time_error":maximum_time_error,"maximum_key_value_error":maximum_value_error,"tolerance":0.000001,"geometry_edited":false,"method":"Direct GLTFDocument native clip saved and cache-ignored reload compared within float serialization precision; bypasses scene import animation optimization."},"  ")+"\n")
	model.free();print("NATIVE_SHARK_CLIP_PARITY ",passed," ",maximum_time_error," ",maximum_value_error);quit(0 if passed else 1)
