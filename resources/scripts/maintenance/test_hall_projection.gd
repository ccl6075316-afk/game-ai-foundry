extends SceneTree
## Exercise document/command/projection separation against actual Godot nodes.
const Hall=preload("res://scripts/aquarium/AquariumHall3D.gd")
var directory := ""
var checks: Dictionary={}

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--maintenance-dir="):directory=arg.trim_prefix("--maintenance-dir=")
    if directory.is_empty():quit(2);return
    DirAccess.make_dir_recursive_absolute(directory)
    call_deferred("_run")

func _run() -> void:
    var hall=Hall.new();hall.configure_save(directory+"/never-a-player-save.json",false);root.add_child(hall)
    for i in 3:await process_frame
    var started := Time.get_ticks_usec()
    for i in 12:
        hall.build_commands.execute("patch",{"id":"bench-1","patch":{"at":[.25 if i%2 else 0,.85]}},false)
    var command_mean_usec: float=(Time.get_ticks_usec()-started)/12.0
    print("MODEL_COMMAND_MEAN_USEC ",command_mean_usec)
    var minimal := {"schema_version":1,"floor_style":0,"wall_style":0,"objects":[
        {"id":"bench","kind":"bench","name":"bench","at":[-4,2],"yaw":0.0,"scale":1.0},
        {"id":"wall","kind":"wall","name":"wall","at":[4,2],"yaw":0.0,"scale":1.0,"length":3.0,"door":false}]}
    # Version 1 disallows partitions; construct the exact same valid schema2 fixture.
    minimal.schema_version=2;minimal.parcels=hall.Footprint.initial()
    hall._restore(minimal)
    for i in 3:await process_frame
    checks.scene_materialized=hall.objects.size()==2 and hall._valid_state(hall._state())
    var bench_id: int=hall.objects[0].node.get_instance_id()
    var wall_body: int=hall.objects[1].body.get_instance_id()
    var at: Vector3=hall.objects[0].node.position
    var receipt: Dictionary=hall.build_commands.execute("patch",{"id":"bench","patch":{"at":[-3,2]}})
    checks.command_updates_document_without_nodes=receipt.ok and hall.document.object_data("bench").at[0]==-3 and hall.objects[0].node.position==at
    hall._apply_document(false,receipt)
    checks.projection_updates_same_node=hall.objects[0].node.position.x==-3 and hall.objects[0].node.get_instance_id()==bench_id
    checks.unrelated_wall_collision_reused=hall.objects[1].body.get_instance_id()==wall_body
    hall._change_finish("wall_style")
    checks.finish_change_does_not_rebuild_collision=hall.objects[1].body.get_instance_id()==wall_body
    var saved := JSON.stringify(hall._state())
    hall.objects[0].data.at[0]=500;hall.objects[0].node.position.x=500
    checks.scene_cannot_mutate_document=JSON.stringify(hall._state())==saved
    hall._restore(hall._state())
    checks.restore_projects_authoritative_values=hall.objects[0].node.position.x==-3
    hall._mode(false);hall.selected=0
    var key := InputEventKey.new();key.keycode=KEY_DELETE;key.pressed=true
    saved=JSON.stringify(hall._state());hall._unhandled_key_input(key)
    checks.walk_mode_does_not_edit=JSON.stringify(hall._state())==saved
    hall._save_layout()
    checks.readonly_does_not_write=not FileAccess.file_exists(directory+"/never-a-player-save.json")
    hall._undo()
    checks.undo_projects_previous_document=hall.wall_style==0
    var okay := not checks.values().has(false)
    var file=FileAccess.open(directory+"/projection.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"ok":okay,"checks":checks,"default_layout_command_mean_usec":command_mean_usec},"  "));file.close()
    hall.queue_free()
    for i in 3:await process_frame
    print("HALL_PROJECTION ",okay," ",checks.size());quit(0 if okay else 1)
