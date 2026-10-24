extends "capture_surface_mouth_audit.gd"
## Fixed-camera original/candidate review for explicitly frozen species geometry.
var study:Dictionary
var study_path:String
func _initialize():
    var args=OS.get_cmdline_user_args();study_path=args[0];out=args[1]
    study=JSON.parse_string(FileAccess.get_file_as_string(study_path))
    call_deferred("run")
func run():
    DirAccess.make_dir_recursive_absolute(out)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    hall._select_display(study.species);var e=hall._selected()
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):
        intrinsic[mesh.get_instance_id()]=mesh.visible
        if not e.model.is_ancestor_of(mesh):mesh.hide()
    for tank in hall.tanks:tank.root.visible=tank.species==study.species
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
    e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
    e.player.stop();e.skeleton.reset_bone_poses()
    var r=region(e);var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    for variant in ["original","candidate"]:
        if variant=="candidate":
            assert(FileAccess.get_sha256(study.gray_mesh)==study.gray_sha256)
            var data=JSON.parse_string(FileAccess.get_file_as_string(study.gray_mesh))
            var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
            var vertices=PackedVector3Array();var normals=PackedVector3Array()
            for p in data.vertices:vertices.append(Vector3(p[0],p[1],p[2]))
            for p in data.normals:normals.append(Vector3(p[0],p[1],p[2]))
            arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(data.triangles)
            var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
            body.mesh=mesh;body.skin=null
        var stored=[]
        for mesh in e.model.find_children("*","MeshInstance3D",true,false):
            for si in mesh.mesh.get_surface_count():stored.append([mesh,si,mesh.get_surface_override_material(si),mesh.get_active_material(si)])
        set_mode(e,stored,"clay")
        var folder=out.path_join(variant);DirAccess.make_dir_recursive_absolute(folder)
        for view in [["side",0.,0.],["front",PI/2.,0.],["top",0.,1.56],["oblique",.65,.2]]:
            camera(e,r,true,view[1],view[2]);await shot(folder.path_join("head-"+view[0]+"-clay.png"))
        camera(e,r,false,.45,.28);await shot(folder.path_join("whole-oblique-clay.png"))
    var file=FileAccess.open(out.path_join("capture.validation.json"),FileAccess.WRITE)
    file.store_string(JSON.stringify({"ok":true,"status":"done","next_action":"human_review","species":study.species,"plan_sha256":FileAccess.get_sha256(study_path),"production_installed":false,"scope":"Fixed camera static gray comparison. No source, material or rig acceptance."},"  "));file.close()
    hall.queue_free();await process_frame;quit()
