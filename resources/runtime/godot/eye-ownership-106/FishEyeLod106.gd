extends RefCounted
## Explicit candidate exception: retire one frozen bad LOD, never approve it.
const CONFIG = "res://assets/models/fish/motion/eye-ownership-106.json"
var last_error: String = ""
var last_receipt: Dictionary = {}
func fail(message: String) -> int:
    last_error = message
    push_error("FishEyeLod106: " + message)
    return 0
func sha(value: Variant) -> String:
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    context.update(value if value is PackedByteArray else var_to_bytes(value))
    return context.finish().hex_encode()
func attributes(mesh: ArrayMesh) -> Dictionary:
    var meta: Dictionary = {}
    for key in mesh.get_meta_list(): meta[str(key)] = mesh.get_meta(key)
    return {"resource_name":mesh.resource_name, "resource_local_to_scene":mesh.resource_local_to_scene,
        "resource_scene_unique_id":mesh.resource_scene_unique_id, "lightmap_size_hint":mesh.lightmap_size_hint,
        "blend_shape_mode":mesh.blend_shape_mode, "blend_shape_count":mesh.get_blend_shape_count(),
        "custom_aabb":mesh.custom_aabb, "aabb":mesh.get_aabb(), "shadow_mesh_id":mesh.shadow_mesh.get_instance_id() if mesh.shadow_mesh != null else 0,
        "metadata_sha256":sha(meta)}
func apply(model: Node3D, species: String, path: String = CONFIG) -> int:
    last_error = ""
    last_receipt = {}
    var config = JSON.parse_string(FileAccess.get_file_as_string(path))
    if not config is Dictionary or not config.get("profiles") is Dictionary: return fail("Invalid profile")
    if not config.profiles.has(species): return 0
    var p: Dictionary = config.profiles[species]
    if model == null or model.scene_file_path != p.model_path or FileAccess.get_sha256(p.model_path) != p.model_sha256: return fail("Model mismatch")
    if model.has_meta("eye_lod_106_receipt"): return fail("LOD exception already installed")
    var mesh := model.find_child("Closed_body", true, false) as MeshInstance3D
    if mesh == null or not mesh.mesh is ArrayMesh: return fail("Expected Closed_body ArrayMesh")
    var original := mesh.mesh as ArrayMesh
    if original.get_script() != null or original.get_blend_shape_count() != 0: return fail("Scripted mesh/blend shapes are unsupported")
    var known := ["resource_local_to_scene","resource_name","lightmap_size_hint","_blend_shape_names","_surfaces","blend_shape_mode","custom_aabb","shadow_mesh","script"]
    for property in original.get_property_list():
        if int(property.usage) & PROPERTY_USAGE_STORAGE and property.name not in known: return fail("Unknown stored mesh property: " + str(property.name))
    var before: Array = original.get("_surfaces")
    if before.size() != 2: return fail("Expected exactly two frozen body surfaces")
    var keys := ["format","primitive","vertex_data","vertex_count","skin_data","attribute_data","aabb","uv_scale","index_data","index_count","lods","bone_aabbs","material","name"]
    for surface in before:
        for key in surface:
            if key not in keys: return fail("Unknown serialized surface field: " + str(key))
    var expected := before.duplicate(true)
    var raw_lods: Array = expected[0].get("lods", [])
    var retirement: Dictionary = p.get("retired_lod", {})
    if raw_lods.size() != 12 or retirement.get("triangles", 0) != 402 or retirement.get("index", -1) != 5: return fail("Unexpected LOD inventory")
    var retired_bytes: PackedByteArray = raw_lods[11]
    if abs(float(raw_lods[10])-float(retirement.get("edge_length",-1.))) > 1e-12 or sha(retired_bytes) != retirement.get("index_data_sha256") or retired_bytes.size() != 2412:
        return fail("Bad LOD does not match frozen retirement evidence")
    raw_lods.resize(10)
    expected[0].lods = raw_lods
    var before_attributes := attributes(original)
    var before_arrays: Array = []
    for index in original.get_surface_count(): before_arrays.append(sha(original.surface_get_arrays(index)))
    # Preserve packed serialized vertex/normal/UV/skin/index bytes directly.
    # Decoding and re-encoding arrays could silently change quantized normals.
    var copy := original.duplicate(false) as ArrayMesh
    copy.resource_scene_unique_id = original.resource_scene_unique_id
    copy.clear_surfaces()
    copy.set("_surfaces", expected)
    if copy.get("_surfaces") != expected or attributes(copy) != before_attributes: return fail("Raw surface/resource attribute preservation failed")
    var after_arrays: Array = []
    for index in copy.get_surface_count(): after_arrays.append(sha(copy.surface_get_arrays(index)))
    if before_arrays != after_arrays: return fail("Decoded surface arrays changed")
    var skin := mesh.skin
    var skeleton_path := mesh.skeleton
    mesh.mesh = copy
    if mesh.skin != skin or mesh.skeleton != skeleton_path:
        mesh.mesh = original
        return fail("Skin/skeleton binding changed")
    last_receipt = {"species":species,"model_sha256":p.model_sha256,"config_sha256":FileAccess.get_sha256(path),
        "helper_sha256":FileAccess.get_sha256(get_script().resource_path),"exception":"Retire Closed_body surface0 nativeLOD5 only; old LOD5 is rejected, not passed",
        "retired_lod":retirement,"body_surface0_lods_before":6,"body_surface0_lods_after":5,"surface1_lods_preserved":true,
        "original_raw_surfaces_sha256":sha(before),"expected_after_raw_surfaces_sha256":sha(expected),"actual_after_raw_surfaces_sha256":sha(copy.get("_surfaces")),
        "all_decoded_surface_arrays_before":before_arrays,"all_decoded_surface_arrays_after":after_arrays,
        "resource_attributes_before":str(before_attributes),"resource_attributes_after":str(attributes(copy)),
        "source_resource_path":original.resource_path,"runtime_copy_resource_path":copy.resource_path,"new_runtime_resource_identity":true,
        "skin_same_object":true,"skeleton_path_unchanged":true,"original_resource_raw_unchanged":sha(original.get("_surfaces"))==sha(before),"fin_objects_touched":false}
    model.set_meta("eye_lod_106_receipt",last_receipt)
    return 1
