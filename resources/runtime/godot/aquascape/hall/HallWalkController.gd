extends RefCounted
## Live movement only. Editor/mode ownership remains with the host.
static func tick(player: CharacterBody3D,delta: float) -> void:
    var input := Input.get_vector("hall_left","hall_right","hall_forward","hall_back")
    var direction: Vector3=player.basis*Vector3(input.x,0,input.y)
    var speed := 5.0 if Input.is_physical_key_pressed(KEY_SHIFT) else 2.7
    player.velocity.x=direction.x*speed;player.velocity.z=direction.z*speed
    if not player.is_on_floor():player.velocity.y-=18*delta
    else:player.velocity.y=0
    player.move_and_slide()
