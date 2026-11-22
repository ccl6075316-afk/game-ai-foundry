extends SceneTree
## Run with --fixed-fps 60 --resolution 1920x1080 -- --expect=1920x1080.
## Simulation advances by 1/60 per image while frame intervals use wall time.
class TimedTank extends "res://scripts/aquarium/ocean_school/OceanSchoolReview.gd":
    var sim_usec := 0
    func _move_animals(dt:float) -> void:
        var start:=Time.get_ticks_usec()
        super._move_animals(dt)
        sim_usec=Time.get_ticks_usec()-start

func _initialize() -> void:
    run.call_deferred()

func run() -> void:
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var tank:=TimedTank.new()
    root.add_child(tank)
    var output:=""
    var expected:=Vector2i(1920,1080)
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="): output=arg.trim_prefix("--output=")
        if arg.begins_with("--expect="):
            var dims:=arg.trim_prefix("--expect=").split("x")
            expected=Vector2i(int(dims[0]),int(dims[1]))
    await RenderingServer.frame_post_draw
    var actual:=root.get_texture().get_image().get_size()
    print("OCEAN_DEVICE ",RenderingServer.get_video_adapter_name()," renderer=",RenderingServer.get_current_rendering_method()," pixels=",actual," 3d_scale=",root.scaling_3d_scale)
    if actual!=expected or not is_equal_approx(root.scaling_3d_scale,1.):
        quit(4)
        return
    var n:=1
    for s in tank.schools: n+=s.node.multimesh.instance_count
    if n!=20000: quit(1); return
    for mode in ["overview","dive","inside","feed"]:
        if mode=="dive":
            tank.enter_school()
            tank.focus_distance=32.
        var followed:=tank.focused
        var member:=tank.focus_member
        var seen_levels:Dictionary={}
        if mode=="feed": tank.feed()
        var frames:Array[float]=[]
        var cpu:Array[float]=[]
        var focus_error:=0.0
        var previous:=0
        for i in 300:
            await process_frame
            if mode=="dive":
                tank.focus_distance=lerpf(32.,1.2,smoothstep(0.,240.,i))
                tank._follow()
                seen_levels[tank.schools[followed].level]=true
            var now:=Time.get_ticks_usec()
            if i>=60:
                frames.append((now-previous)/1000.)
                cpu.append(tank.sim_usec/1000.)
                if tank.focused>=0:
                    focus_error=maxf(focus_error,absf(tank.camera.position.distance_to(tank._subject())-tank.focus_distance))
            previous=now
            if i==25 and not output.is_empty():
                await RenderingServer.frame_post_draw
                root.get_texture().get_image().save_jpg(output+"/"+mode+".jpg",.91)
        var levels:=[0,0,0]
        for s in tank.schools:
            levels[0]+=int(s.detail_count)
            levels[maxi(1,s.level)]+=s.node.multimesh.instance_count-int(s.detail_count)
        frames.sort()
        cpu.sort()
        print("OCEAN_BENCH ",JSON.stringify({"mode":mode,"individuals":n,"levels":levels,"sample_frames":frames.size(),
            "frame_ms":[frames[119],frames[227],frames[237]],"fish_update_ms":[cpu[119],cpu[227]],"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
            "feed_schools":tank.feeding_groups,"pellets_left":tank.pellets_left,"focus_error_m":focus_error,"zoom_levels":seen_levels.keys()}))
        if mode=="dive" and (seen_levels.size()!=3 or tank.focused!=followed or tank.focus_member!=member):
            quit(3)
            return
        if focus_error>.005 or (mode=="feed" and (tank.feeding_groups==0 or tank.feeding_groups>=tank.SCHOOLS)):
            quit(2)
            return
    quit()
