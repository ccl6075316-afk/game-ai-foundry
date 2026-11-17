extends RefCounted
## Smooth hammerhead swimming, approach and bite, in native metres.
const STOP := 4.0
const CONTACT := 1.55
const TAKE_END := 2.08
const UPPER := Vector3(.882482767,-.134967908,0.)
const LOWER := Vector3(.87767595,-.13808,0.)
const GATE_AXIS := Vector3(0,1,0)
const DELAYS := [0.,.036,.071,.108,.147,.188,.230,.276]
const BEND_DEG := [11.,16.,20.,15.,4.,-10.,-22.,-28.]
var skeleton: Skeleton3D
var carrier: Node3D
var swim
var head: int
var upper: int
var lower: int
var floor: int
var chain: Array[int]=[]

func bind(root_node: Node3D, skeleton_node: Skeleton3D, controller) -> void:
    carrier=root_node
    skeleton=skeleton_node
    swim=controller
    for id in 8:
        chain.append(skeleton.find_bone("body_%02d"%id))
        assert(chain[-1]>=0)
    head=skeleton.find_bone("feeding_head")
    upper=skeleton.find_bone("jaw_upper")
    lower=skeleton.find_bone("jaw_lower")
    floor=skeleton.find_bone("oral_floor")
    assert(mini(mini(head,upper),mini(lower,floor))>=0)

func blend(t: float, start: float, finish: float) -> float:
    return smoothstep(0.,1.,clampf((t-start)/(finish-start),0.,1.))

func curve(t: float, samples: Array) -> float:
    for i in range(samples.size()-1):
        var pair: Array=samples[i]
        var after: Array=samples[i+1]
        if t<=float(after[0]):
            return lerpf(pair[1],after[1],blend(t,pair[0],after[0]))
    return samples[-1][1]

func travel(t: float, large: bool) -> float:
    # Monotonic Hermite paths have explicit speeds at the phase boundaries.
    var keys := [[0.,-1.02,.40],[.92,-.54,.70],[CONTACT,0.,1.08],[2.13,.52,.84],[STOP,1.85,.64]]
    if large:
        keys=[[0.,-1.01,.40],[.92,-.51,.72],[CONTACT,0.,.58],[2.12,.20,.23],[STOP,.84,.43]]
    for i in range(keys.size()-1):
        var a: Array=keys[i]
        var b: Array=keys[i+1]
        if t<=float(b[0]):
            var dt: float=b[0]-a[0]
            var u:=clampf((t-float(a[0]))/dt,0.,1.)
            return (2.*u*u*u-3.*u*u+1.)*float(a[1])+(u*u*u-2.*u*u+u)*dt*float(a[2])+(-2.*u*u*u+3.*u*u)*float(b[1])+(u*u*u-u*u)*dt*float(b[2])
    return keys[-1][1]

func prey_free(t: float, large: bool) -> Vector3:
    if large:
        return Vector3(.871+.042*(t-CONTACT),-.155+.005*sin((t-CONTACT)*2.),.007*sin((t-CONTACT)*2.6))
    return Vector3(.873+.068*(t-CONTACT),-.154+.012*sin((t-CONTACT)*3.1),.015*sin((t-CONTACT)*3.6))

func bend(t: float) -> float:
    var dt:=t-1.86
    var envelope:=blend(t,1.55,1.80)*(1.-blend(t,2.52,3.33))
    return sin(TAU*(1.28*dt-.12*dt*dt))*envelope

func rotate(id: int, angle: float) -> void:
    var rest:=skeleton.get_bone_rest(id).basis.get_rotation_quaternion()
    skeleton.set_bone_pose_rotation(id,rest*Quaternion(Vector3.UP,deg_to_rad(angle)))

func offset(id: int, delta: Vector3) -> void:
    var parent:=skeleton.get_bone_parent(id)
    var rest:=skeleton.get_bone_rest(id).origin
    skeleton.set_bone_pose_position(id,rest+skeleton.get_bone_global_rest(parent).basis.inverse()*delta)

func point(at: Vector3, id: int) -> Vector3:
    return skeleton.global_transform*(skeleton.get_bone_global_pose(id)*skeleton.get_bone_global_rest(id).affine_inverse()*at)

func oral_frame() -> Dictionary:
    var high:=point(UPPER,upper)
    var low:=point(LOWER,lower)
    var orth:=skeleton.global_basis*skeleton.get_bone_global_pose(head).basis*skeleton.get_bone_global_rest(head).basis.inverse()
    var separation: Vector3=high-low
    var along:=orth.x.normalized()
    var up: Vector3=separation.normalized()
    var crosswise:=-(orth.z-orth.z.dot(up)*up).normalized()
    var lengthwise_up: Vector3=(up-along*along.dot(up)).normalized()
    return {"upper":high,"lower":low,"center":high.lerp(low,.5),"up":up,"gap":separation.length(),
        "crosswise":Basis(crosswise,up,crosswise.cross(up)).orthonormalized(),
        "forward":Basis(along,lengthwise_up,along.cross(lengthwise_up)).orthonormalized()}

func apply(t: float, large: bool) -> Dictionary:
    swim.seek(.64+t)
    carrier.transform=Transform3D.IDENTITY
    var gape := curve(t,[[0.,0.],[.80,0.],[1.14,.29],[1.38,1.],[1.55,.55],[1.79,.66],[1.99,.50],[2.22,0.],[STOP,0.]])
    if large:
        gape=curve(t,[[0.,0.],[.78,0.],[1.14,.22],[1.36,1.],[CONTACT,.65],[1.78,.55],[2.48,.50],[STOP,.46]])
    var protrude := curve(t,[[0.,0.],[1.22,0.],[1.42,.51],[CONTACT,.82],[1.89,.50],[2.23,0.],[STOP,0.]])
    if large:
        protrude=curve(t,[[0.,0.],[1.22,0.],[1.41,.44],[CONTACT,.85],[1.88,.62],[2.63,.52],[STOP,.44]])
    protrude=minf(protrude,5.*gape)
    var lift:=curve(t,[[0.,0.],[.81,0.],[1.38,1.],[1.72,.53],[2.34,.16],[3.14,0.],[STOP,0.]])
    var mix:=blend(t,1.25,1.69)*(1.-blend(t,2.86,3.70))*.81 if large else blend(t,.93,1.34)*(1.-blend(t,1.56,2.25))*.46
    var previous:=0.
    for i in 8:
        var bone:=chain[i]
        var desired:=float(BEND_DEG[i])*bend(t-float(DELAYS[i])) if large else 3.7*sin(float(i)/7.*PI)*blend(t,.69,1.34)*(1.-blend(t,1.52,2.08))
        var rest:=skeleton.get_bone_rest(bone).basis.get_rotation_quaternion()
        var axis:=skeleton.get_bone_global_rest(bone).basis.inverse()*GATE_AXIS
        var goal:=rest*Quaternion(axis.normalized(),deg_to_rad(desired-previous))
        skeleton.set_bone_pose_rotation(bone,skeleton.get_bone_pose_rotation(bone).slerp(goal,mix))
        previous=desired
    # Keep the validated independence of both sibling jaw bones.
    rotate(head,-2.6*lift)
    rotate(lower,28.*gape)
    rotate(upper,2.9*protrude)
    offset(upper,Vector3(.0055,-.0018,0.)*protrude)
    offset(floor,Vector3(.002,-.0065,0.)*gape)
    var heading := curve(t,[[0.,-13.],[.63,-9.],[1.41,-1.],[CONTACT,0.],[2.6,4.],[STOP,3.]])
    if large:
        heading=curve(t,[[0.,-10.],[.78,-6.],[CONTACT,0.],[3.35,-4.],[STOP,-2.]])+bend(t)*7.
    carrier.rotation.y=deg_to_rad(heading)
    skeleton.force_update_all_bone_transforms()
    var close_fraction:=blend(t,1.25,CONTACT)*(1.-blend(t,CONTACT,1.93))
    var expected:=prey_free(CONTACT,large)
    var start_offset:=Vector3(travel(t,large),-.046*(1.-blend(t,0.,1.29)),.27*(1.-blend(t,0.,1.44)))
    var anchor: Vector3=oral_frame().center
    var correction := (expected-anchor)*close_fraction
    carrier.position=start_offset+correction
    skeleton.force_update_all_bone_transforms()
    return {"t":t,"gape":gape,"protrusion":protrude,"head":lift,"bend":bend(t) if large else 0.,
        "travel":travel(t,large),"heading":heading,"blend":mix,"carrier":carrier.position}
