extends SceneTree
## Read-only QA: actual exhibit controller, actual imported GLB skin matrices.
## --model /abs/fish.glb --output /private/tmp/skin-export --projected true|false
## Export posed body triangles + fin-root points; check with Blender BVH companion.
var model_path := ""
var target_species := "blacktip_reef_shark"
var out := "/private/tmp/shark-skin-export"
var projected := false
var cached: Array = []
var exhibit
var surfaces: Array = []
var body_triangles: Array = []
var report := {"schema_version":1,"command":"volume.fin.export-runtime-skin","stage":"validate","status":"done","next_action":"human_review","ok":true,"failures":[],"samples":[]}

func _initialize() -> void:
    var args := OS.get_cmdline_user_args()
    for i in range(0,args.size(),2):
        match args[i]:
            "--model": model_path=args[i+1]
            "--species": target_species=args[i+1]
            "--output": out=args[i+1]
            "--projected": projected=args[i+1]=="true"
            _: assert(false,"Unknown option")
    assert(FileAccess.file_exists(model_path))
    call_deferred("run")

func cache_model(path: String, target: String) -> void:
    var document := GLTFDocument.new()
    var state := GLTFState.new()
    assert(document.append_from_file(path,state)==OK)
    var instance := document.generate_scene(state)
    var packed := PackedScene.new()
    assert(packed.pack(instance)==OK)
    packed.take_over_path(target)
    cached.append(packed)
    instance.free()

func prepare_surfaces(entry: Dictionary) -> void:
    var skeleton: Skeleton3D=entry.skeleton
    var body_offset := 0
    for node in entry.model.find_children("*","MeshInstance3D",true,false):
        var mesh := node as MeshInstance3D
        var is_body := str(mesh.name).begins_with("Closed_body")
        var is_fin := str(mesh.name).begins_with("Pectoral_") or str(mesh.name).begins_with("Pelvic_")
        if not is_body and not is_fin:continue
        var bind_bones: Array[int]=[]
        for bind in mesh.skin.get_bind_count():
            var index := mesh.skin.get_bind_bone(bind)
            if index<0:index=skeleton.find_bone(mesh.skin.get_bind_name(bind))
            assert(index>=0)
            bind_bones.append(index)
        var own_fin_bone := skeleton.find_bone(str(mesh.name))
        if is_fin and own_fin_bone<0:
            for bone in skeleton.get_bone_count():
                var bone_name: String=skeleton.get_bone_name(bone)
                if bone_name.begins_with(str(mesh.name)+"_") and bone_name.trim_prefix(str(mesh.name)+"_").is_valid_int():
                    own_fin_bone=bone;break
        for surface in mesh.mesh.get_surface_count():
            var arrays := mesh.mesh.surface_get_arrays(surface)
            var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
            var joints: PackedInt32Array=arrays[Mesh.ARRAY_BONES]
            var weights: PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS]
            var triangles: PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
            var influences: int=joints.size()/vertices.size()
            var ids: Array[int]=[]
            if is_body:
                for i in range(0,triangles.size(),3):
                    body_triangles.append([body_offset+triangles[i],body_offset+triangles[i+1],body_offset+triangles[i+2]])
                body_offset+=vertices.size()
            else:
                assert(own_fin_bone>=0)
                for i in vertices.size():
                    var fin_weight := 0.0
                    for j in influences:
                        if bind_bones[joints[i*influences+j]]==own_fin_bone:
                            fin_weight+=weights[i*influences+j]
                    # Legacy own-fin weight is t; projected root-band weight is exactly zero.
                    if fin_weight<=(0.0000001 if projected else 0.050001):ids.append(i)
                assert(not ids.is_empty(),"No root skin vertices "+str(mesh.name))
            var edges: Array=[]
            if is_fin:
                var idmap: Dictionary={}
                for i in ids:idmap[i]=true
                var seen: Dictionary={}
                for i in range(0,triangles.size(),3):
                    for pair in [[triangles[i],triangles[i+1]],[triangles[i+1],triangles[i+2]],[triangles[i+2],triangles[i]]]:
                        var key: String="%d:%d"%[mini(pair[0],pair[1]),maxi(pair[0],pair[1])]
                        if idmap.has(pair[0]) and idmap.has(pair[1]) and not seen.has(key):
                            edges.append(pair);seen[key]=true
            surfaces.append({"name":str(mesh.name),"mesh":mesh,"vertices":vertices,"joints":joints,"weights":weights,"triangles":triangles,"influences":influences,"bind_bones":bind_bones,"is_body":is_body,"ids":ids,"edges":edges})

func sample_skin(entry: Dictionary, label: String, seconds: float) -> void:
    var skeleton: Skeleton3D=entry.skeleton
    skeleton.force_update_all_bone_transforms()
    var skeleton_to_carrier: Transform3D=entry.carrier.global_transform.affine_inverse()*skeleton.global_transform
    var body: Array=[]
    var roots: Dictionary={}
    for surface in surfaces:
        var transforms: Array[Transform3D]=[]
        for bind in surface.bind_bones.size():
            transforms.append(skeleton_to_carrier*skeleton.get_bone_global_pose(surface.bind_bones[bind])*surface.mesh.skin.get_bind_pose(bind))
        var coords: Array[Vector3]=[]
        for i in surface.vertices.size():
            var point := Vector3.ZERO
            for j in int(surface.influences):
                var at: int=i*int(surface.influences)+j
                var weight: float=surface.weights[at]
                if weight>0.0:point+=(transforms[surface.joints[at]]*surface.vertices[i])*weight
            coords.append(point)
        if surface.is_body:
            for point in coords:body.append([point.x,point.y,point.z])
        else:
            var points: Array=[]
            for i in surface.ids:
                var point: Vector3=coords[i]
                points.append([point.x,point.y,point.z])
            for edge in surface.edges:
                for k in [1,2,3]:
                    var point: Vector3=coords[edge[0]].lerp(coords[edge[1]],float(k)/4.0)
                    points.append([point.x,point.y,point.z])
            roots[surface.name]={"vertex_count":surface.ids.size(),"edge_count":surface.edges.size(),"points_m":points}
    var data := {"action":label,"seconds":seconds,"body_vertices_m":body,"body_triangles":body_triangles,"roots":roots}
    var filename: String=out+"/%s-%04d.json"%[label,int(round(seconds*1000))]
    var file := FileAccess.open(filename,FileAccess.WRITE)
    file.store_string(JSON.stringify(data));file.close()
    report.samples.append({"action":label,"seconds":seconds,"posed_mesh_json":filename,"sha256":FileAccess.get_sha256(filename)})

func run() -> void:
    DirAccess.make_dir_recursive_absolute(out)
    for species in ["blacktip_reef_shark","scalloped_hammerhead","silver_arowana","hairtail","piranha","arapaima"]:
        var target: String="res://assets/models/fish/%s.glb"%species
        cache_model(model_path if species==target_species else target,target)
    exhibit=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(exhibit)
    exhibit.set_process(false);exhibit.paused=true
    exhibit._select_display(target_species)
    await process_frame
    var entry: Dictionary=exhibit._selected()
    prepare_surfaces(entry)
    if surfaces.size()<5:
        push_error("Incomplete skin surfaces");quit(2);return
    for action in ["Swim","Turn","Ascend","Dive"]:
        entry.controller.set_action(action,true);entry.controller.step(0.0)
        for i in 8:
            var seconds: float=float(entry.profile.period_seconds)*float(i)/8.0
            entry.controller.seek(seconds)
            sample_skin(entry,action,seconds)
        print("SKIN_EXPORTED ",action)
    report["species"]=target_species
    report["model"]=model_path
    report["model_sha256"]=FileAccess.get_sha256(model_path)
    report["selection"]="Own-fin bone weight exactly0 for projected root band" if projected else "Own-fin bone weight<=.05 for legacy source t<=.05"
    report["cm_per_export_unit"]=100.0
    report["body_triangles"]=body_triangles.size()
    report["controller_source"]="res://scripts/aquarium/FoundryFishMotion.gd"
    report["controller_sha256"]=FileAccess.get_sha256(report["controller_source"])
    report["exhibit_sha256"]=FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd")
    report["motion_config_sha256"]=FileAccess.get_sha256("res://assets/models/fish/motion/motion.json")
    report["export_script_sha256"]=FileAccess.get_sha256(get_script().resource_path)
    report["engine_version"]=Engine.get_version_info().string
    report["sample_limit"]="Eight equally spaced sample times per action; between-sample contact is not proven."
    var file:=FileAccess.open(out+"/export.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  "));file.close()
    print("SKIN_EXPORT_DONE ",out)
    quit()
