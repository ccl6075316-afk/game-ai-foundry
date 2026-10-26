extends "audit_runtime_performance.gd"
## Read-only current final factory audit. Inherits the tested geometry counters.
const SELECTED := ["zander", "black_seabream", "bluegill", "atlantic_sailfish", "pacific_bluefin_tuna"]
var binder
var before: Dictionary = {}
var records: Array = []
var failures: Array = []
var excluded_paths: Array = []

func current_bindings() -> Dictionary:
    # Enumerate the same actual-runtime scope, filtering whale-only paths BEFORE
    # hashing. Shared JSON/shader files remain bound even if they also name whales.
    var paths: Array[String] = []
    binder._files("res://assets/models/fish", paths)
    binder._files("res://scripts/aquarium", paths)
    paths.append("res://project.godot"); paths.append("res://scenes/fish_school_review.tscn")
    paths.sort()
    var result := {}
    for path in paths:
        if "whaleshark" in path.to_lower().replace("-", "").replace("_", ""):
            if not excluded_paths.has(path): excluded_paths.append(path)
            continue
        result[path] = FileAccess.get_sha256(path)
    return result

func repeated_index_count(indices: PackedInt32Array) -> int:
    var repeated := 0
    for start in range(0, indices.size() - 2, 3):
        var a := indices[start]; var b := indices[start + 1]; var c := indices[start + 2]
        if a == b or a == c or b == c: repeated += 1
    return repeated

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="): output = arg.trim_prefix("--output=")
    var expected := ProjectSettings.globalize_path("res://../plans/reviews/fish-geometry-redundancy-v4").simplify_path()
    if not output.is_absolute_path() or output != expected:
        push_error("Use exact absolute fish-geometry-redundancy-v4 review root"); quit(2); return
    var directory := DirAccess.open("/")
    var cursor := "/"
    for part in output.split("/", false):
        cursor = cursor.path_join(part)
        if directory.is_link(cursor): push_error("Symlink output ancestor rejected"); quit(2); return
    if DirAccess.make_dir_recursive_absolute(output) != OK: quit(2); return
    call_deferred("run")

func run() -> void:
    binder = load("res://scripts/aquarium/fish_school/FishSchoolReview.gd").new()
    before = current_bindings()
    bind_file(get_script().resource_path)
    bind_file(get_script().resource_path.get_base_dir().path_join("audit_runtime_performance.gd"))
    var fixture_ok := self_test()
    fixture_ok = fixture_ok and repeated_index_count(PackedInt32Array([0, 1, 2, 0, 0, 1, 0, 1, 1])) == 2 and repeated_index_count(PackedInt32Array()) == 0
    if not fixture_ok: failures.append({"code": "counter_self_test_failed"})
    holder = Node3D.new(); root.add_child(holder)
    factory = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    for species in SELECTED:
        var count_before: int = factory.fish.size()
        var profile: Dictionary = factory.profiles[species]
        factory._add_fish(holder, species, float(profile.real_length_cm) / 100.0, profile)
        if factory.fish.size() != count_before + 1:
            failures.append({"code": "factory_append_failed", "species": species}); break
        var entry: Dictionary = factory.fish[-1]
        if entry.species != species or not is_instance_valid(entry.model) or not is_instance_valid(entry.skeleton):
            failures.append({"code": "factory_species_invalid", "species": species}); break
        var final := inspect_model(entry.model)
        final.totals["repeated_index_triangles"] = 0
        var parts: Array = []
        for row in final.meshes:
            var instance: MeshInstance3D = entry.model.get_node(row.node)
            var triangles := 0
            for surface in row.surfaces:
                triangles += int(surface.triangles)
                var arrays: Array = instance.mesh.surface_get_arrays(surface.surface)
                var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
                surface["repeated_index_triangles"] = repeated_index_count(indices) if instance.mesh.surface_get_primitive_type(surface.surface) == Mesh.PRIMITIVE_TRIANGLES else 0
                final.totals.repeated_index_triangles += int(surface.repeated_index_triangles)
                var material = instance.get_active_material(surface.surface)
                var uses_id: bool = material is ShaderMaterial and material.shader != null and "VERTEX_ID" in material.shader.code
                surface["active_shader_uses_VERTEX_ID"] = uses_id
                if material is ShaderMaterial and material.shader != null:
                    surface["active_shader_resource"] = material.shader.resource_path
                    surface["active_shader_sha256"] = material.shader.code.sha256_text()
            var bounds: AABB = instance.mesh.get_aabb()
            row["mesh_aabb_size_native"] = [bounds.size.x, bounds.size.y, bounds.size.z]
            # Keep material identity/dependency flags; no repeated texture records.
            row.erase("materials")
            parts.append({"node": row.node, "visible": row.visible, "triangles": triangles,
                "share_of_visible_fish": float(triangles) / maxf(1.0, final.totals.visible_triangles) if row.visible else 0.0})
        parts.sort_custom(func(a, b): return a.triangles > b.triangles)
        records.append({"species": species, "real_length_m": entry.length_m, "controller": entry.controller.get_script().resource_path,
            "totals": final.totals, "meshes": final.meshes, "top_dense_parts": parts.slice(0, 8)})
        print("GEOMETRY_V4 ", JSON.stringify({"species": species, "totals": final.totals, "top_dense_parts": parts.slice(0, 4)}))
        factory.fish.erase(entry); entry.carrier.free()
        await process_frame
    var after: Dictionary = current_bindings()
    var changes: Array = []
    for path in before:
        if before[path] != after.get(path): changes.append(path)
    for path in after:
        if not before.has(path): changes.append(path)
    for path in input_bindings:
        if input_bindings[path] != FileAccess.get_sha256(path): changes.append(path)
    if not changes.is_empty(): failures.append({"code": "source_changed", "paths": changes})
    if records.size() != SELECTED.size(): failures.append({"code": "incomplete_species_inventory"})
    var report := {"schema_version": 1, "command": "fish.geometry-redundancy.current-inventory", "ok": failures.is_empty(),
        "status": "done" if failures.is_empty() else "failed", "next_action": "human_review" if failures.is_empty() else "fix_input",
        "self_test": fixture_ok, "inputs": {"selected_species": SELECTED, "bindings_sha256": before, "external_and_loaded_resources_sha256": input_bindings, "changed_sources": changes,
            "excluded_whale_only_paths_not_hashed": excluded_paths, "shared_json_and_shaders_remain_bound": true},
        "inventory": records, "environment": {"headless": DisplayServer.get_name() == "headless", "rendering_method": RenderingServer.get_current_rendering_method()},
        "scope": ["Current final factory assembly only, no production changes or decimation", "Base triangle counts, not rendered LOD/pixel cost", "Repeated-index triangle primitives have coincident index endpoints under any shared vertex/skinning evaluation; no deletion or renumbering performed", "Rest-position zero/coincident/unused diagnostics are candidates; no attribute, skinning or semantic removability proof", "Flatness or density is not a harmless deletion proof", "No target triangle count or asset acceptance"],
        "engine_error_check": "pending external stdout/log scan; not deliverable until sealed", "failures": failures}
    FileAccess.open(output.path_join("inventory.validation.json"), FileAccess.WRITE).store_string(JSON.stringify(report, "  ") + "\n")
    factory.free(); binder.free()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    print("GEOMETRY_V4_FINISH ", JSON.stringify({"ok": report.ok, "species": records.size(), "bindings": before.size()}))
    quit(0 if report.ok else 1)
