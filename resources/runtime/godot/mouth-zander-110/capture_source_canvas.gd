extends "capture_trial_109.gd"
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(2024,742)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
    hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(2024,742)
    hall.viewport.size=Vector2i(2024,742);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    hall._select_display("zander");var entry:Dictionary=hall._selected()
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):
        intrinsic[mesh.get_instance_id()]=mesh.visible
        mesh.visible=entry.model.is_ancestor_of(mesh) and mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    entry.controller.set_motion_controls({"body_amplitude":0.,"body_frequency":1.,"fin_amplitude":0.,"fin_frequency":1.},true)
    entry.controller.set_action("Swim",true);entry.controller.step(0.);entry.controller.seek(0.)
    hall.viewport.mesh_lod_threshold=0.
    var center:Vector3=entry.model.global_transform*Vector3.ZERO
    var basis:Basis=entry.model.global_transform.basis.orthonormalized()
    hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    hall.camera.keep_aspect=Camera3D.KEEP_HEIGHT
    hall.camera.size=742./2024.*entry.model.global_transform.basis.get_scale().x
    hall.camera.global_position=center+basis*Vector3(0,0,3.)
    hall.camera.look_at(center,basis*Vector3.UP)
    var stored:Array=[]
    for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
        for surface in mesh.mesh.get_surface_count():stored.append([mesh,surface,mesh.get_surface_override_material(surface),mesh.get_active_material(surface)])
    var files:Dictionary={}
    for mode in ["texture","albedo","clay"]:
        set_mode(entry,stored,mode)
        await process_frame;RenderingServer.force_draw();await process_frame;RenderingServer.force_draw()
        var p:String=out+"/source-canvas-"+mode+".png"
        assert(hall.viewport.get_texture().get_image().save_png(p)==OK)
        files[p]=FileAccess.get_sha256(p)
    var f=FileAccess.open(out+"/source-canvas.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"files":files,"camera":"Native X[-.5,.5],Y[-742/2024/2,742/2024/2]; original2024x742canvas; orthographic; no local alignment","model_sha256":FileAccess.get_sha256("res://assets/models/fish/zander.glb")},"  "));f.close()
    hall.queue_free();await process_frame;quit()
