extends SceneTree
var hall
var out: String
var records: Dictionary={}
func _initialize():
    var args=OS.get_cmdline_user_args();assert(args.size()==1,"Expected absolute output directory");out=args[0];call_deferred("run")
func run():
    DirAccess.make_dir_recursive_absolute(out);root.size=Vector2i(1200,800)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800);hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    var cfg=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/head-source.json")).profiles
    var black=StandardMaterial3D.new();black.albedo_color=Color.BLACK;black.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    for sp in hall.SPECIES:
        if not cfg.has(sp):continue
        hall._select_display(sp);var entry:Dictionary=hall._selected()
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and str(mesh.name)==cfg[sp].mesh
        entry.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true);entry.controller.seek(0.)
        var mesh=entry.model.find_child(cfg[sp].mesh,true,false) as MeshInstance3D;var skin=mesh.get_active_material(0) as ShaderMaterial
        for s in range(1,mesh.mesh.get_surface_count()):mesh.set_surface_override_material(s,black)
        var tr:Transform3D=entry.carrier.global_transform;var basis=tr.basis.orthonormalized();var center=tr.origin+basis*Vector3(entry.length_m*.32,0.,0.)
        for mode in [1,2]:
            skin.set_shader_parameter("head_eye_debug",mode)
            for view in [["top",0.,1.55],["front",PI/2.,0.]]:
                var offset=basis*Vector3(sin(view[1])*cos(view[2]),sin(view[2]),cos(view[1])*cos(view[2]));hall.camera.near=.003;hall.camera.global_position=center+offset*entry.length_m*.62;hall.camera.look_at(center,basis*Vector3.UP)
                await process_frame;await RenderingServer.frame_post_draw
                assert(hall.viewport.get_texture().get_image().save_png(out+"/"+sp+"-"+view[0]+"-"+str(mode)+".png")==OK)
        skin.set_shader_parameter("head_eye_debug",0)
        records[sp]=FileAccess.get_sha256("res://assets/models/fish/"+sp+".glb")
    var f=FileAccess.open(out+"/capture.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"models_sha256":records,"head_source_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/head-source.json"),"shader_sha256":FileAccess.get_sha256("res://scripts/aquarium/FishHeadSource.gdshaderinc"),"views_per_species":4,"method":"Actual source-eye footprint isolated on the current material; mode1 constrained, mode2 old wrap negative control. Specialty non-planar eye models require separate textured visual review."}));f.close()
    quit()
