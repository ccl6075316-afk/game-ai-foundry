extends SceneTree
## Compare changes in screen velocity across consecutive frames at native 1080p.
func _initialize() -> void:
    run.call_deferred()

func run() -> void:
    var tank=load("res://scenes/ocean_school_review.tscn").instantiate()
    root.add_child(tank)
    tank.set_process(false)
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--pixels="):
            await capture_zoom(tank,arg.trim_prefix("--pixels="))
            return
    var free_view:bool="--free" in OS.get_cmdline_user_args()
    var ok := Vector2i(root.get_visible_rect().size) == Vector2i(1920,1080)
    for paused:bool in [true,false]:
        tank.overview()
        tank.enter_school()
        var school:Dictionary=tank.schools[tank.focused]
        var selected:int=tank.focus_member
        tank.focus_distance=5.5 if free_view else 6.5
        tank._follow()
        tank.paused=paused
        var target:Vector3=tank._subject()
        if free_view: tank.focused=-1
        var neighbours:Array=[]
        for i in school.slots.size():
            if i==selected: continue
            var p:Vector3=tank.member_center(school,i,school.flow.Pose(i))
            neighbours.append([p.distance_squared_to(target),i])
        neighbours.sort_custom(func(a,b):return a[0]<b[0])
        neighbours.resize(24)
        var cam:Camera3D=tank.camera
        var start_eye:=cam.position
        var floor_point:=cam.position-cam.basis.z*cam.position.y/cam.basis.z.y+cam.basis.x*5.
        var last:Dictionary={}
        var prior:Dictionary={}
        var maxima:=[0.,0.,0.]
        var last_world:Dictionary={}
        var prior_world:Dictionary={}
        var max_fish_impulse:=0.
        var worst_fish:=[]
        var near_frames:=0
        var wheel:=InputEventMouseButton.new()
        wheel.pressed=true
        for frame in 330:
            if frame in [30,38,46,54,62,70,78,86,94,102,110,118,126,145,153,161,178,186,194]:
                wheel.button_index=MOUSE_BUTTON_WHEEL_DOWN if frame>=145 and frame<=161 else MOUSE_BUTTON_WHEEL_UP
                tank._unhandled_input(wheel)
            tank._process(1./60.)
            var centre:Vector3=tank.member_center(school,selected,school.flow.Pose(selected))
            var current:Dictionary={-1:cam.unproject_position(floor_point),-2:cam.unproject_position(centre)}
            var world:Dictionary={}
            var accel:Array[float]=[]
            for n in neighbours:
                var i:int=n[1]
                var pos:Vector3=tank.member_center(school,i,school.flow.Pose(i))
                if cam.is_position_behind(pos): continue
                var screen:=cam.unproject_position(pos)
                if Rect2(0,0,1920,1080).has_point(screen):
                    current[i]=screen
                    world[i]=pos
                    if frame>=30 and last_world.has(i) and prior_world.has(i):
                        var predicted:Vector3=last_world[i]+(last_world[i]-prior_world[i])
                        var change:=screen.distance_to(cam.unproject_position(predicted))
                        if change>max_fish_impulse:
                            max_fish_impulse=change
                            worst_fish=[frame,i,pos.distance_to(predicted)]
            if paused: ok = ok and cam.position.distance_to(start_eye)<.00001
            if frame>=30 and cam.position.distance_to(centre)/tank.magnification<=3.6:
                for i in current:
                    if not prior.has(i) or not last.has(i): continue
                    if not Rect2(0,0,1920,1080).has_point(current[i]): continue
                    var impulse:float=(current[i]-2.*last[i]+prior[i]).length()
                    if i<0:
                        maxima[-i-1]=maxf(maxima[-i-1],impulse)
                    else:
                        accel.append(impulse)
                if accel.size()>=3:
                    near_frames+=1
                    accel.sort()
                    maxima[2]=maxf(maxima[2],accel[accel.size()/2])
            prior=last
            last=current
            prior_world=last_world
            last_world=world
        print("ZOOM_MOTION free=",free_view," paused=",paused," measured_near_frames=",near_frames," max change in px/frame [floor,subject,median neighbours]=",maxima," individual_world_impulse_px=",max_fish_impulse," worst=",worst_fish)
        ok = ok and near_frames>=30 and maxima.max()<2.5 and max_fish_impulse<2.5
    # Half-notch high-resolution wheel events must land at the same final
    # magnification as one ordinary notch, independent of presentation rate.
    var wheel:=InputEventMouseButton.new()
    wheel.pressed=true
    wheel.button_index=MOUSE_BUTTON_WHEEL_UP
    wheel.factor=.5
    for fps:int in [30,60,120]:
        tank.overview()
        tank._unhandled_input(wheel)
        tank._unhandled_input(wheel)
        for frame in 2*fps: tank._scroll(1./fps)
        ok = ok and absf(tank.magnification-1./.82)<.0001
    quit(0 if ok else 1)

## Native backbuffer replay consumed by verify_croaker_zoom_pixels.py.
func capture_zoom(tank, prefix:String) -> void:
    tank.watch_neighbours()
    tank.paused=true
    var pixels:=FileAccess.open(prefix+".gray",FileAccess.WRITE)
    var metadata:=FileAccess.open(prefix+".csv",FileAccess.WRITE)
    if not pixels or not metadata:
        quit(2)
        return
    var cam:Camera3D=tank.camera
    var eye:=cam.position
    var wheel:=InputEventMouseButton.new()
    wheel.position=Vector2(970,500)
    wheel.global_position=wheel.position
    wheel.pressed=true
    for frame in 164:
        if frame in [15,28,34,53,58,65,79,86,106,111,133,142]:
            wheel.button_index=MOUSE_BUTTON_WHEEL_DOWN if frame in [106,111] else MOUSE_BUTTON_WHEEL_UP
            root.push_input(wheel,true)
        tank._process(1./60.)
        await RenderingServer.frame_post_draw
        var image:=root.get_texture().get_image()
        if image.get_size()!=Vector2i(1920,1080):
            quit(3)
            return
        image.convert(Image.FORMAT_L8)
        pixels.store_buffer(image.get_data())
        metadata.store_line("%d,%.9f,%.9f,%.8f"%[frame,cam.position.distance_to(eye),cam.fov,cam.position.distance_to(tank._subject())])
    pixels.close()
    metadata.close()
    quit()
