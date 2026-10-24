extends "capture_surface_mouth_audit.gd"
## Exact native source canvas; no independent crop/fit of candidate anatomy.
func run():
    var args=OS.get_cmdline_user_args();out=args[0];var source_root=args[1];DirAccess.make_dir_recursive_absolute(out)
    var hall_script=load("res://scripts/aquarium/VolumeFishExhibit.gd");hall=hall_script.new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    var profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    var rows=[]
    for species in profiles:
        hall._select_display(species);var e:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic.get(node.get_instance_id(),false)
        for node in hall.world.find_children("*","Label3D",true,false):node.hide()
        var source=source_root.path_join(species).path_join("source-original.png");var im=Image.load_from_file(source);assert(im!=null)
        e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true);e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
        if e.has("jaw_controller"):e.jaw_controller.apply(1.)
        var stored=[]
        for node in e.model.find_children("*","MeshInstance3D",true,false):
            for si in node.mesh.get_surface_count():var mat=node.get_active_material(si);stored.append([node,si,mat,mat])
        hall.viewport.size=im.get_size();hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
        var tr:Transform3D=e.model.global_transform;var scale:float=tr.basis.get_scale().x
        hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL;hall.camera.size=float(im.get_height())/im.get_width()*scale;hall.camera.near=.00001
        hall.camera.global_position=tr*Vector3(0.,0.,2.);hall.camera.look_at(tr*Vector3.ZERO,tr.basis.orthonormalized()*Vector3.UP)
        var folder=out.path_join(species);DirAccess.make_dir_recursive_absolute(folder);var images={}
        for mode in ["texture","albedo","clay"]:
            set_mode(e,stored,mode);var path=folder.path_join("source-canvas-"+mode+".png");await shot(path);images[mode]={"path":path,"sha256":FileAccess.get_sha256(path)}
        set_mode(e,stored,"texture")
        rows.append({"species":species,"source":source,"source_sha256":FileAccess.get_sha256(source),"native_canvas":[im.get_width(),im.get_height()],"images":images,"jaw_reference":1. if e.has("jaw_controller") else null})
    var f=FileAccess.open(out.path_join("capture.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==profiles.size(),"rows":rows,"config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json"),"checker_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Actual configured fish on the exact native source canvas at native XY/scale; no local crop or refit. Source pose limitations and hidden thickness remain separate."}));f.close()
    hall.queue_free();await process_frame;quit()
