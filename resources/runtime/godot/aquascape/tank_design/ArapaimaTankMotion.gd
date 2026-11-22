extends RefCounted

const Interior = preload("ShellInterior.gd")
const RouteMotion = preload("../fish_school/FishSchoolMotionAdapter.gd")
const Sectors := 64
enum Activity { CRUISE, DESCEND, REST, LEAVE, BREATHE }
var activity := Activity.CRUISE
var age := 0.0
var since_air := 0.0
var angle := 0.0
var floor_height := PackedFloat32Array()
var can_settle := PackedByteArray()
var water := 0.0
var cruising_y := 0.0
var rest_y := 0.0
var lift_from := 0.0
var descent_time := 7.0
var ascent_time := 7.0
var air_leg_time := 5.6
var rig: Dictionary
var motion := RouteMotion.new()
var lip := preload("../../screens/FishingVolumeFish.gd").new()

func setup(display: Dictionary, phase: float, recipe: Dictionary) -> void:
	rig = display
	angle = phase
	age = fposmod(phase,3.0)
	since_air = fposmod(phase,TAU)*0.82
	rig.carrier.add_child(lip)
	lip.bind_upper_lip(rig.model,rig.skeleton,recipe)
	motion.configure(rig.controller,Vector3(-sin(angle),0,cos(angle)))

func sector(a: float) -> int:
	return posmod(roundi(a*Sectors/TAU),Sectors)

# Rebuild when the player edits the tank. Include the whole fish and the arc
# between adjacent samples, so a narrow rock cannot slip between two checks.
func fit(entry: Dictionary, box: Rect2, bed: Dictionary, height: float, decor: Array[Dictionary]) -> void:
	water = Interior.waterline(height)
	var l := float(entry.length)
	var margin := l*0.53 + PI*float(entry.radius)/Sectors
	floor_height.resize(Sectors)
	can_settle.resize(Sectors)
	var highest := 0.0
	for i in Sectors:
		var p := Vector2(entry.center.x,entry.center.z)+Vector2.from_angle(TAU*i/Sectors)*float(entry.radius)
		var lo := ((p-Vector2.ONE*margin-box.position)/box.size*Interior.GRID).floor().clamp(Vector2.ZERO,Vector2.ONE*Interior.GRID)
		var hi := ((p+Vector2.ONE*margin-box.position)/box.size*Interior.GRID).ceil().clamp(Vector2.ZERO,Vector2.ONE*Interior.GRID)
		var top := 0.0
		var bottom := INF
		for z in range(int(lo.y),int(hi.y)+1):
			for x in range(int(lo.x),int(hi.x)+1):
				var y := Interior.floor_y(Vector2(x,z)/Interior.GRID,bed,height)
				top=maxf(top,y)
				bottom=minf(bottom,y)
		var flat := top-bottom <= l*0.003
		for prop in decor:
			var obstacle: AABB = prop.root.transform*prop.bounds
			var footprint := Rect2(obstacle.position.x,obstacle.position.z,obstacle.size.x,obstacle.size.z)
			if p.distance_to(p.clamp(footprint.position,footprint.end)) <= margin:
				top=maxf(top,obstacle.end.y)
				flat=false
		floor_height[i]=top
		can_settle[i]=int(flat)
		highest=maxf(highest,top)
	cruising_y = clampf(lerpf(highest,water,0.48),highest+0.15*l,water-0.15*l)
	if activity in [Activity.DESCEND,Activity.REST]:
		var suitable := can_settle[sector(angle)]!=0 if activity==Activity.REST else landing_clear(entry)
		if not suitable:
			lift_from=rig.carrier.position.y
			ascent_time=vertical_time(cruising_y-lift_from,7.0)
			change(Activity.LEAVE)
		else:
			rest_y=floor_height[sector(angle)]+0.1172*l

func landing_clear(entry: Dictionary) -> bool:
	var first := sector(angle)
	# Reserve the remaining approach and first part of the departure.
	var travel_time := vertical_time(cruising_y-floor_height[first]-0.1172*float(entry.length),7.0)
	var steps := mini(Sectors,ceili(angular_speed(entry)*(travel_time+1.0)*Sectors/TAU)+1)
	for k in range(steps+1):
		var i := (first+k)%Sectors
		if can_settle[i]==0 or absf(floor_height[i]-floor_height[first])>0.003*float(entry.length):
			return false
	return true

func angular_speed(entry: Dictionary) -> float:
	return minf(0.42,0.07*float(entry.length)/maxf(0.01,float(entry.radius)))

func vertical_time(distance: float, minimum: float) -> float:
	return maxf(minimum,absf(distance)/(float(rig.length_m)*0.22))

func change(next: Activity) -> void:
	activity=next
	age=0.0

# The workshop preview has its own display rig. Preserve the live behaviour
# when the same fish passes between it and the saved hall projection.
func resume_from(other) -> void:
	activity=other.activity
	age=other.age
	angle=other.angle
	since_air=other.since_air
	rest_y=other.rest_y
	lift_from=other.lift_from
	descent_time=other.descent_time
	ascent_time=other.ascent_time
	air_leg_time=other.air_leg_time
	motion=RouteMotion.new()
	motion.configure(rig.controller,other.motion.orientation().x.normalized())

func advance(entry: Dictionary, dt: float) -> void:
	age+=dt
	since_air+=dt
	var l := float(entry.length)
	if activity==Activity.CRUISE:
		if since_air>=32.0:
			air_leg_time=vertical_time(water-cruising_y,5.6)
			change(Activity.BREATHE)
		elif age>=5.0 and since_air<18.0 and landing_clear(entry):
			rest_y=floor_height[sector(angle)]+0.1172*l
			descent_time=vertical_time(cruising_y-rest_y,7.0)
			change(Activity.DESCEND)
	elif activity==Activity.DESCEND and age>=descent_time: change(Activity.REST)
	elif activity==Activity.REST and age>=6.0:
		lift_from=rest_y
		ascent_time=vertical_time(cruising_y-lift_from,7.0)
		change(Activity.LEAVE)
	elif activity==Activity.LEAVE and age>=ascent_time: change(Activity.CRUISE)
	elif activity==Activity.BREATHE and age>=air_leg_time*2.0+0.8:
		since_air=0.0
		change(Activity.CRUISE)

	var drive := 1.0
	var still := 0.0
	var pitch := 0.0
	var y := cruising_y
	var surface := 0.0
	var jaw := 0.0
	match activity:
		Activity.DESCEND:
			var u := smoothstep(0.,descent_time,age)
			drive=1.-u
			pitch=-0.44*sin(PI*u)
			still=smoothstep(descent_time-2.5,descent_time,age)
			y=lerpf(cruising_y,rest_y,u)
		Activity.REST:
			y=rest_y
			still=1.
			drive=0.
		Activity.LEAVE:
			var u := smoothstep(0.,ascent_time,age)
			drive=u
			still=1.-smoothstep(0.,2.5,age)
			pitch=0.44*sin(PI*u)
			y=lerpf(lift_from,cruising_y,u)
		Activity.BREATHE:
			var at_water := age-air_leg_time
			surface=smoothstep(0.,air_leg_time,age)-smoothstep(0.5,air_leg_time+0.8,at_water)
			# Lower the body away from the waterline before tipping the nose down.
			pitch=0.28*(smoothstep(0.,3.,age)-smoothstep(0.5,3.0,at_water))
			pitch-=0.24*(smoothstep(2.4,3.8,at_water)-smoothstep(air_leg_time-1.8,air_leg_time+0.8,at_water))
			jaw=0.64*(smoothstep(-0.2,0.15,at_water)-smoothstep(0.45,0.85,at_water))
			drive+=surface
	angle=fposmod(angle+dt*angular_speed(entry)*drive,TAU)
	var tangent := Vector3(-sin(angle)*cos(pitch),sin(pitch),cos(angle)*cos(pitch))
	if dt>0:
		rig.controller.set_motion_controls({"body_amplitude":(0.36+0.4*absf(pitch))*(1.-still),"body_frequency":0.56+absf(pitch),"fin_amplitude":0.43*(1.-still)})
		motion.observe(tangent,dt)
		motion.step(dt)
	var center: Vector3=entry.center
	y=maxf(y,floor_height[sector(angle)]+l*(0.1172+0.50*absf(sin(pitch))))
	rig.carrier.transform=Transform3D(motion.orientation(),Vector3(center.x+entry.radius*cos(angle),y,center.z+entry.radius*sin(angle)))
	if dt>0:
		preload("../individual_swim/ArapaimaPose.gd").apply(rig,still,jaw)
	if surface>0.0:
		var mouth: Vector3=rig.carrier.get_parent().to_local(lip.mouth_world())
		rig.carrier.position.y+=(water-mouth.y)*surface
