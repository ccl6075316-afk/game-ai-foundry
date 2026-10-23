extends "trial_swim_gait132.gd"
## Supplemental candidate GPU coverage; baseline topology/donor gate is separate.

var body_viewport: SubViewport

func _shot(path: String) -> void:
    await process_frame
    await process_frame
    await RenderingServer.frame_post_draw
    body_viewport.get_texture().get_image().save_png(path)

func run() -> void:
    _setup()
    var entry := _spawn(Vector3.ZERO)
    var wrapper = _make_gait(entry)
    body_viewport = SubViewport.new()
    body_viewport.size = Vector2i(640, 640)
    body_viewport.own_world_3d = true
    body_viewport.transparent_bg = true
    body_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    root.add_child(body_viewport)
    world.reparent(body_viewport)
    var env := WorldEnvironment.new()
    env.environment = Environment.new()
    env.environment.background_mode = Environment.BG_CLEAR_COLOR
    env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.environment.ambient_light_energy = 1.0
    world.add_child(env)
    camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.size = 0.25
    camera.near = 0.001
    world.add_child(camera)
    var ownership: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles.bluegill
    var opacity: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/body-opacity.json")).profiles.bluegill
    var bodies: Array = []
    for mesh in entry.model.find_children("*", "MeshInstance3D", true, false):
        if ownership.fins.has(str(mesh.name)) or str(mesh.name) in opacity.suppressed_auxiliary or opacity.decorative_overlays.has(str(mesh.name)) or mesh.has_meta("decorative_relief112"):
            mesh.hide()
            continue
        var materials: Array = []
        for s in mesh.mesh.get_surface_count(): materials.append(mesh.get_active_material(s))
        bodies.append({"mesh":mesh,"materials":materials})
    assert(not bodies.is_empty())
    var reference := StandardMaterial3D.new()
    reference.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    reference.cull_mode = BaseMaterial3D.CULL_DISABLED
    reference.albedo_color = Color.WHITE
    var views := [[0.0,0.0],[PI,0.0],[PI/2.0,0.0],[-PI/2.0,0.0],[0.5,0.85],[0.5,-0.85],[PI+0.5,0.65],[PI+0.5,-0.65]]
    var records: Array = []
    var index := 0
    for action in ["Swim", "Turn", "Ascend", "Dive"]:
        assert(wrapper.set_action(action))
        for phase in [0.65, 1.9]:
            var wait := fposmod(float(phase) - fposmod(wrapper.elapsed, float(config.cycle_seconds)), float(config.cycle_seconds))
            var steps := maxi(1, roundi(wait * 120.0))
            for k in steps: wrapper.step(1.0 / 120.0)
            await process_frame
            await process_frame
            var pairs: Array = []
            for v in views.size():
                var tr: Transform3D = entry.carrier.global_transform
                var yaw: float = views[v][0]
                var elevation: float = views[v][1]
                camera.global_position = tr.origin + tr.basis.orthonormalized() * Vector3(sin(yaw)*cos(elevation),sin(elevation),cos(yaw)*cos(elevation)) * 0.7
                camera.look_at(tr.origin, tr.basis.orthonormalized() * Vector3.UP)
                var stem := "body-p%02d-v%d" % [index, v]
                for b in bodies:
                    for s in b.materials.size(): b.mesh.set_surface_override_material(s, b.materials[s])
                await _shot(output.path_join(stem + "-actual.png"))
                for b in bodies:
                    for s in b.materials.size(): b.mesh.set_surface_override_material(s, reference)
                await _shot(output.path_join(stem + "-closed.png"))
                pairs.append({"actual":stem + "-actual.png","reference":stem + "-closed.png","actual_sha256":FileAccess.get_sha256(output.path_join(stem + "-actual.png")),"reference_sha256":FileAccess.get_sha256(output.path_join(stem + "-closed.png"))})
            records.append({"action":action,"candidate":wrapper.snapshot(),"pairs":pairs})
            index += 1
    var bindings := _inputs()
    bindings["body_capture"] = FileAccess.get_sha256(get_script().resource_path)
    for file in ["res://assets/models/fish/motion/body-opacity.json","res://assets/models/fish/motion/surface-ownership.json","res://scripts/aquarium/FishBodyOpaque.gdshader","res://scripts/aquarium/FishMouthPigment.gdshader"]:
        bindings[file] = FileAccess.get_sha256(file)
    _save("body-capture.validation.json", {"ok":true,"command":"fish.swim-gait132.body-capture","status":"done","next_action":"human_review","inputs":bindings,"records":records,"scope":"64 views across eight actual candidate propel/coast and four-action poses; fins hidden. Compare identical posed geometry using actual production body materials and opaque reference. Supplemental to baseline closed-shell/donor gate, not full visual acceptance."})
    factory.free()
    quit()
