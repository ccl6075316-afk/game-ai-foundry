extends SceneTree
## Read-only actual-game material/mouth audit. Runtime controls are temporary.
var hall
var out:String
var requested:Array=[]
var ownership:Dictionary
var intrinsic:Dictionary={}
var records:Array=[]
var shaders:Dictionary={}
var starting_bindings:Dictionary={}
func runtime_files(directory:String)->Array:
    var files:Array=[]
    for name in DirAccess.get_files_at(directory):
        if name.get_extension() in ["gd","gdshader","gdshaderinc","json"]:files.append(directory.path_join(name).trim_prefix("res://"))
    for name in DirAccess.get_directories_at(directory):files.append_array(runtime_files(directory.path_join(name)))
    return files
func _initialize():
    var args=OS.get_cmdline_user_args();out=args[0]
    for i in range(1,args.size()):requested.append(args[i])
    call_deferred("run")
func shot(path:String):
    await process_frame
    RenderingServer.force_draw()
    await process_frame
    RenderingServer.force_draw()
    assert(hall.viewport.get_texture().get_image().save_png(path)==OK)
func region(entry:Dictionary)->Dictionary:
    var points:Array[Vector3]=[]
    var inverse:Transform3D=entry.model.global_transform.affine_inverse()
    var excluded:Dictionary=ownership[entry.species].fins
    for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
        if excluded.has(str(mesh.name)) or not intrinsic.get(mesh.get_instance_id(),false):continue
        var tr:Transform3D=inverse*mesh.global_transform
        for surface in mesh.mesh.get_surface_count():
            var vertices:PackedVector3Array=mesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
            for v in vertices:points.append(tr*v)
    assert(not points.is_empty())
    var bounds:=AABB(points[0],Vector3.ZERO)
    for v in points:bounds=bounds.expand(v)
    var start:float=bounds.position.x+bounds.size.x*.80
    var head:=AABB();var first=true
    for v in points:
        if v.x>=start:
            if first:head=AABB(v,Vector3.ZERO);first=false
            else:head=head.expand(v)
    assert(not first)
    var tr:Transform3D=entry.model.global_transform
    var ext:Vector3=head.size*tr.basis.get_scale()
    return {"body":bounds,"head":head,"extent_m":maxf(ext.x,maxf(ext.y,ext.z))}
func camera(entry:Dictionary,r:Dictionary,close:bool,yaw:float,pitch:float):
    var basis:Basis=entry.carrier.global_transform.basis.orthonormalized()
    var center:Vector3=entry.model.global_transform*(r.head.get_center() if close else r.body.get_center())
    var distance:float=maxf(r.extent_m*1.9,entry.length_m*.20) if close else entry.length_m*1.45
    hall.camera.near=.0005
    hall.camera.global_position=center+basis*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*distance
    hall.camera.look_at(center,basis*Vector3.UP)
func unlit(material:Material)->Material:
    var copy:Material=material.duplicate()
    if copy is ShaderMaterial:
        var key:String=material.shader.resource_path
        if not shaders.has(key):
            var shader=Shader.new();var code:String=material.shader.code
            if code.contains("render_mode"):code=code.replace("render_mode","render_mode unshaded,")
            else:code=code.replace("shader_type spatial;","shader_type spatial;\nrender_mode unshaded;")
            shader.code=code;shaders[key]=shader
        copy.shader=shaders[key]
    elif copy is StandardMaterial3D:copy.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    return copy
func set_mode(entry:Dictionary,stored:Array,mode:String):
    for item in stored:
        var mesh:MeshInstance3D=item[0];var surface:int=item[1];var original:Material=item[3]
        if mode=="texture":mesh.set_surface_override_material(surface,item[2]);continue
        if mode=="albedo":mesh.set_surface_override_material(surface,unlit(original));continue
        var clay=StandardMaterial3D.new();clay.albedo_color=Color(.65,.65,.65);clay.roughness=1.;clay.cull_mode=BaseMaterial3D.CULL_DISABLED
        if mode=="ownership":
            clay.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
            var oral:bool=original.resource_name.to_lower().contains("oral")
            if original is ShaderMaterial:oral=oral or original.shader.resource_path.ends_with("FishMouthPigment.gdshader")
            clay.albedo_color=Color(1.,0.,1.) if oral else Color(.75,.75,.75)
        mesh.set_surface_override_material(surface,clay)
func run():
    DirAccess.make_dir_recursive_absolute(out)
    if FileAccess.file_exists("res://scripts/aquarium/BodyChart112.gd"):
        for file in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):starting_bindings[file]=FileAccess.get_sha256("res://"+file)
    root.size=Vector2i(1200,800)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800)
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    if requested.is_empty():requested=hall.SPECIES
    for species in requested:
        assert(species in hall.SPECIES)
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        entry.controller.set_motion_controls({"body_amplitude":0.,"body_frequency":1.,"fin_amplitude":0.,"fin_frequency":1.},true)
        assert(entry.controller.set_action("Swim",true))
        entry.controller.step(0.)
        entry.controller.seek(0.)
        if entry.has("jaw_controller"):entry.jaw_controller.apply(1.)
        await process_frame
        var r:Dictionary=region(entry)
        var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        var stored:Array=[];var material_inventory:Array=[]
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            for surface in mesh.mesh.get_surface_count():
                var material:Material=mesh.get_active_material(surface)
                stored.append([mesh,surface,mesh.get_surface_override_material(surface),material])
                material_inventory.append({"mesh":str(mesh.name),"surface":surface,"visible":intrinsic[mesh.get_instance_id()],"name":material.resource_name,"shader":material.shader.resource_path if material is ShaderMaterial else "StandardMaterial3D"})
        var views=[["whole-side",false,0.,0.],["whole-opposite",false,PI,0.],["whole-top",false,0.,1.56],["whole-bottom",false,0.,-1.56],["whole-oblique",false,.45,.28],["head-side",true,0.,0.],["head-front",true,PI/2.,0.],["head-top",true,0.,1.56],["head-bottom",true,0.,-1.56],["head-oblique",true,.65,.20]]
        for view in views:
            camera(entry,r,view[1],view[2],view[3])
            set_mode(entry,stored,"texture");await shot(folder+"/"+view[0]+".png")
            if view[0] in ["whole-top","whole-bottom","head-side","head-front","head-top","head-bottom","head-oblique"]:
                set_mode(entry,stored,"albedo");await shot(folder+"/"+view[0]+"-albedo.png")
                set_mode(entry,stored,"clay");await shot(folder+"/"+view[0]+"-clay.png")
            if view[0] in ["head-front","head-oblique","head-bottom"]:
                set_mode(entry,stored,"ownership");await shot(folder+"/"+view[0]+"-ownership.png")
            set_mode(entry,stored,"texture")
            if view[0] in ["whole-side","whole-top","whole-bottom","whole-oblique"]:
                for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
                    if ownership[species].fins.has(str(mesh.name)):mesh.visible=false
                await shot(folder+"/"+view[0]+"-skin-only.png")
                for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.visible=intrinsic[mesh.get_instance_id()]
        var samples:Array=[]
        entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        for action in ["Swim","Turn","Ascend","Dive"]:
            assert(entry.controller.set_action(action,true))
            entry.controller.step(0.)
            for j in 4:
                var t:float=[0.,.35,.75,1.25][j]
                entry.controller.seek(t)
                if entry.has("jaw_controller"):entry.jaw_controller.apply(float(j)/3.)
                camera(entry,r,j in [1,2],PI/2. if j==2 else (.65 if j==1 else (PI if j==3 else 0.)),.12 if j==1 else 0.)
                var file=folder+"/motion-"+action+"-%d.png"%j
                await shot(file)
                assert(entry.controller.snapshot().action==action)
                samples.append({"action":action,"seconds":t,"jaw_ratio":float(j)/3. if entry.has("jaw_controller") else -1.,"snapshot":entry.controller.snapshot(),"file":file,"sha256":FileAccess.get_sha256(file)})
        set_mode(entry,stored,"texture")
        records.append({"species":species,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"name":hall.LABELS[species],"body_region_native":str(r.body),"head_region_native":str(r.head),"materials":material_inventory,"motion_samples":samples,"separate_jaw":entry.has("jaw_controller")})
        print("SURFACE_MOUTH_CAPTURE ",species)
    var files:Dictionary={}
    for file in starting_bindings:
        assert(FileAccess.get_sha256("res://"+file)==starting_bindings[file],"Runtime changed during visual capture: "+file)
        files[file]=starting_bindings[file]
    for file in ["scripts/aquarium/VolumeFishExhibit.gd","scripts/aquarium/FishBodyOpaque.gdshader","scripts/aquarium/FishMouthPigment.gdshader","scripts/aquarium/FishHeadSource.gdshaderinc","scripts/aquarium/FishHeadSource.gd","scripts/aquarium/FishSurfaceOwnership.gd","scripts/aquarium/FoundryFishMotion.gd","assets/models/fish/motion/head-source.json","assets/models/fish/motion/mouth-pigment.json","assets/models/fish/motion/body-opacity.json","assets/models/fish/motion/surface-ownership.json","assets/models/fish/motion/motion.json"]:
        if FileAccess.file_exists("res://"+file):files[file]=FileAccess.get_sha256("res://"+file)
    var f=FileAccess.open(out+"/capture.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":records.size()==requested.size(),"status":"done","next_action":"human_review","records":records,"files":files,"script_sha256":FileAccess.get_sha256(OS.get_cmdline_args()[OS.get_cmdline_args().find("--script")+1]),"scope":"Read-only current-game textured/albedo/clay/ownership/hidden-fin views and16 discrete four-action frames per species. Not source-anatomy, fin-contact or continuous visibility acceptance."}));f.close()
    hall.queue_free();await process_frame
    if RenderingServer.has_method("force_sync"):RenderingServer.force_sync()
    await process_frame
    quit()
