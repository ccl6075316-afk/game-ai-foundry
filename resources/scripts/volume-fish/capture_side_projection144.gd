extends "capture_source_fins143.gd"
## Read-only, native-pixel orthographic comparison of the installed game.
func run():
    DirAccess.make_dir_recursive_absolute(out)
    var bindings={}
    for file in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):
        bindings[file]=FileAccess.get_sha256("res://"+file)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    var rows=[]
    for species in requested:
        hall._select_display(species);var e:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic.get(node.get_instance_id(),false)
        for node in hall.world.find_children("*","Label3D",true,false):node.hide()
        e.player.stop();e.skeleton.reset_bone_poses();e.skeleton.force_update_all_bone_transforms()
        var spec:Dictionary=source_specs[species];var im=source_image_for_species(species)
        var pad:Vector2i=Vector2i(spec.padding[0],spec.padding[1]);hall.viewport.size=im.get_size()+pad*2
        hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
        source_camera(e)
        hall.camera.size*=float(hall.viewport.size.y)/im.get_height()
        var stored=[]
        for mesh in e.model.find_children("*","MeshInstance3D",true,false):
            for si in mesh.mesh.get_surface_count():stored.append([mesh,si,mesh.get_surface_override_material(si),mesh.get_active_material(si)])
        var folder=out.path_join(species);DirAccess.make_dir_recursive_absolute(folder);var images={}
        for mode in ["texture","albedo"]:
            set_mode(e,stored,mode);var p=folder.path_join("side-"+mode+".png");await shot(p)
            images[mode]={"path":p,"sha256":FileAccess.get_sha256(p)}
        set_mode(e,stored,"texture")
        rows.append({"species":species,"name":hall.LABELS[species],"images":images,"source_sha256":spec.source_sha256,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"canvas":[hall.viewport.size.x,hall.viewport.size.y],"padding":spec.padding,"pose":"Installed skeleton native rest; no runtime motion or jaw animation applied.","projection":"orthographic; fixed source pixel mapping, common source/model padding; no local fitting"})
        print("SIDE_PROJECTION144 ",species)
    for file in bindings:assert(FileAccess.get_sha256("res://"+file)==bindings[file],"Runtime changed during capture: "+file)
    var f=FileAccess.open(out.path_join("capture.validation.json"),FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":rows.size()==requested.size(),"status":"done","next_action":"human_review","records":rows,"runtime_files":bindings,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Current installed game, fixed native source coordinates. Comparison only; not new shape or whole-fish acceptance."},"  "));f.close()
    hall.queue_free();await process_frame;quit()
