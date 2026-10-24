extends "./capture_hammer_tail_audit.gd"
## Actual game orbit/actions/native clip + source-table/LOD and fin ownership audit.
func run():
    DirAccess.make_dir_recursive_absolute(out)
    for file in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):starting_bindings[file]=FileAccess.get_sha256("res://"+file)
    root.size=Vector2i(960,640)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(960,640)
    hall.viewport.size=Vector2i(960,640);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var helper=load("res://scripts/aquarium/HammerSurface136.gd").new()
    var rest=load("res://scripts/aquarium/RestSurface114.gd").new()
    for species in requested:
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        var materials=[];var lods=[];var fin_count=0
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            lods.append({"mesh":str(mesh.name),"snapshot":rest.snapshot(mesh),"surfaces":mesh.mesh.get_surface_count()})
            for si in mesh.mesh.get_surface_count():
                var material=mesh.get_active_material(si)
                if ownership[species].fins.has(str(mesh.name)):
                    assert(material is ShaderMaterial and material.shader.resource_path=="res://scripts/aquarium/FishSurfaceOwnership.gdshader")
                    assert(material.get_shader_parameter("fin") and material.get_shader_parameter("edge_count")>0);fin_count+=1
                if str(mesh.name) in ["Closed_body","Cephalofoil"] and (str(mesh.name)=="Cephalofoil" or species=="great_hammerhead" or si==2):
                    var receipt=helper.validate(entry.model,species,mesh,si,material);assert(receipt.ok);materials.append(receipt)
                    var original=material.get_shader_parameter("hammer137_projection")
                    material.set_shader_parameter("hammer137_projection",Vector4.ZERO)
                    assert(not helper.validate(entry.model,species,mesh,si,material).ok)
                    material.set_shader_parameter("hammer137_projection",original)
                    assert(helper.validate(entry.model,species,mesh,si,material).ok)
        assert(fin_count>=ownership[species].fins.size() and materials.size()>=4)
        entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        var r=region(entry);var frames=[]
        for frame in 480:
            var action=["Swim","Turn","Ascend","Dive"][frame/120]
            if frame%120==0:assert(entry.controller.set_action(action,frame==0))
            entry.controller.step(1./24.)
            var phase=float(frame)/480.;var yaw=.45*sin(phase*TAU);var pitch=.20*sin(phase*TAU*2.)
            camera(entry,r,frame<80,yaw,pitch)
            if frame>=80:
                var center:Vector3=entry.model.global_transform*r.body.get_center()
                var distance_gain:float=[1.0,1.1,1.25][mini(2,frame/160)]
                hall.camera.global_position=center+(hall.camera.global_position-center)*distance_gain
            await process_frame
            await RenderingServer.frame_post_draw
            if frame%60==0:
                var file=folder+"/orbit-%03d.png"%frame;assert(hall.viewport.get_texture().get_image().save_png(file)==OK)
                frames.append({"frame":frame,"action":action,"file":file,"sha256":FileAccess.get_sha256(file),"snapshot":entry.controller.snapshot(),"camera_distance":hall.camera.global_position.distance_to(entry.model.global_position)})
        var config=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles[species]
        var player=entry.model.find_children("*","AnimationPlayer",true,false)[0] as AnimationPlayer
        var skeleton=entry.model.find_children("*","Skeleton3D",true,false)[0] as Skeleton3D
        player.stop();skeleton.reset_bone_poses();player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        player.play(config.base_clip);var clip=player.get_animation(config.base_clip)
        for frame in 120:
            player.seek(clip.length*float(frame)/120.,true);player.advance(0.);skeleton.force_update_all_bone_transforms()
            camera(entry,r,false,.6,.25)
            await process_frame
            await RenderingServer.frame_post_draw
            if frame%30==0:
                var file=folder+"/native-%03d.png"%frame;assert(hall.viewport.get_texture().get_image().save_png(file)==OK)
                frames.append({"frame":480+frame,"action":"Native","native_phase":float(frame)/120.,"file":file,"sha256":FileAccess.get_sha256(file)})
        player.stop()
        records.append({"species":species,"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"ok":true,"movie_simulation_seconds":25.,"frames":frames,"materials":materials,"all_imported_lod_array_bindings":lods,"fin_surfaces":fin_count,"wrong_projection_negative_control":true})
    for file in starting_bindings:assert(FileAccess.get_sha256("res://"+file)==starting_bindings[file],"Runtime changed during capture: "+file)
    var f=FileAccess.open(out+"/runtime.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"records":records,"files":starting_bindings,"checker_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Actual four-action orbit with real transitions, near/normal/far distances, native clip, per-surface current rest tables including full imported LOD snapshots, unchanged fin shaders. Movie25 simulated seconds per fish. No continuous collision proof."},"  "));f.close();quit()
