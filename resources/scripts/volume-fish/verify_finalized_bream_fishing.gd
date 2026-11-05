extends SceneTree
var result={"kind":"canonical_finalized_bream_fishing_route","ok":false,"checks":[],"fish":[],"fresh_process":true,"runtime_static_build_calls":0}
func ck(value:bool,label:String):result.checks.append({"ok":value,"check":label})
func static_digest(model):
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256)
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        for surface in mesh.mesh.get_surface_count():h.update(var_to_bytes(mesh.mesh.surface_get_arrays(surface)))
    return h.finish().hex_encode()
func _initialize():
    create_timer(20).timeout.connect(func():quit(2))
    call_deferred("run")
func run():
    var helper=load("res://scripts/aquarium/FinalizedWidthBatch20261101.gd").new()
    var actor_script=load("res://scripts/screens/FishingVolumeFish.gd")
    for species in ["red_seabream","black_seabream"]:
        var actor=actor_script.new();root.add_child(actor)
        var configured=actor.configure(species);ck(configured and actor.ready_model,species+" actual Fishing configure")
        if not configured:continue
        var row=helper.table()[species];var recipe=helper.mouth_recipe(species)
        ck(actor.controller.get_script().resource_path==row.motion_runtime,species+" canonical controller")
        ck(absf(actor.model.scale.x-float(row.model_scale))<.000001,species+" reviewed source scale")
        ck(actor.model.find_children("*","Skeleton3D",true,false).size()==1 and actor.model.find_children("*","AnimationPlayer",true,false).size()==1,species+" one rig/player")
        var inventory=actor.model.get_meta("final_width20261101_receipt")
        ck(inventory.runtime_static_build_calls==0 and inventory.static_builders_disabled,species+" exact finalizer no builders")
        ck(str(actor.mouth_mesh.name)==recipe.mesh,species+" actual body-owned packed lip mesh")
        var expected=Vector3(recipe.position_native[0],recipe.position_native[1],recipe.position_native[2]);ck(actor.mouth_vertex.distance_to(expected)<.0000001,species+" exact imported lip point")
        var before=static_digest(actor.model);var poses=[]
        for action in ["Swim","Turn","Ascend","Dive"]:
            actor.animate(.25,action);actor.skeleton.force_update_all_bone_transforms()
            var point=actor.mouth_world();ck(point.is_finite(),species+" real skinned lip "+action)
            ck(actor.carrier.transform.is_equal_approx(Transform3D.IDENTITY),species+" fishing owns world transform "+action)
            poses.append({"action":action,"position":[point.x,point.y,point.z]})
        ck(before==static_digest(actor.model),species+" actions retain static geometry/UV/skin")
        var hook=Vector3(.1,.3,.2);actor.place_hook(hook,Vector3.LEFT);ck(actor.mouth_world().distance_to(hook)<.00001,species+" actual lip hook placement")
        result.fish.append({"species":species,"model_sha256":row.model_sha256,"recipe_sha256":row.mouth_recipe.sha256,"inventory":inventory,"poses":poses});actor.free()
    result.ok=result.fish.size()==2 and result.checks.all(func(row):return row.ok)
    var f=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);f.store_string(JSON.stringify(result,"  "));f.close();print("BREAM_ROUTE ",result.ok," checks=",result.checks.size());quit(0 if result.ok else 1)
