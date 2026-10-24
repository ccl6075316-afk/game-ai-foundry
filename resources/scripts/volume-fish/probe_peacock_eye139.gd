extends "capture_surface_mouth_audit.gd"
func run():
    DirAccess.make_dir_recursive_absolute(out)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    hall._select_display("peacock_bass");var e:Dictionary=hall._selected()
    for tank in hall.tanks:tank.root.visible=tank.species=="peacock_bass"
    for node in hall.world.find_children("*","MeshInstance3D",true,false):
        intrinsic[node.get_instance_id()]=node.visible
        if not e.model.is_ancestor_of(node):node.hide()
    for node in hall.world.find_children("*","Label3D",true,false):node.hide()
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
    e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
    if e.has("jaw_controller"):e.jaw_controller.apply(1.)
    var r=region(e)
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var mat=body.get_active_material(0) as ShaderMaterial
    var original_guard=mat.get_shader_parameter("chart112_eye_rect_native")
    for variant in ["baseline","no-eye-cap","no-eye-guard","retire-old-eye-sheet"]:
        for node in e.model.find_children("Eye_relief112*","MeshInstance3D",true,false):node.visible=variant in ["baseline","retire-old-eye-sheet"]
        for node in e.model.find_children("Textured_eye*","MeshInstance3D",true,false):node.visible=variant!="retire-old-eye-sheet"
        mat.set_shader_parameter("chart112_eye_rect_native",Vector4.ZERO if variant=="no-eye-guard" else original_guard)
        if variant=="no-eye-guard":mat.set_shader_parameter("chart112_eye_rect_native",Vector4.ZERO)
        camera(e,r,true,.65,.2);await shot(out+"/"+variant+".png")
    var file=FileAccess.open(out+"/probe.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"ok":true,"scope":"Diagnostic only: isolated existing eye cap and chart eye guard. No production edits.","model_sha256":FileAccess.get_sha256("res://assets/models/fish/peacock_bass.glb")}));file.close()
    hall.queue_free();await process_frame;quit()
