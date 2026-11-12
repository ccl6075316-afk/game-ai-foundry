extends SceneTree
## Integration smoke check. Per-fish geometry, contact and visual reports remain separate.
const SPECIES = ["red_seabream", "black_seabream", "piranha", "peacock_bass", "yellow_croaker", "zander", "arapaima", "pacific_bluefin_tuna", "blacktip_reef_shark"]
var output = ""
var selected_species = SPECIES
var result = {"kind":"tail_repair_actual_canonical_entries", "ok":false, "fresh_process":true, "user_acceptance":false, "physics_490_077_repeated":false, "fish":[], "checks":[], "errors":[]}

func ck(value: bool, description: String):
    result.checks.append({"check":description, "ok":value})
    if not value: result.errors.append(description)

func static_digest(model):
    var h = HashingContext.new()
    h.start(HashingContext.HASH_SHA256)
    for mesh in model.find_children("*", "MeshInstance3D", true, false):
        for surface in mesh.mesh.get_surface_count(): h.update(var_to_bytes(mesh.mesh.surface_get_arrays(surface)))
        for bind in mesh.skin.get_bind_count(): h.update(var_to_bytes([mesh.skin.get_bind_name(bind), mesh.skin.get_bind_bone(bind), mesh.skin.get_bind_pose(bind)]))
    var skeleton = model.find_children("*", "Skeleton3D", true, false)[0]
    for bone in skeleton.get_bone_count(): h.update(var_to_bytes([skeleton.get_bone_name(bone), skeleton.get_bone_parent(bone), skeleton.get_bone_rest(bone)]))
    return h.finish().hex_encode()

func material_digest(model):
    var h = HashingContext.new()
    h.start(HashingContext.HASH_SHA256)
    for mesh in model.find_children("*", "MeshInstance3D", true, false):
        for surface in mesh.mesh.get_surface_count():
            var m = mesh.get_active_material(surface) as BaseMaterial3D
            h.update(var_to_bytes([m.albedo_color, m.transparency, m.alpha_scissor_threshold, m.cull_mode, m.texture_filter, m.roughness, m.metallic, m.emission_enabled, m.emission]))
            if m.albedo_texture != null: h.update(m.albedo_texture.get_image().get_data())
            if m.emission_texture != null: h.update(m.emission_texture.get_image().get_data())
    return h.finish().hex_encode()

func _initialize():
    var args = OS.get_cmdline_user_args()
    if args.size() not in [2,4] or args[0] != "--output" or (args.size()==4 and args[2]!="--species"):
        push_error("Use -- --output <absolute experiment validation.json>")
        quit(1)
        return
    if args.size()==4: selected_species = Array(str(args[3]).split(","))
    output = str(args[1])
    if not output.is_absolute_path() or FileAccess.file_exists(output):
        push_error("Output must be a new absolute file")
        quit(1)
        return
    DirAccess.make_dir_recursive_absolute(output.get_base_dir())
    call_deferred("run")

func run():
    var cache = load("res://scripts/aquarium/FishAppearanceCache.gd")
    cache.begin_entry()
    var width = load("res://scripts/aquarium/FinalizedWidthBatch20261101.gd").new()
    var eleven = load("res://scripts/aquarium/FinalizedElevenFish20261105.gd").new()
    var fishing = load("res://scripts/screens/FishingVolumeFish.gd")
    var exhibit = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    exhibit._load_profiles()
    var world = Node3D.new()
    root.add_child(world)
    for species in selected_species:
        var is_width = width.table().has(species)
        var helper = width if is_width else eleven
        var row = helper.table()[species]
        var path = "res://assets/models/fish/%s.glb" % species
        ck(FileAccess.get_sha256(path) == row.model_sha256, species + " actual canonical GLB hash")
        ck(helper.matches_path(path, species), species + " finalized branch selected")
        var old_size = exhibit.fish.size()
        exhibit._add_fish(world, species, float(row.real_length_cm)/100.0, exhibit.profiles[species])
        if exhibit.fish.size() != old_size + 1:
            ck(false, species + " actual display entry created")
            continue
        var entry = exhibit.fish[-1]
        var model = entry.model
        var receipt = model.get_meta("final_width20261101_receipt" if is_width else "final_eleven_receipt", {})
        ck(not receipt.is_empty() and receipt.get("static_builders_disabled", false) and receipt.get("runtime_static_build_calls", receipt.get("static_build_calls", -1)) == 0, species + " exact finalizer without static builders")
        var expected_scale = float(row.model_scale if is_width else row.review_model_scale)
        ck(absf(model.scale.x - expected_scale) < .000001, species + " reviewed display scale")
        ck(entry.profile == helper.motion_profile(species), species + " exact motion profile")
        ck(entry.controller.get_script().resource_path == (helper.controller_script(species) if is_width else row.motion_runtime), species + " exact controller")
        ck(model.find_children("*", "Skeleton3D", true, false).size() == 1 and model.find_children("*", "AnimationPlayer", true, false).size() == 1, species + " one skeleton and player")
        for mesh in model.find_children("*", "MeshInstance3D", true, false):
            for surface in mesh.mesh.get_surface_count():
                var material = mesh.get_active_material(surface) as BaseMaterial3D
                ck(material != null and material.texture_filter == BaseMaterial3D.TEXTURE_FILTER_NEAREST, species + " nearest " + str(mesh.name) + ":" + str(surface))
        var direct = helper.load_model(path, species)
        if not is_width: helper._bind_nearest(direct.find_children("*", "MeshInstance3D", true, false))
        ck(static_digest(model) == static_digest(direct), species + " source versus actual entry arrays rig exact")
        ck(material_digest(model) == material_digest(direct), species + " source versus actual entry material RGBA exact")
        var cached_size = exhibit.fish.size()
        exhibit._add_fish(world, species, float(row.real_length_cm)/100.0, exhibit.profiles[species])
        ck(exhibit.fish.size() == cached_size + 1 and exhibit.loading_metrics[-1].reused_appearance, species + " real second entry uses prepared cache")
        var cached = exhibit.fish[-1].model
        ck(static_digest(cached) == static_digest(direct) and material_digest(cached) == material_digest(direct), species + " actual cached arrays rig RGBA exact")
        direct.free()
        var before = static_digest(model)
        for action in ["Swim", "Turn", "Ascend", "Dive", "Swim"]:
            entry.controller.set_action(action)
            for phase in 90: entry.controller.step(1.0/60.0)
        ck(before == static_digest(model), species + " action changes retain static geometry UV skin rig")
        if species in ["peacock_bass", "arapaima"]: ck(not entry.has("jaw_controller") and entry.controller.jaw_controller != null, species + " single jaw owner")
        var actor = fishing.new()
        world.add_child(actor)
        var ready = actor.configure(species)
        ck(ready and actor.ready_model, species + " actual Fishing configure")
        var recipe = helper.mouth_recipe(species) if helper.requires_mouth_recipe(species) else {}
        var poses = []
        if ready and not recipe.is_empty():
            var p = recipe.position_native
            var expected = Vector3(p[0], p[1], p[2])
            ck(actor.mouth_vertex.distance_to(expected) < .0000001 and str(actor.mouth_mesh.name) == str(recipe.mesh), species + " exact body-owned upper lip")
            var actor_before = static_digest(actor.model)
            for action in ["Swim", "Turn", "Ascend", "Dive"]:
                actor.animate(.25, action)
                actor.skeleton.force_update_all_bone_transforms()
                var mouth = actor.mouth_world()
                ck(mouth.is_finite(), species + " real skinned lip " + action)
                ck(actor.carrier.transform.is_equal_approx(Transform3D.IDENTITY), species + " Fishing owns world transform " + action)
                poses.append({"action":action, "position":[mouth.x, mouth.y, mouth.z]})
            ck(actor_before == static_digest(actor.model), species + " Fishing actions retain static arrays")
            var hook = Vector3(.1, .3, .2)
            actor.place_hook(hook, Vector3.LEFT)
            ck(actor.mouth_world().distance_to(hook) < .00001, species + " actual upper lip hook placement")
        result.fish.append({"species":species, "model_sha256":row.model_sha256, "recipe_sha256":row.get("mouth_recipe", {}).get("sha256", "existing fallback unchanged"), "display_scale":model.scale.x, "table_scale":expected_scale, "inventory":receipt, "static_digest":before, "mouth_poses":poses})
        actor.free()
    result.ok = result.fish.size() == selected_species.size() and result.errors.is_empty()
    var file = FileAccess.open(output, FileAccess.WRITE)
    file.store_string(JSON.stringify(result, "  "))
    file.close()
    print("REPAIRED_NINE_CANONICAL ", result.ok, " fish=", result.fish.size(), " checks=", result.checks.size())
    cache.clear()
    exhibit.fish.clear()
    exhibit.free()
    world.free()
    await process_frame
    await process_frame
    quit(0 if result.ok else 1)
