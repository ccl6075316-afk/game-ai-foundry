extends SceneTree
## Compare both sides of each mesh handoff with identical camera and animation.
func _initialize() -> void:
    run.call_deferred()

func capture() -> Image:
    await RenderingServer.frame_post_draw
    return root.get_texture().get_image().get_region(Rect2(700,330,520,420))

func run() -> void:
    var tank=load("res://scenes/ocean_school_review.tscn").instantiate()
    root.add_child(tank)
    tank.set_process(false)
    var lengths:Array[float]=[]
    var ok:=true
    var box:AABB=tank.skin.meshes[0].get_aabb()
    for school:Dictionary in tank.schools:
        var batch:MultiMesh=school.node.multimesh
        var small:=0
        var large:=0
        for i in batch.instance_count:
            var length_m:=batch.get_instance_transform(i).basis.x.length()*box.size.x
            lengths.append(length_m)
            if length_m<.22: small+=1
            if length_m>.49: large+=1
        if mini(small,large)<batch.instance_count*.15:
            push_error("Insufficient size variation in school starting at fish %d" % school.first_id)
            ok=false
    lengths.sort()
    print("CROAKER_LENGTH_CM min_p10_p50_p90_max=", [100*lengths.front(),100*lengths[lengths.size()/10],100*lengths[lengths.size()/2],100*lengths[lengths.size()*9/10],100*lengths.back()])
    tank.hide()
    for layer in tank.find_children("*","CanvasLayer",false,false): layer.visible=false
    root.transparent_bg=true
    var camera:=Camera3D.new()
    root.add_child(camera)
    camera.position=Vector3(0,.16,1.1)
    camera.look_at(Vector3.ZERO)
    camera.make_current()
    var fish:=MultiMeshInstance3D.new()
    var mesh:=MultiMesh.new()
    mesh.transform_format=MultiMesh.TRANSFORM_3D
    mesh.use_custom_data=true
    mesh.instance_count=1
    mesh.set_instance_transform(0,Transform3D(Basis.IDENTITY.scaled(Vector3.ONE*.46),Vector3.ZERO))
    fish.multimesh=mesh
    var material:ShaderMaterial=tank.skin.material.duplicate()
    material.set_shader_parameter("shark_center",Vector3(100,100,100))
    material.set_shader_parameter("clock",1.5)
    fish.material_override=material
    root.add_child(fish)
    for fine in 2:
        for phase:float in [.1,.4,.8]:
            mesh.set_instance_custom_data(0,Color(.35,.58,phase,.4))
            mesh.mesh=tank.skin.meshes[fine]
            material.set_shader_parameter("coarse_mix",1.)
            var before:=await capture()
            mesh.mesh=tank.skin.meshes[fine+1]
            material.set_shader_parameter("coarse_mix",0.)
            var after:=await capture()
            if phase==.4:
                for arg in OS.get_cmdline_user_args():
                    if arg.begins_with("--output="):
                        var base:=arg.trim_prefix("--output=")+"/lod-"+str(fine)
                        before.save_png(base+"-before.png")
                        after.save_png(base+"-after.png")
            var silhouette_diff:=0
            var colour_diff:=0
            var coverage:=0
            for y in before.get_height():
                for x in before.get_width():
                    var a:=before.get_pixel(x,y)
                    var b:=after.get_pixel(x,y)
                    if maxf(a.a,b.a)<.5: continue
                    coverage+=1
                    if absf(a.a-b.a)>.5: silhouette_diff+=1
                    if maxf(absf(a.r-b.r),maxf(absf(a.g-b.g),absf(a.b-b.b)))>.07: colour_diff+=1
            print("CROAKER_LOD level=",fine," phase=",phase," pixels=",coverage," silhouette_diff=",silhouette_diff," colour_diff=",colour_diff)
            ok=ok and coverage>1000 and silhouette_diff<coverage*.007 and colour_diff<coverage*.025
    var folder:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--wheel="): folder=arg.trim_prefix("--wheel=")
    ok=await wheel_sweep(tank,camera,fish,folder) and ok
    quit(0 if ok else 1)

## Flood transparent regions with 4-connectivity. Only fully enclosed regions
## count as holes; clear water bordering the silhouette is expected.
func coverage(image:Image) -> Vector2i:
    var bounds:=image.get_used_rect()
    if not bounds.has_area(): return Vector2i.ZERO
    var crop:=image.get_region(bounds)
    crop.convert(Image.FORMAT_RGBA8)
    var pixels:=crop.get_data()
    var width:=crop.get_width()
    var height:=crop.get_height()
    var flags:=PackedByteArray()
    flags.resize(width*height)
    var solid:=0
    for i in flags.size():
        flags[i]=int(pixels[i*4+3]>=128)
        solid+=flags[i]
    var queue:=PackedInt32Array()
    queue.resize(flags.size())
    var largest:=0
    for i in flags.size():
        if flags[i]!=0: continue
        queue[0]=i
        flags[i]=1
        var head:=0
        var count:=1
        var edge:=false
        while head<count:
            var at:=queue[head]
            head+=1
            var x:=at%width
            var y:=at/width
            if x==0 or x==width-1 or y==0 or y==height-1: edge=true
            for n:int in [at-1 if x>0 else -1,at+1 if x+1<width else -1,at-width,at+width]:
                if n<0 or n>=flags.size() or flags[n]!=0: continue
                flags[n]=1
                queue[count]=n
                count+=1
        if not edge: largest=maxi(largest,count)
    return Vector2i(solid,largest)

## Isolate the selected ID from the actual scene's two draw buffers. Orthographic
## magnification keeps even the distant fish large enough to see an empty texel.
func wheel_sweep(tank,camera:Camera3D,base:MultiMeshInstance3D,folder:String) -> bool:
    tank.enter_school()
    tank.focus_distance=32.
    tank._follow()
    var school:Dictionary=tank.schools[tank.focused]
    var subject:int=tank.focus_member
    var detail:=base.duplicate() as MultiMeshInstance3D
    detail.multimesh=base.multimesh.duplicate()
    root.add_child(detail)
    camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    camera.size=1.40
    var wheel:=InputEventMouseButton.new()
    wheel.pressed=true
    var levels:Dictionary={}
    var min_pixels:=2147483647
    var largest_gap:=0
    for frame in 160:
        if frame%2==0:
            wheel.button_index=MOUSE_BUTTON_WHEEL_UP if frame<42 or frame>=106 else MOUSE_BUTTON_WHEEL_DOWN
            tank._unhandled_input(wheel)
        tank._process(1./30.)
        camera.transform=tank.camera.transform
        var node:MultiMeshInstance3D=school.node
        var xf:=node.multimesh.get_instance_transform(subject)
        var traits:=node.multimesh.get_instance_custom_data(subject)
        base.transform=node.transform
        base.multimesh.mesh=node.multimesh.mesh
        base.multimesh.set_instance_transform(0,xf)
        base.multimesh.set_instance_custom_data(0,traits)
        base.material_override=node.material_override
        detail.visible=false
        if school.detail and school.detail.visible:
            var batch:MultiMesh=school.detail.multimesh
            for i in batch.visible_instance_count:
                var item:=batch.get_instance_transform(i)
                if item.origin.distance_squared_to(xf.origin)>.000001: continue
                detail.transform=node.transform
                detail.multimesh.mesh=batch.mesh
                detail.multimesh.set_instance_transform(0,item)
                detail.multimesh.set_instance_custom_data(0,batch.get_instance_custom_data(i))
                detail.material_override=school.detail.material_override
                detail.visible=true
                break
        levels[school.level]=true
        var shot:=await capture()
        var measured:=coverage(shot)
        min_pixels=mini(min_pixels,measured.x)
        largest_gap=maxi(largest_gap,measured.y)
        if not folder.is_empty(): shot.save_png(folder+"/wheel-%03d.png"%frame)
    print("CROAKER_WHEEL sampled=",160," levels=",levels.keys()," subject=",int(school.first_id)+subject," min_pixels=",min_pixels," largest_enclosed_gap=",largest_gap)
    return levels.size()==3 and min_pixels>1000 and largest_gap<=16
