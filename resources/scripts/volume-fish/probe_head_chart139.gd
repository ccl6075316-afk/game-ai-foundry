extends "capture_surface_mouth_audit.gd"
## Isolated chart diagnosis; no asset installation or acceptance.
func run():
    var args=OS.get_cmdline_user_args();out=args[0];var species=args[1]
    DirAccess.make_dir_recursive_absolute(out)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    hall._select_display(species);var e:Dictionary=hall._selected()
    for tank in hall.tanks:tank.root.visible=tank.species==species
    for node in hall.world.find_children("*","MeshInstance3D",true,false):
        intrinsic[node.get_instance_id()]=node.visible
        if not e.model.is_ancestor_of(node):node.hide()
    for node in hall.world.find_children("*","Label3D",true,false):node.hide()
    e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
    e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    if args.size()>2:
        body.mesh=load(args[2])
        for si in body.mesh.get_surface_count():body.set_surface_override_material(si,null)
    var mat=body.get_active_material(0) as ShaderMaterial
    var longitudinal=mat.get_shader_parameter("chart112_longitudinal")
    var normal=mat.get_shader_parameter("chart112_normal_blend")
    var guard=mat.get_shader_parameter("chart112_eye_rect_native")
    var original_code:String=mat.shader.code
    var front=mat.get_shader_parameter("front112_x")
    print("CHART_PARAMS ",species," ",longitudinal," ",normal," ",guard)
    for node in e.model.find_children("*eye*","MeshInstance3D",true,false):print("EYE_NODE ",node.name," visible=",node.visible)
    for node in e.model.find_children("Eye_relief112*","MeshInstance3D",true,false):print("RELIEF_NODE ",node.name," visible=",node.visible)
    var r=region(e)
    for variant in ["baseline","longitudinal","normal","no-guard","upper-only","no-front","no-eye-cap"]:
        for node in e.model.find_children("Eye_relief112*","MeshInstance3D",true,false):node.visible=variant!="no-eye-cap"
        var shader=Shader.new();shader.code=original_code
        if variant=="upper-only":
            shader.code=original_code.replace("amount*=1.-smoothstep(chart112_longitudinal.z,chart112_longitudinal.w,u);","amount*=max(1.-smoothstep(chart112_longitudinal.z,chart112_longitudinal.w,u),smoothstep(.4,.75,y));")
        mat.shader=shader
        mat.set_shader_parameter("chart112_longitudinal",longitudinal if variant in ["baseline","upper-only","no-front","no-eye-cap"] else Vector4(longitudinal.x,longitudinal.y,1.05,1.1))
        if front!=null:mat.set_shader_parameter("front112_x",Vector2(10.,11.) if variant=="no-front" else front)
        mat.set_shader_parameter("chart112_normal_blend",Vector2(.15,.5) if variant in ["normal","no-guard"] else normal)
        mat.set_shader_parameter("chart112_eye_rect_native",Vector4.ZERO if variant=="no-guard" else guard)
        camera(e,r,true,.65,.2);await shot(out+"/"+variant+".png")
    hall.queue_free();await process_frame;quit()
