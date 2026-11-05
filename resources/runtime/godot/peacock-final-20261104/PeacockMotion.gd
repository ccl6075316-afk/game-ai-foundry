extends "res://scripts/aquarium/FoundryFishMotion.gd"
## Species-only normal motion wrapper. No geometry/material/static construction.
## Preserves the original peacock exhibit's18degree jaw controller and amount1.
var jaw_controller
var jaw_amount := 1.0

func configure(carrier: Node3D, model: Node3D, player: AnimationPlayer, skeleton: Skeleton3D, profile: Dictionary, tank_origin: Vector3 = Vector3.ZERO) -> Dictionary:
	jaw_controller=null
	var result: Dictionary = super.configure(carrier,model,player,skeleton,profile,tank_origin)
	if not result.get("ok",false):return result
	jaw_controller=load("res://scripts/aquarium/FoundryJawMotion.gd").new()
	jaw_controller.configure(skeleton,18.0)
	set_jaw_amount(float(profile.get("jaw_open_amount",1.0)))
	result["jaw"]={"bone":"jaw_lower","maximum_degrees":18.0,"amount":jaw_amount,"normal_runtime_only":true}
	return result

func set_jaw_amount(amount: float) -> void:
	assert(is_finite(amount))
	jaw_amount=clampf(amount,0.0,1.0)
	if jaw_controller!=null:jaw_controller.apply(jaw_amount)

func seek(seconds: float) -> void:
	super.seek(seconds)
	if jaw_controller!=null:jaw_controller.apply(jaw_amount)

func step(delta: float) -> void:
	super.step(delta)
	if jaw_controller!=null:jaw_controller.apply(jaw_amount)

func snapshot() -> Dictionary:
	var result: Dictionary=super.snapshot()
	result["jaw_control"]={"bone":"jaw_lower","maximum_degrees":18.0,"amount":jaw_amount,"configured":jaw_controller!=null,"single_runtime_wrapper":true}
	return result
