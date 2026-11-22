extends SceneTree
var tank
var candidates:=0
var tight:=0
var lowest:=100.
var worst:=[]
var image:Image
var rows:int
var rest_vertices:PackedVector3Array
var near_pairs:=0
var unclear:=0
var projected:=INF
var distant:=false
var full_tank:=false
var cross_school:=0
var sampled_schools:Dictionary={}
var tracked_pair:Array=[]
var previous:Array[Vector3]=[]
var previous_step:Array[Vector3]=[]
var samples_in_pair:=0
var frame_checks:=0
var frame_flags:=0
var worst_step_change:=0.
var worst_step:=[]
func positions(s:Dictionary,i:int) -> PackedVector3Array:
    var xf:Transform3D=s.node.multimesh.get_instance_transform(i)
    var centre:Vector3=tank.member_center(s,i,xf)
    var basis:Basis=s.node.basis*xf.basis
    var color:Color=s.node.multimesh.get_instance_custom_data(i)
    var clock:float=tank.elapsed+s.phase
    var t:=clock*(.82+color.r*.35)
    var phase:=TAU*color.r
    var f:=fposmod(color.b,1.)*16.
    var a:=floori(f)
    var b:=(a+1)%16
    var feed:float=s.influence*minf(tank.feed_time,1.)*(1.-smoothstep(.45,1.6,s.node.to_global(xf.origin).distance_to(tank.food_node.position)))
    var mouth:float=(.5-.5*cos(t*3.55+phase))*lerpf(.42,.96,feed)
    var vertices:=PackedVector3Array()
    for j:int in tank.skin.meshes[0].surface_get_array_len(0):
        var x:=j%256
        var y:=j/256
        var shut:=image.get_pixel(x,y+rows*a*2).lerp(image.get_pixel(x,y+rows*b*2),f-a)
        var open:=image.get_pixel(x,y+rows*(a*2+1)).lerp(image.get_pixel(x,y+rows*(b*2+1)),f-a)
        var rest:=rest_vertices[j]
        var strength:=lerpf(1.,.53+.47*color.g,smoothstep(.16,.47,.49-rest.x))
        var v:=rest.lerp(Vector3(shut.r,shut.g,shut.b),strength)
        v+=Vector3(open.r-shut.r,open.g-shut.g,open.b-shut.b)*mouth
        vertices.append(centre+basis*v)
    return vertices
func check_mesh(a:Dictionary,i:int,b:Dictionary,j:int,n:Vector3):
    if n.is_zero_approx():return
    var lo:=INF
    var hi:=-INF
    for v:Vector3 in positions(a,i):lo=minf(lo,v.dot(n))
    for v:Vector3 in positions(b,j):hi=maxf(hi,v.dot(n))
    projected=minf(projected,lo-hi)
    unclear+=int(lo<=hi)
    near_pairs+=1
func _initialize(): run.call_deferred()
func scan():
    var bins:Dictionary={}
    var nearest:=INF
    var watch:=[]
    # In a fixed overview, inspect the actual poses around schools at depth.
    var centre:Vector3=tank.camera.position
    if distant:
        var school_ids:=[5,18,24,37]
        centre=tank.schools[school_ids[int(tank.elapsed/6.)%4]].node.position
    for s:Dictionary in tank.schools:
        var cam:Vector3=s.node.to_local(centre)
        var food:Vector3=s.node.to_local(tank.food_node.position)
        if not full_tank and cam.length()>16. and (tank.feed_time<=0. or food.length()>16.): continue
        for i in s.slots.size():
            if not full_tank and s.slots[i].distance_to(cam)>3.2 and (tank.feed_time<=0. or s.slots[i].distance_to(food)>2.): continue
            sampled_schools[s.first_id]=true
            var xf:Transform3D=s.node.multimesh.get_instance_transform(i)
            var at:Vector3=tank.member_center(s,i,xf)
            var dir:Vector3=s.node.basis*xf.basis.x
            var key:=Vector3i((at/.72).floor())
            for x in range(-1,2):
                for y in range(-1,2):
                    for z in range(-1,2):
                        for b:Array in bins.get(key+Vector3i(x,y,z),[]):
                            var lengths:float=dir.length()+b[1].length()
                            if at.distance_to(b[0])>lengths*.58:continue
                            var endpoints:=Geometry3D.get_closest_points_between_segments(at-dir*.32,at+dir*.32,b[0]-b[1]*.32,b[0]+b[1]*.32)
                            var gap:=endpoints[0].distance_to(endpoints[1])-lengths*.18
                            if gap<nearest:
                                nearest=gap
                                watch=[s,i,b[3],b[4],(endpoints[0]-endpoints[1]).normalized()]
                            candidates+=1
                            if s!=b[3]:cross_school+=1
                            if gap<0.:tight+=1
                            if gap<lowest:
                                lowest=gap
                                worst=[s.first_id+i,b[2],tank.elapsed]
            if not bins.has(key):bins[key]=[]
            bins[key].append([at,dir,s.first_id+i,s,i])
    if watch.size()>0:check_mesh.callv(watch)
    tracked_pair=watch
    previous.clear()
    previous_step.clear()
    samples_in_pair=0

func follow_encounter():
    if tracked_pair.is_empty(): return
    var centres:Array[Vector3]=[]
    var axes:Array[Vector3]=[]
    for k:int in [0,2]:
        var school:Dictionary=tracked_pair[k]
        var i:int=tracked_pair[k+1]
        var xf:Transform3D=school.node.multimesh.get_instance_transform(i)
        centres.append(tank.member_center(school,i,xf))
        axes.append(school.node.basis*xf.basis.x)
    var closest:=Geometry3D.get_closest_points_between_segments(centres[0]-axes[0]*.32,centres[0]+axes[0]*.32,centres[1]-axes[1]*.32,centres[1]+axes[1]*.32)
    frame_flags+=int(closest[0].distance_to(closest[1])<.18*(axes[0].length()+axes[1].length()))
    frame_checks+=1
    if samples_in_pair>0:
        var step:Array[Vector3]=[centres[0]-previous[0],centres[1]-previous[1]]
        if samples_in_pair>1:
            for k in 2:
                var change:=step[k].distance_to(previous_step[k])
                if change>worst_step_change:
                    worst_step_change=change
                    worst_step=[int(tracked_pair[2*k].first_id)+int(tracked_pair[2*k+1]),tank.elapsed]
        previous_step=step
    previous=centres
    samples_in_pair+=1
func run():
    tank=load("res://scenes/ocean_school_review.tscn").instantiate()
    root.add_child(tank)
    tank.set_process(false)
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--passing="):
            capture_school_passes(arg.trim_prefix("--passing="))
            return
    distant="--distant" in OS.get_cmdline_user_args()
    full_tank="--full-tank" in OS.get_cmdline_user_args()
    image=tank.skin.material.get_shader_parameter('poses').get_image()
    rows=tank.skin.material.get_shader_parameter('rows')
    rest_vertices=tank.skin.meshes[0].surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    var extremes:=[0,0]
    for j in rest_vertices.size():
        if rest_vertices[j].x<rest_vertices[extremes[0]].x:extremes[0]=j
        if rest_vertices[j].x>rest_vertices[extremes[1]].x:extremes[1]=j
    var length:float=rest_vertices[extremes[1]].x-rest_vertices[extremes[0]].x
    for j:int in extremes:
        var extent:=Vector2(INF,-INF)
        for frame in 16:
            var z:=image.get_pixel(j%256,j/256+rows*frame*2).b
            extent=Vector2(minf(extent.x,z),maxf(extent.y,z))
        print("CROAKER_STROKE rest_x=",rest_vertices[j].x," peak_span_fraction=",(extent.y-extent.x)/length)
    var speeds:Array[float]=[]
    var rates:Array[float]=[]
    var ticks:=720 if full_tank else (1440 if distant else 3600)
    for tick in ticks:
        if full_tank and tick==180:
            tank.enter_school()
            tank.feed()
        elif not full_tank and not distant:
            if tick%900==0:tank.enter_school()
            if tick%900==120:tank.feed()
        tank._process(1./60.)
        if tick<120 and tick%12==0:
            for school:Dictionary in tank.schools:
                var velocity:PackedVector3Array=school.flow.GetVelocities()
                for j in range(0,velocity.size(),8):
                    speeds.append(velocity[j].length())
                    var traits:Color=school.node.multimesh.get_instance_custom_data(j)
                    rates.append(1.05+1.12*traits.g)
        if full_tank:
            if tick in [0,120,240,360,480,600,719]:scan()
        elif tick%12==0:scan()
        if samples_in_pair<12:follow_encounter()
        if tick%240==0:await process_frame
    speeds.sort()
    rates.sort()
    print("CROAKER_CRUISE speed_p10_p50_p90_mps=",[speeds[speeds.size()/10],speeds[speeds.size()/2],speeds[speeds.size()*9/10]]," beat_p10_p50_p90_hz=",[rates[rates.size()/10],rates[rates.size()/2],rates[rates.size()*9/10]])
    print("OCEAN_CONTACT full_tank=",full_tank," distant=",distant," candidates=",candidates," cross_school=",cross_school," capsule_flags=",tight," lowest=",lowest," worst=",worst)
    print("OCEAN_MESH samples=",near_pairs," not_separated=",unclear," min_projection_m=",projected)
    print("OCEAN_ENCOUNTER frames=",frame_checks," tight_frames=",frame_flags," maximum_change_in_step_m=",worst_step_change," worst=",worst_step)
    var scans:=7 if full_tank else ticks/12
    # Passing schools may leave metres of clearance. Require coverage of
    # the observed schools; a close cross-school pair is measured separately.
    var coverage_ok:bool=not full_tank or sampled_schools.size()==tank.schools.size()
    if distant: coverage_ok=sampled_schools.size()>=4
    quit(int(unclear>0 or tight>0 or near_pairs!=scans or not coverage_ok or frame_flags>0 or worst_step_change>.012))

## World-space rendered fish centres and forward axes, every half-second.
## Read the scratch files with verify_croaker_shoal_passing.py.
func capture_school_passes(prefix:String) -> void:
    var out:=FileAccess.open(prefix+".bin",FileAccess.WRITE)
    var ids:=FileAccess.open(prefix+".ids",FileAccess.WRITE)
    if not out or not ids:
        quit(2)
        return
    for s in tank.schools: ids.store_line(str(s.slots.size()))
    ids.close()
    for tick in 1351:
        if tick>0: tank._move_animals(1./30.)
        if tick%15!=0: continue
        var values:=PackedVector3Array()
        for s in tank.schools:
            for i in s.slots.size():
                var pose:Transform3D=s.flow.Pose(i)
                values.append(tank.member_center(s,i,pose))
                values.append(s.node.basis*pose.basis.x)
        out.store_buffer(values.to_byte_array())
    out.close()
    quit()
