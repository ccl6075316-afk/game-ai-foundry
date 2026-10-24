extends Node
## Plays the exported native skeletal clips on a shared gentle current clock.
var running := true
var current_time := 0.0
var duration := 10.0
var players: Array=[]
var models: Dictionary={}
var probes: Array=[]
var failures: Array=[]

func attach(id: String, model: Node3D) -> void:
    models[id]=model
    var found := false
    for player in model.find_children("*","AnimationPlayer",true,false):
        for clip in player.get_animation_list():
            if not String(clip).ends_with("WaterSway"):continue
            var animation: Animation=player.get_animation(clip)
            animation.loop_mode=Animation.LOOP_LINEAR
            duration=animation.length
            player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
            player.play(clip)
            player.advance(0)
            players.append(player)
            found=true
    if not found:failures.append(id+": missing native WaterSway animation")
    _collect_probes(id,model)

func _process(delta: float) -> void:
    if running:apply_at(current_time+delta)

func apply_at(seconds: float) -> void:
    current_time=fposmod(seconds,duration)
    for player in players:
        player.seek(current_time,true)
        player.advance(0)

func _collect_probes(id: String, model: Node3D) -> void:
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        var skeleton: Skeleton3D=mesh.get_node_or_null(mesh.skeleton) as Skeleton3D
        if skeleton==null or mesh.skin==null:
            failures.append(id+"/"+mesh.name+": missing native skeleton/skin")
            continue
        var leaf: bool=String(mesh.name).begins_with("traced_leaf_")
        for surface in mesh.mesh.get_surface_count():
            var a: Array=mesh.mesh.surface_get_arrays(surface)
            var vertices: PackedVector3Array=a[Mesh.ARRAY_VERTEX]
            var uv: PackedVector2Array=a[Mesh.ARRAY_TEX_UV]
            var joints: PackedInt32Array=a[Mesh.ARRAY_BONES]
            var weights: PackedFloat32Array=a[Mesh.ARRAY_WEIGHTS]
            if joints.is_empty() or weights.is_empty():
                failures.append(id+"/"+mesh.name+": missing imported weights")
                continue
            for anchor in [true,false]:
                if not leaf and not anchor:continue
                var candidates: Array=[]
                for i in vertices.size():
                    var t: float=1.0-uv[i].y
                    if (anchor and (not leaf or t<=.080001)) or (not anchor and t>.90):candidates.append(i)
                if candidates.is_empty():
                    failures.append(id+"/"+mesh.name+": empty root or tip region")
                    continue
                var count: int=mini(5,candidates.size())
                for sample_index in count:
                    var index: int=candidates[int(sample_index*(candidates.size()-1)/maxi(1,count-1))]
                    var influence_count: int=joints.size()/vertices.size()
                    var binds: Array=[]
                    for k in influence_count:
                        var w: float=weights[index*influence_count+k]
                        if w<=0:continue
                        var bind: int=joints[index*influence_count+k]
                        var bone: int=mesh.skin.get_bind_bone(bind)
                        if bone<0:bone=skeleton.find_bone(mesh.skin.get_bind_name(bind))
                        if bone<0:
                            failures.append(id+": unresolved bind bone")
                            continue
                        binds.append({"bone":bone,"weight":w,"inverse":mesh.skin.get_bind_pose(bind)})
                    probes.append({"id":id,"mesh":String(mesh.name),"anchor":anchor,"skeleton":skeleton,"vertex":vertices[index],"binds":binds})

func sample_probes() -> Array:
    var samples: Array=[]
    for probe in probes:
        var point := Vector3.ZERO
        var skeleton: Skeleton3D=probe.skeleton
        for bind in probe.binds:
            point+=(skeleton.global_transform*skeleton.get_bone_global_pose(bind.bone)*bind.inverse*probe.vertex)*bind.weight
        samples.append({"id":probe.id,"mesh":probe.mesh,"anchor":probe.anchor,"position":[point.x,point.y,point.z]})
    return samples

func rig_summary() -> Dictionary:
    var summary: Dictionary={}
    for id in models:
        var bones := 0
        for skeleton in models[id].find_children("*","Skeleton3D",true,false):bones+=skeleton.get_bone_count()
        summary[id]={"bones":bones,"probes":probes.filter(func(p):return p.id==id).size()}
    return summary
