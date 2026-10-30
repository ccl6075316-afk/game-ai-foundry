extends SceneTree
## Offline extraction of actual frozen shader texture donors, not a game repair.
func _initialize() -> void: call_deferred("run")
func run() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() >= 3)
	var path: String = args[0]; var out: String = args[1]
	assert(not DirAccess.dir_exists_absolute(out))
	assert(DirAccess.make_dir_recursive_absolute(out) == OK)
	var material := ResourceLoader.load(path, "ShaderMaterial", ResourceLoader.CACHE_MODE_IGNORE) as ShaderMaterial
	assert(material != null)
	var records := {}
	for key in args.slice(2):
		var texture := material.get_shader_parameter(key) as Texture2D
		assert(texture != null, "Missing explicit donor: "+key)
		var image := texture.get_image()
		assert(image != null)
		if image.is_compressed(): assert(image.decompress() == OK)
		if image.has_mipmaps(): image.clear_mipmaps()
		image.convert(Image.FORMAT_RGBA8)
		var target := out.path_join(key+".png")
		assert(image.save_png(target) == OK)
		var hash := HashingContext.new(); hash.start(HashingContext.HASH_SHA256); hash.update(image.get_data())
		records[key] = {"path":target,"sha256":FileAccess.get_sha256(target),"RGBA_sha256":hash.finish().hex_encode(),"size":[image.get_width(),image.get_height()],"source_resource":texture.resource_path}
	var report := {"ok":true,"kind":"actual_frozen_material_inputs","material":path,"material_sha256":FileAccess.get_sha256(path),"textures":records,"scope":"Exact existing base-level RGBA extraction. Source material/texture unmodified; no donor or visual approval."}
	FileAccess.open(out.path_join("material-inputs.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("MATERIAL_INPUTS_EXTRACTED ",records.size())
	quit()
