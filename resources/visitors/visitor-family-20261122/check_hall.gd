extends SceneTree
## Exercise the actual cold-imported meshes, the exhibit and both camera views.

func _initialize() -> void:
    check.call_deferred()

func check() -> void:
    var scene = load("res://scenes/visitor_family_hall.tscn").instantiate()
    root.add_child(scene)
    await process_frame
    var problems: Array[String] = []
    var guests := {}
    var tank: Dictionary = scene.hall.objects[0]
    var shell: AABB = tank.node.global_transform * scene.hall._bounds(tank.data)
    var contents = tank.node.get_node("Shell/Contents")
    if contents.swimmers.size() != 3 or not scene.hall.read_only:
        problems.append("Expected a three-fish exhibit in a read-only hall")
    if scene.family.get_child_count() != 4:
        problems.append("Expected four distinct guests")
    for guest in scene.family.get_children():
        var nodes: Array = guest.find_children("*", "MeshInstance3D", true, false)
        if guest is MeshInstance3D:
            nodes.append(guest)
        var mesh: MeshInstance3D = nodes[0]
        var bounds: AABB = mesh.global_transform * mesh.get_aabb()
        var mat := mesh.get_active_material(0) as BaseMaterial3D
        var faces := mesh.mesh.get_faces().size() / 3
        if mat == null or mat.albedo_texture == null or mesh.mesh.get_surface_count() != 1:
            problems.append("Missing painted surface on " + str(guest.name))
        if absf(bounds.position.y) > .005 or bounds.intersects(shell):
            problems.append("Incorrect placement of " + str(guest.name))
        guests[str(guest.name)] = {"triangles":faces, "height_m":bounds.size.y,
            "clearance_from_glass_m":bounds.position.z - shell.end.z}
    for closeup in [false, true]:
        scene.set_view(closeup)
        await process_frame
        for guest in scene.family.get_children():
            if not scene.camera.is_position_in_frustum(guest.global_position) or not scene.camera.is_position_in_frustum(
                    guest.global_position + Vector3.UP * guests[str(guest.name)].height_m):
                problems.append("Guest outside camera view: " + str(guest.name))
    print("VISITOR_FAMILY ", JSON.stringify({"guests":guests,"fish":contents.swimmers.size(),"problems":problems}))
    scene.queue_free()
    await process_frame
    await process_frame
    quit(0 if problems.is_empty() else 1)
