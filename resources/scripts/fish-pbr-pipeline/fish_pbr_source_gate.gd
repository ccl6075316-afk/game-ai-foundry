extends RefCounted
## Read the GLB contract before Godot generates missing tangents or sanitizes names.
static func inspect(document: Dictionary) -> Dictionary:
	var materials: Array = document.get("materials", [])
	var safe_name := false
	if materials.size() == 1:
		var name := str(materials[0].get("name", "")).to_lower()
		safe_name = not name.is_empty() and "eye" not in name and "fin" not in name
	var meshes: Array = document.get("meshes", [])
	var accessors: Array = document.get("accessors", [])
	var tangents := not meshes.is_empty()
	for mesh in meshes:
		var primitives: Array = mesh.get("primitives", [])
		tangents = tangents and not primitives.is_empty()
		for primitive in primitives:
			var attributes: Dictionary = primitive.get("attributes", {})
			var tangent := int(attributes.get("TANGENT", -1))
			var position := int(attributes.get("POSITION", -1))
			if tangent < 0 or tangent >= accessors.size() or position < 0 or position >= accessors.size():
				tangents = false
				continue
			var stream: Dictionary = accessors[tangent]
			tangents = tangents and stream.get("type") == "VEC4" and int(stream.get("count", 0)) > 0 and stream.get("count") == accessors[position].get("count")
	return {"explicit_tangent_stream": tangents, "optics_safe_single_material_name": safe_name}
