extends RefCounted
## Runtime-only photographic underwater lighting wrapper for display fish.
## Supports both legacy single-albedo fish and multi-material PBR fish (Normal/ORM/Eye/Fins).
## Never modifies source .glb meshes or textures on disk.

const SHADER := preload("FishUnderwaterLit.gdshader")

const SHARK_SPECIES := [
	"blacktip_reef_shark",
	"great_hammerhead",
	"scalloped_hammerhead",
	"smooth_hammerhead",
	"whale_shark",
]

const SILVERY_MARINE_SPECIES := [
	"black_seabream",
	"red_seabream",
	"sea_bass",
	"atlantic_salmon",
	"pacific_bluefin_tuna",
	"atlantic_sailfish",
	"largehead_hairtail",
	"silver_arowana",
	"mahi_mahi",
	"yellow_croaker",
]

const SPECIES_OVERRIDES := {
	"blacktip_reef_shark": {"roughness": 0.88, "specular": 0.08, "metallic": 0.0, "sheen": 0.02, "fin_sss": 0.16},
	"black_seabream": {"roughness": 0.64, "specular": 0.20, "metallic": 0.04, "sheen": 0.24, "fin_sss": 0.32},
	"red_seabream": {"roughness": 0.62, "specular": 0.22, "metallic": 0.05, "sheen": 0.28, "fin_sss": 0.38},
}

static func species_profile(species: String) -> Dictionary:
	if SPECIES_OVERRIDES.has(species):
		return SPECIES_OVERRIDES[species]
	if species in SHARK_SPECIES:
		return {"roughness": 0.88, "specular": 0.08, "metallic": 0.0, "sheen": 0.02, "fin_sss": 0.16}
	if species in SILVERY_MARINE_SPECIES:
		return {"roughness": 0.65, "specular": 0.19, "metallic": 0.04, "sheen": 0.22, "fin_sss": 0.30}
	return {"roughness": 0.74, "specular": 0.14, "metallic": 0.02, "sheen": 0.12, "fin_sss": 0.26}

static func wrap_model(model: Node3D, species: String, waterline := 4.38, sand_y := 0.10) -> Array[Dictionary]:
	var opt := species_profile(species)
	var records: Array[Dictionary] = []
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		if mesh.mesh == null:
			continue
		for s in mesh.mesh.get_surface_count():
			var orig: Material = mesh.get_active_material(s)
			if not (orig is BaseMaterial3D):
				continue
			var base_mat := orig as BaseMaterial3D
			var mat_name := base_mat.resource_name.to_lower()
			var lit := ShaderMaterial.new()
			lit.shader = SHADER
			var has_tex := base_mat.albedo_texture != null
			lit.set_shader_parameter("has_albedo_tex", has_tex)
			if has_tex:
				lit.set_shader_parameter("albedo_tex", base_mat.albedo_texture)
			lit.set_shader_parameter("albedo_tint", base_mat.albedo_color)
			lit.set_shader_parameter("use_vertex_color", base_mat.vertex_color_use_as_albedo)

			var is_eye_surf := "eye" in mat_name
			var is_fin_surf := (not is_eye_surf) and (
				"fin" in mat_name
				or base_mat.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
				or base_mat.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA
			)
			lit.set_shader_parameter("is_eye", is_eye_surf)
			lit.set_shader_parameter("is_fin", is_fin_surf)
			lit.set_shader_parameter("alpha_scissor", base_mat.alpha_scissor_threshold if base_mat.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR else 0.42)

			# Bind PBR Normal & ORM maps automatically when present on the imported material
			if base_mat.normal_enabled and base_mat.normal_texture != null:
				lit.set_shader_parameter("has_normal_tex", true)
				lit.set_shader_parameter("normal_tex", base_mat.normal_texture)
				lit.set_shader_parameter("normal_depth", base_mat.normal_scale)
			else:
				lit.set_shader_parameter("has_normal_tex", false)

			var orm_tex: Texture2D = base_mat.roughness_texture if base_mat.roughness_texture != null else base_mat.metallic_texture
			if orm_tex != null:
				lit.set_shader_parameter("has_orm_tex", true)
				lit.set_shader_parameter("orm_tex", orm_tex)
				lit.set_shader_parameter("has_ao_tex", base_mat.ao_enabled and base_mat.ao_texture != null)
			else:
				lit.set_shader_parameter("has_orm_tex", false)
				lit.set_shader_parameter("has_ao_tex", false)

			lit.set_shader_parameter("wet_roughness", opt.roughness)
			lit.set_shader_parameter("wet_specular", opt.specular)
			lit.set_shader_parameter("scale_metallic", opt.metallic)
			lit.set_shader_parameter("scale_sheen", opt.sheen)
			lit.set_shader_parameter("fin_translucency", opt.fin_sss)
			lit.set_shader_parameter("waterline", waterline)
			lit.set_shader_parameter("sand_y", sand_y)
			records.append({"mesh": mesh, "surface": s, "orig": orig, "lit": lit})
	return records

static func apply_records(records: Array[Dictionary], enabled: bool, params: Dictionary = {}) -> void:
	for rec in records:
		var mesh: MeshInstance3D = rec.mesh
		if not is_instance_valid(mesh):
			continue
		if enabled:
			var lit: ShaderMaterial = rec.lit
			for key in params:
				lit.set_shader_parameter(key, params[key])
			mesh.set_surface_override_material(rec.surface, lit)
		else:
			mesh.set_surface_override_material(rec.surface, rec.orig)

static func set_clock(records: Array[Dictionary], clock: float) -> void:
	for rec in records:
		if is_instance_valid(rec.mesh):
			(rec.lit as ShaderMaterial).set_shader_parameter("clock", clock)
