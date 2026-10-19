extends SceneTree
var hall
var out: String
var profiles: Dictionary
var opaque_profiles: Dictionary
func _initialize():
    out=OS.get_cmdline_user_args()[0]
    call_deferred("run")
func capture(path: String):
    await process_frame
    await RenderingServer.frame_post_draw
    assert(hall.viewport.get_texture().get_image().save_png(path)==OK)
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(800,600);root.content_scale_size=Vector2i(800,600)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);hall.viewport.size=Vector2i(800,600);hall.viewport.transparent_bg=true
    hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    opaque_profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/body-opacity.json")).profiles
    for env in hall.world.find_children("*","WorldEnvironment",true,false):
        env.environment.background_mode=Environment.BG_CLEAR_COLOR
    var reference:=StandardMaterial3D.new();reference.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;reference.cull_mode=BaseMaterial3D.CULL_DISABLED;reference.albedo_color=Color.WHITE
    var records: Array=[]
    var views=[[0.,0.],[PI,0.],[PI/2.,0.],[-PI/2.,0.],[.5,.85],[.5,-.85],[PI+.5,.65],[PI+.5,-.65]]
    for species in hall.SPECIES:
        hall._select_display(species)
        var entry: Dictionary=hall._selected()
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and not profiles[species].fins.has(str(mesh.name)) and not str(mesh.name) in opaque_profiles[species].suppressed_auxiliary and not opaque_profiles[species].get("decorative_overlays",{}).has(str(mesh.name))
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            if opaque_profiles[species].get("decorative_overlays",{}).has(str(mesh.name)):
                for si in mesh.mesh.get_surface_count():
                    var original=mesh.mesh.surface_get_material(si)
                    var active=mesh.get_active_material(si)
                    assert(active is StandardMaterial3D and active.transparency==original.transparency and active.albedo_color==original.albedo_color and active.albedo_texture==original.albedo_texture,"Authored head fusion overwritten")
        var bodies: Array=[]
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            if not profiles[species].fins.has(str(mesh.name)) and not str(mesh.name) in opaque_profiles[species].suppressed_auxiliary and not opaque_profiles[species].get("decorative_overlays",{}).has(str(mesh.name)):
                var originals: Array=[]
                for s in mesh.mesh.get_surface_count():
                    var material=mesh.get_active_material(s)
                    if material is ShaderMaterial:
                        if material.shader.resource_path=="res://scripts/aquarium/FishMouthPigment.gdshader":
                            var mouth_profiles:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-pigment.json")).profiles
                            assert(mouth_profiles.has(species),"Unregistered oral pigment")
                            var p:Dictionary=mouth_profiles[species]
                            assert(p.mesh==str(mesh.name) and int(p.oral_surface)==s,"Wrong oral pigment surface")
                            assert(p.model_sha256==FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"))
                            assert(material.get_shader_parameter("source_texture")!=null,"Missing oral palette")
                        else:
                            assert(material.shader.resource_path=="res://scripts/aquarium/FishBodyOpaque.gdshader","Unexpected body shader")
                            assert(material.get_shader_parameter("opaque_skin")!=null,"Missing body donor")
                    else:
                        assert(material is StandardMaterial3D and material.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED,"Nonopaque body surface")
                    originals.append(material)
                bodies.append({"mesh":mesh,"materials":originals})
        var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        for pose in 2:
            entry.controller.set_motion_controls({"body_amplitude":0. if pose==0 else 2.5,"fin_amplitude":0. if pose==0 else 2.5},true);entry.controller.seek(1.17)
            await process_frame
            await process_frame
            for v in views.size():
                var tr: Transform3D=entry.carrier.global_transform;var yaw: float=views[v][0];var pitch: float=views[v][1]
                hall.camera.global_position=tr.origin+tr.basis.orthonormalized()*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*entry.length_m*1.4
                hall.camera.look_at(tr.origin,tr.basis.orthonormalized()*Vector3.UP)
                var stem=folder+"/p%d-v%d"%[pose,v]
                for b in bodies:
                    for s in b.materials.size():b.mesh.set_surface_override_material(s,b.materials[s])
                await capture(stem+"-actual.png")
                for b in bodies:
                    for s in b.materials.size():b.mesh.set_surface_override_material(s,reference)
                await capture(stem+"-closed.png")
            records.append({"species":species,"pose":pose,"views":views.size(),"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")})
        for b in bodies:
            for s in b.materials.size():b.mesh.set_surface_override_material(s,b.materials[s])
        print("BODY_COVERAGE ",species)
    var bindings: Dictionary={}
    for file in ["scripts/aquarium/FishHeadSource.gd","scripts/aquarium/FishHeadSource.gdshaderinc","assets/models/fish/motion/head-source.json","scripts/aquarium/FishSurfaceOwnership.gd","scripts/aquarium/FishSurfaceOwnership.gdshader","scripts/aquarium/FishBodyOpaque.gdshader","scripts/aquarium/FishMouthPigment.gd","scripts/aquarium/FishMouthPigment.gdshader","scripts/aquarium/FoundryFishMotion.gd","assets/models/fish/motion/mouth-pigment.json","assets/models/fish/motion/body-opacity.json","assets/models/fish/motion/motion.json"]:bindings[file]=FileAccess.get_sha256("res://"+file)
    var f=FileAccess.open(out+"/capture.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"records":records,"files":bindings}));f.close();quit()
