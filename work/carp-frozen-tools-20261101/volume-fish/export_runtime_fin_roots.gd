extends SceneTree
# Run against the game project with -- plan.json output-directory [before|after].
var plan: Dictionary
var out: String
var variant: String
var surfaces: Array
var faces: Array
var samples: Array
var export_membranes := false
const PACKED_PARTS = preload("PackedFishValidation.gd")
func _initialize() -> void:call_deferred("run")
func save_json(path: String, value: Variant) -> void:
    var f=FileAccess.open(path,FileAccess.WRITE);assert(f!=null,path);f.store_string(JSON.stringify(value));f.close()
func prepare(entry: Dictionary, spec: Dictionary) -> void:
    surfaces=[];faces=[];var offset=0;var found={};var s: Skeleton3D=entry.skeleton
    var logical: Dictionary=PACKED_PARTS.surfaces(entry,spec)
    if logical.packed:entry["packed_partition_proof"]=logical.proof
    for source in logical.surfaces:
        var node: MeshInstance3D=source.mesh
        var name: String=source.name;var is_body=name==spec.body
        for token in ["Dorsal","Anal","Caudal","Pectoral","Pelvic","Tail_Fin","Adipose"]:
            assert(not (token in name) or spec.fins.has(name),"Fin omitted from completion gate: "+spec.species+"/"+name)
        if not is_body and not spec.fins.has(name):continue
        found[name]=true;var bindings: Array[int]=[]
        for j in node.skin.get_bind_count():
            var index=node.skin.get_bind_bone(j)
            if index<0:index=s.find_bone(node.skin.get_bind_name(j))
            assert(index>=0);bindings.append(index)
        var a: Array=source.arrays;var vertices: PackedVector3Array=a[Mesh.ARRAY_VERTEX];var joints: PackedInt32Array=a[Mesh.ARRAY_BONES];var weights: PackedFloat32Array=a[Mesh.ARRAY_WEIGHTS];var triangles: PackedInt32Array=a[Mesh.ARRAY_INDEX];var count: int=joints.size()/vertices.size();var ids: Array[int]=[];var edges: Array=[]
        if is_body:
            for i in range(0,triangles.size(),3):faces.append([offset+triangles[i],offset+triangles[i+1],offset+triangles[i+2]])
            offset+=vertices.size()
        else:
            var radius: float=float(spec.length_native)*.00002
            var root_cells: Dictionary={}
            for raw in spec.fins[name].rest_points_gltf:
                var p=Vector3(raw[0],raw[1],raw[2]);var key=Vector3i((p/radius).floor())
                if not root_cells.has(key):root_cells[key]=[]
                root_cells[key].append(p)
            var transforms: Array[Transform3D]=[]
            for j in bindings.size():transforms.append(s.global_transform*s.get_bone_global_rest(bindings[j])*node.skin.get_bind_pose(j))
            var selected={}
            for i in vertices.size():
                var point=Vector3.ZERO
                for j in count:
                    var at=i*count+j
                    point+=(transforms[joints[at]]*vertices[i])*weights[at]
                var cell=Vector3i((point/radius).floor());var matched=false
                for dx in [-1,0,1]:
                    for dy in [-1,0,1]:
                        for dz in [-1,0,1]:
                            for p in root_cells.get(cell+Vector3i(dx,dy,dz),[]):
                                if point.distance_to(p)<radius:matched=true;break
                if matched:ids.append(i);selected[i]=true
            var seen={}
            for i in range(0,triangles.size(),3):
                for pair in [[triangles[i],triangles[i+1]],[triangles[i+1],triangles[i+2]],[triangles[i+2],triangles[i]]]:
                    var key="%d:%d"%[mini(pair[0],pair[1]),maxi(pair[0],pair[1])]
                    if selected.has(pair[0]) and selected.has(pair[1]) and not seen.has(key):edges.append(pair);seen[key]=true
            assert(not ids.is_empty(),"Unmapped basal selection: "+spec.species+"/"+name)
        surfaces.append({"name":name,"body":is_body,"mesh":node,"vertices":vertices,"joints":joints,"weights":weights,"triangles":triangles,"bindings":bindings,"count":count,"ids":ids,"edges":edges})
    assert(found.size()==spec.fins.size()+1,"Incomplete fin inventory "+spec.species)

func sample(entry: Dictionary, label: String, seconds: float) -> void:
    if variant=="diagnostic" and label!="Static" and not (label in ["Native","Range:WideFast","Clearance:Independent"] and is_equal_approx(seconds,3.75)):return
    var s: Skeleton3D=entry.skeleton;s.force_update_all_bone_transforms();var relative: Transform3D=entry.carrier.global_transform.affine_inverse()*s.global_transform;var body: Array=[];var roots={};var membranes={}
    for surface in surfaces:
        var transforms: Array[Transform3D]=[]
        for j in surface.bindings.size():transforms.append(relative*s.get_bone_global_pose(surface.bindings[j])*surface.mesh.skin.get_bind_pose(j))
        var coords: Array[Vector3]=[]
        for i in surface.vertices.size():
            var point=Vector3.ZERO
            for j in surface.count:
                var at: int=i*int(surface.count)+j
                point+=(transforms[surface.joints[at]]*surface.vertices[i])*surface.weights[at]
            coords.append(point)
        if surface.body:
            for p in coords:body.append([p.x,p.y,p.z])
        else:
            if export_membranes:
                var membrane_points: Array=[]
                for p in coords:membrane_points.append([p.x,p.y,p.z])
                var triangles: PackedInt32Array=surface.triangles
                membranes[surface.name]={"vertices_m":membrane_points,"triangles":Array(triangles)}
            var points: Array=[]
            for i in surface.ids:
                var p: Vector3=coords[i];points.append([p.x,p.y,p.z])
            for edge in surface.edges:
                for k in [1,2,3,4,5,6,7]:
                    var p: Vector3=coords[edge[0]].lerp(coords[edge[1]],float(k)/8.);points.append([p.x,p.y,p.z])
            roots[surface.name]={"vertex_count":surface.ids.size(),"edge_count":surface.edges.size(),"points_m":points}
    var filename=out+"/sample-%03d.json"%samples.size();var data={"body_vertices_m":body,"body_triangles":faces,"roots":roots}
    if export_membranes:data["membranes"]=membranes
    save_json(filename,data);samples.append({"action":label,"seconds":seconds,"posed_mesh_json":filename,"sha256":FileAccess.get_sha256(filename)})
func run() -> void:
    var args=OS.get_cmdline_user_args();assert(args.size()>=3);plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var root_out=args[1];variant=args[2]
    export_membranes="--membranes" in args
    var profiles: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    for spec in plan.items:
        if args.size()>3 and args[3]!="--membranes" and spec.species!=args[3]:continue
        var path: String=spec.model;out=root_out+"/"+spec.species;DirAccess.make_dir_recursive_absolute(out);samples=[]
        var carrier=Node3D.new();root.add_child(carrier);var model: Node3D
        var resource_path=ProjectSettings.localize_path(path.replace("\\","/"))
        if resource_path.begins_with("res://"):
            # Installed assets use precisely the imported resource the game loads.
            var packed=load(resource_path) as PackedScene;assert(packed!=null);model=packed.instantiate()
        else:
            var document=GLTFDocument.new();var state=GLTFState.new();assert(document.append_from_file(path,state)==OK);model=document.generate_scene(state)
        carrier.add_child(model)
        var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0];var player=model.find_children("*","AnimationPlayer",true,false)[0];player.stop();skeleton.reset_bone_poses();skeleton.force_update_all_bone_transforms()
        var entry={"carrier":carrier,"model":model,"skeleton":skeleton,"player":player};prepare(entry,spec)
        var profile: Dictionary=profiles[spec.species];model.scale=Vector3.ONE*float(profile.real_length_cm)/100./float(spec.length_native)
        sample(entry,"Static",0.)
        if export_membranes:
            player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
            player.play(profile.base_clip)
            var native_clip: Animation=player.get_animation(profile.base_clip)
            for phase in 25:
                var native_time:=native_clip.length*float(phase)/25.
                player.seek(native_time,true);player.advance(0.);sample(entry,"Native",native_time)
            player.stop();skeleton.reset_bone_poses();skeleton.force_update_all_bone_transforms()
        var controller=load("res://scripts/aquarium/FoundryFishMotion.gd").new();assert(controller.configure(carrier,model,player,skeleton,profile).ok);entry.controller=controller
        for action in ["Swim","Turn","Ascend","Dive"]:
            controller.set_action(action,true);controller.step(0.)
            for phase in 16:
                var t=float(profile.period_seconds)*float(phase)/16.;controller.seek(t);sample(entry,action,t)
        for target in ["Turn","Ascend","Dive","Swim"]:
            controller.set_action(target,false)
            for k in 4:
                controller.step(float(profile.transition_seconds)/4.);sample(entry,"Transition:"+target,float(k+1)*float(profile.transition_seconds)/4.)
        var ranges: Dictionary={"Neutral":[0.,0.,0.,0.],"WideSlow":[2.5,.35,2.5,.35],"WideFast":[2.5,3.,2.5,3.],"FinsOnly":[0.,0.,2.5,3.],"BodyOnly":[2.5,3.,0.,0.]}
        for label in ranges:
            var v: Array=ranges[label]
            controller.set_motion_controls({"body_amplitude":v[0],"body_frequency":v[1],"fin_amplitude":v[2],"fin_frequency":v[3]},true)
            for phase in 16:
                var t=float(profile.period_seconds)*float(phase)/16.;controller.seek(t);sample(entry,"Range:"+label,t)
        for target in ["Neutral","WideSlow","WideFast","FinsOnly"]:
            var v: Array=ranges[target]
            controller.set_motion_controls({"body_amplitude":v[0],"body_frequency":v[1],"fin_amplitude":v[2],"fin_frequency":v[3]})
            for k in 4:
                controller.step(.125);sample(entry,"RangeTransition:"+target,float(k+1)*.125)
        if export_membranes:
            var mixes: Dictionary={"MixedLow":[.5,.7,.5,1.3],"MixedMid":[1.5,1.3,1.25,.7],"Independent":[2.5,3.,.3,.35],"MaxDense":[2.5,3.,2.5,3.]}
            for label in mixes:
                var v: Array=mixes[label]
                controller.set_motion_controls({"body_amplitude":v[0],"body_frequency":v[1],"fin_amplitude":v[2],"fin_frequency":v[3]},true)
                for phase in 64:
                    var t=float(profile.period_seconds)*float(phase)/64.;controller.seek(t);sample(entry,"Clearance:"+label,t)
            for k in 32:
                var fraction:=float(k)/31.
                controller.set_motion_controls({"body_amplitude":2.5*(1.-fraction),"body_frequency":.35+2.65*fraction,"fin_amplitude":2.5*fraction,"fin_frequency":3.-2.65*fraction})
                controller.step(.0625);sample(entry,"Clearance:ControlSweep",float(k+1)*.0625)
        var report={"ok":true,"model":path,"model_sha256":FileAccess.get_sha256(path),"selection":"Frozen explicit full basal bands and source basal polylines; seven points per root edge","expected_fins":spec.fins.keys(),"controller_source":"res://scripts/aquarium/FoundryFishMotion.gd","controller_sha256":FileAccess.get_sha256("res://scripts/aquarium/FoundryFishMotion.gd"),"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"export_script_sha256":FileAccess.get_sha256(get_script().resource_path),"engine_version":Engine.get_version_info().string,"sample_limit":"Static rest;16 samples per four actions;four samples per four consecutive transitions. Unsampled instants are not certified.","body_triangles":faces.size(),"samples":samples}
        if entry.has("packed_partition_proof"):
            report["packed_partition_proof"]=entry.packed_partition_proof
            report["packed_parts_manifest_sha256"]=FileAccess.get_sha256(spec.packed_parts_manifest)
            report["packed_helper_sha256"]=FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("PackedFishValidation.gd"))
        report["motion_range_revision"]=1
        if export_membranes:
            report["fin_membrane_revision"]=1
            report["sample_limit"]="490 discrete poses: original 177, native clip 25, four dense independent control mixes 256, control sweep 32. Full fin surfaces exported; not continuous proof."
        if not export_membranes:report["sample_limit"]="81 baseline poses plus 80 independent amplitude/frequency range poses and 16 range transitions; 177 discrete poses, not continuous proof."
        if variant=="diagnostic":report["sample_limit"]="Diagnostic subset only; not a delivery gate.";report["diagnostic_only"]=true
        save_json(out+"/export.validation.json",report);print("FIN_EXPORT_DONE ",spec.species," ",samples.size());carrier.queue_free();await process_frame
    quit()
