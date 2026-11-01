extends SceneTree
const Lab=preload("res://scripts/aquarium/passage/PassageLab.gd")
const Route=preload("res://scripts/aquarium/passage/PassageRoute.gd")
var lab
var directory := ""
var checks: Dictionary={}
var outputs: Array=[]
var measurements: Dictionary={}

func check(id: String,okay: bool) -> void:
    checks[id]=okay;print("PASSAGE_CHECK ",id," ",okay)

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--report-dir="):directory=arg.trim_prefix("--report-dir=")
    if directory.is_empty():quit(2);return
    DirAccess.make_dir_recursive_absolute(directory);call_deferred("run")

func settle() -> void:
    for i in 8:await process_frame
    await RenderingServer.frame_post_draw

func capture(name_value: String) -> void:
    await settle()
    var path := directory+"/"+name_value+".png"
    check("image_"+name_value,root.get_texture().get_image().save_png(path)==OK);outputs.append(path)

func patch(image_value: Image,position_value: Vector3) -> Color:
    var p := Vector2i(lab.eye.unproject_position(position_value));var color := Color(0,0,0,0)
    if not Rect2i(3,3,1914,1074).has_point(p):return Color.BLACK
    for x in range(-2,3):
        for y in range(-2,3):color+=image_value.get_pixelv(p+Vector2i(x,y))
    return color/25

func walk(section: String) -> void:
    var config := Route.initial();config.section=section
    check(section+"_route_committed",lab.commit(config))
    if lab.editing:lab.toggle_mode()
    lab.spawn_player();lab.set_physics_process(false)
    var path: PackedVector3Array=lab.world.path;var index := 1;var fell := false
    var highest: float=lab.player.position.y;var stalled := 0;var previous: Vector3=lab.player.position
    var goal: Vector3=path[-1]+Vector3(1 if path[-1].x>0 else -1,0,0)
    for frame in 1100:
        await physics_frame
        var target: Vector3=path[index] if index<path.size() else goal
        var delta: Vector3=target-lab.player.position;delta.y=0
        if delta.length()<.24:
            if index<path.size():index+=1;continue
            break
        var direction := delta.normalized()
        lab.player.rotation.y=atan2(-direction.x,-direction.z);lab.eye.rotation.x=-.08
        lab.walk_step(direction,1.0/60)
        highest=maxf(highest,lab.player.position.y)
        if lab.player.position.y< -.5:fell=true
        if lab.player.position.distance_to(previous)<.005:stalled+=1
        else:stalled=0
        previous=lab.player.position
        if frame==240:await capture(section+"-inside")
        if stalled>90:break
    var distance := Vector2(lab.player.position.x-goal.x,lab.player.position.z-goal.z).length()
    check(section+"_walk_reaches_exit_platform",index>=path.size() and distance<.35)
    check(section+"_actual_ascent_over_two_metres",highest>3.5)
    check(section+"_no_floor_fall",not fell)
    measurements[section+"_walk"]={"last_waypoint":index,"waypoints":path.size(),"exit_distance":distance,"position":Route.array(lab.player.position),"highest":highest,"stall_frames":stalled}
    await capture(section+"-exit")
    lab.toggle_mode()

func gpu_review(section: String) -> void:
    var config := Route.initial();config.section=section;config.points=[[-13.0,1.0,0.0],[13.0,1.0,0.0]]
    check(section+"_gpu_straight_route_valid",lab.commit(config))
    if lab.editing:lab.toggle_mode()
    lab.player.rotation=Vector3.ZERO;lab.eye.global_position=Vector3(0,2.6,0);lab.eye.look_at(Vector3(0,2.6,6))
    lab.world.frozen=true
    for row in lab.world.fish:row.carrier.hide()
    var donors := Node3D.new();lab.world.add_child(donors)
    var positions := [Vector3(-.7,2.6,.8),Vector3(0,2.6,3),Vector3(1,2.6,5)]
    var material := StandardMaterial3D.new();material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;material.albedo_color=Color(.8,.65,.3)
    for p in positions:lab.world.box(donors,p,Vector3(.6,.6,.03),material)
    lab.world.water_renderer.enabled=false;await settle()
    var off: Image=lab.viewport.get_texture().get_image();await capture(section+"-gpu-water-off")
    lab.world.water_renderer.enabled=true;await settle()
    var on: Image=lab.viewport.get_texture().get_image();await capture(section+"-gpu-water-on")
    var ratios: Array=[]
    for p in positions:
        var a := patch(off,p);var b := patch(on,p);ratios.append(b.r/maxf(a.r,.001))
    check(section+"_gpu_dry_donor_unchanged",absf(ratios[0]-1)<.005)
    check(section+"_gpu_water_remains_beyond_glass",ratios[1]<.985 and ratios[2]<ratios[1]-.01)
    measurements[section+"_gpu_red_ratios"]=ratios
    measurements[section+"_cpu_water_lengths"]=[]
    for p in positions:
        var origin: Vector3=lab.eye.global_position;var direction: Vector3=(p-origin).normalized()
        measurements[section+"_cpu_water_lengths"].append(lab.world.water_renderer.ray_length(lab.world.water_proxy,origin,direction,origin.distance_to(p)))
    # Walk sideways into the real cover; a visual-only tube would allow escape.
    lab.player.position=Vector3(0,1.88,0);lab.player.velocity=Vector3.ZERO
    for frame in 100:
        await physics_frame
        lab.walk_step(Vector3.BACK,1.0/60)
    check(section+"_shell_blocks_sideways_escape",absf(lab.player.position.z)<1.5 and lab.player.position.y>1.7)
    donors.queue_free()
    for row in lab.world.fish:row.carrier.show()
    lab.world.frozen=false;lab.toggle_mode()

func run() -> void:
    lab=Lab.new();lab.save_path=directory+"/not-a-player-save.json";lab.read_only=true;root.add_child(lab);lab.set_physics_process(false)
    await settle()
    check("initial_route_valid",Route.validate(lab.session.route).is_empty())
    check("twenty_four_existing_swimming_fish",lab.world.fish.size()==24)
    check("real_floor_and_shell_collisions",lab.world.cover.floor_body!=null and lab.world.cover.shell_body!=null)
    await capture("01-editor")
    lab.selected=2;lab.sync_panel();var original: Dictionary=lab.session.route.duplicate(true)
    lab.y_spin.value=1.6
    check("actual_height_control_edits_point",lab.session.route.points[2][1]==1.6)
    lab.undo();check("undo_height",lab.session.route.points[2][1]==original.points[2][1])
    lab.redo();check("redo_height",lab.session.route.points[2][1]==1.6)
    lab.width_spin.value=2.8
    check("actual_width_control",lab.session.route.width==2.8)
    lab.section_choice.select(1);lab.section_choice.item_selected.emit(1)
    check("actual_section_control",lab.session.route.section=="arch")
    check("route_saved_to_explicit_fixture",lab.session.save(directory+"/edited-route.json"))
    lab.reset_route();check("saved_route_cold_read",lab.session.load_route(directory+"/edited-route.json").is_empty() and lab.session.route.section=="arch")
    lab.apply_route()
    lab.read_only=true;lab.save_route();check("readonly_avoids_player_save",not FileAccess.file_exists(lab.save_path))
    var click := InputEventMouseButton.new();click.button_index=MOUSE_BUTTON_LEFT;click.pressed=true
    click.position=lab.editor_camera.unproject_position(Route.point(lab.session.route.points[2])+Vector3.UP*.1)
    lab.canvas.gui_input.emit(click);check("actual_canvas_selects_control_point",lab.selected==2 and lab.dragging)
    var motion := InputEventMouseMotion.new();motion.position=lab.editor_camera.unproject_position(Route.point(lab.session.route.points[2])+Vector3(.3,0,.2))
    lab.canvas.gui_input.emit(motion);click.pressed=false;lab.canvas.gui_input.emit(click)
    check("actual_canvas_drag_commits",not lab.dragging and absf(lab.session.route.points[2][0]-.3)<.11)
    lab.start_drawing()
    for p in Route.initial().points:
        lab.y_spin.value=p[1];click.pressed=true;click.position=lab.editor_camera.unproject_position(Route.point(p));lab.canvas.gui_input.emit(click)
        click.pressed=false;lab.canvas.gui_input.emit(click)
    lab.finish_drawing()
    check("actual_clicks_draw_complete_ascending_route",not lab.drawing and lab.session.route.points.size()==5 and lab.session.route.points[-1][1]==3)
    var committed: Dictionary=lab.session.route.duplicate(true)
    lab.start_drawing();lab.redo()
    check("redo_cancels_unfinished_draft",not lab.drawing and lab.session.route==committed)
    lab.toggle_mode();lab.set_edit_view(false)
    check("view_button_returns_to_editor",lab.editing and lab.editor_camera.current)
    await capture("02-drawn-route")
    await walk("round")
    await walk("arch")
    await gpu_review("round")
    await gpu_review("arch")
    lab.reset_route();await settle()
    for frame in 120:await process_frame
    check("fish_remain_outside_dry_volume",lab.world.fish_clearance_failures==0)
    var okay := not checks.values().has(false)
    var file=FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"ok":okay,"checks":checks,"measurements":measurements,"outputs":outputs,"user_acceptance":"pending"},"  "));file.close()
    lab.queue_free()
    for i in 3:await process_frame
    print("PASSAGE_REVIEW ",okay," ",checks.size());quit(0 if okay else 1)
