extends "./capture_surface_mouth_audit.gd"
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(800,600);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(800,600);hall.viewport.size=Vector2i(800,600);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    for species in ["black_seabream","zander"]:
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        var r:Dictionary=region(entry);var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        entry.controller.set_action("Swim",true);entry.controller.step(0.)
        for frame in 72:
            entry.controller.seek(float(frame)/24.)
            camera(entry,r,false,.32,.72)
            await shot(folder+"/frame-%03d.png"%frame)
        records.append({"species":species,"frames":72,"fps":24,"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"body_chart_helper_sha256":FileAccess.get_sha256("res://scripts/aquarium/BodyChart112.gd"),"scope":"Actual production texture and controller, fixed oblique top camera; visual reference, not artistic acceptance"})
    var f=FileAccess.open(out+"/swim.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"records":records},"  "));quit()
